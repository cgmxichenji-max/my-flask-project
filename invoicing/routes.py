from flask import Blueprint, render_template, request, redirect, url_for, current_app
import os
import sqlite3

from openpyxl import load_workbook

from auth.decorators import module_required


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_database_path():
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return db_path
    return os.path.join(BASE_DIR, 'data', 'main.db')


def get_db_connection():
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    return conn


invoicing_bp = Blueprint('invoicing', __name__, template_folder='../templates')


CUSTOMER_HEADERS = ('达人', '客户', '客户简称', '带货账号昵称', '团长', '账号昵称')
AMOUNT_HEADERS = ('应开金额', '带货费用', '佣金', '求和项:带货费用', '金额')
PLATFORM_HEADERS = ('平台', '平台名称')
PERIOD_HEADERS = ('期间', '账期', '周期')
ENTITY_HEADERS = ('开票主体', '主体')
SHOP_HEADERS = ('店铺', '店铺名称')
REMARK_HEADERS = ('备注', '说明')
PERIOD_START_HEADERS = ('period_start', '账期起点', '期间起点', '开始日期')
PERIOD_END_HEADERS = ('period_end', '账期终点', '期间终点', '结束日期')


def normalize_header(value):
    return str(value or '').strip().replace(' ', '').replace('\n', '')


def find_header(headers, candidates):
    normalized_headers = {normalize_header(header): header for header in headers}
    for candidate in candidates:
        header = normalized_headers.get(normalize_header(candidate))
        if header:
            return header
    return None


def cell_text(value):
    if value is None:
        return ''
    return str(value).strip()


def parse_amount(value):
    if value is None or value == '':
        return None
    text = str(value).strip().replace(',', '').replace('¥', '').replace('￥', '')
    try:
        return float(text)
    except ValueError:
        return None


def find_or_create_customer(conn, raw_name):
    name = (raw_name or '').strip()
    if not name:
        return None, False

    row = conn.execute(
        "SELECT id FROM customer WHERE short_name = ?",
        (name,),
    ).fetchone()
    if row:
        return row['id'], False

    row = conn.execute(
        "SELECT id FROM customer WHERE full_name = ?",
        (name,),
    ).fetchone()
    if row:
        return row['id'], False

    row = conn.execute(
        "SELECT customer_id FROM customer_alias WHERE alias = ?",
        (name,),
    ).fetchone()
    if row:
        return row['customer_id'], False

    cursor = conn.execute(
        "INSERT INTO customer (short_name) VALUES (?)",
        (name,),
    )
    return cursor.lastrowid, True


def get_entity_id_by_name(conn, entity_name):
    if not entity_name:
        return None
    row = conn.execute(
        "SELECT id FROM billing_entity WHERE name = ?",
        (entity_name,),
    ).fetchone()
    return row['id'] if row else None


# ===== 模块首页 =====

@invoicing_bp.route('/')
@module_required('invoicing')
def index():
    return render_template('invoicing_index.html')


# ===== 应开金额导入与查看 =====

@invoicing_bp.route('/expected-amounts')
@module_required('invoicing')
def expected_amounts():
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                e.id,
                c.short_name AS customer_name,
                b.name AS entity_name,
                e.platform,
                e.period,
                e.period_start,
                e.period_end,
                e.amount,
                e.shop_name,
                e.remark,
                e.created_at
            FROM expected_amount e
            LEFT JOIN customer c ON c.id = e.customer_id
            LEFT JOIN billing_entity b ON b.id = e.entity_id
            ORDER BY e.id DESC
            """
        ).fetchall()
        entities = conn.execute(
            "SELECT id, name FROM billing_entity ORDER BY id"
        ).fetchall()
    return render_template(
        'invoicing_expected_amounts.html',
        rows=rows,
        entities=entities,
        result=None,
    )


@invoicing_bp.route('/expected-amounts/import', methods=['POST'])
@module_required('invoicing')
def import_expected_amounts():
    default_entity_id = request.form.get('entity_id')
    default_platform = (request.form.get('platform') or '').strip()
    default_period = (request.form.get('period') or '').strip()
    default_period_start = (request.form.get('period_start') or '').strip() or None
    default_period_end = (request.form.get('period_end') or '').strip() or None
    sheet_name = (request.form.get('sheet_name') or '').strip()
    upload_file = request.files.get('file')

    result = {
        'success': False,
        'message': '',
        'imported_count': 0,
        'created_customer_count': 0,
        'duplicate_skipped_count': 0,
        'skipped_rows': [],
    }

    if not upload_file or not upload_file.filename:
        result['message'] = '请选择 Excel 文件'
    elif not upload_file.filename.lower().endswith(('.xlsx', '.xlsm')):
        result['message'] = '仅支持 .xlsx / .xlsm 文件'
    elif not default_entity_id:
        result['message'] = '请选择默认开票主体'
    elif not default_platform:
        result['message'] = '请输入默认平台'
    elif not default_period:
        result['message'] = '请输入默认期间'
    else:
        try:
            workbook = load_workbook(upload_file, data_only=True)
            worksheet = workbook[sheet_name] if sheet_name else workbook.active
            rows_iter = worksheet.iter_rows(values_only=True)
            raw_headers = next(rows_iter, None)
            if not raw_headers:
                raise ValueError('Excel 表头为空')

            headers = [cell_text(header) for header in raw_headers]
            customer_header = find_header(headers, CUSTOMER_HEADERS)
            amount_header = find_header(headers, AMOUNT_HEADERS)
            platform_header = find_header(headers, PLATFORM_HEADERS)
            period_header = find_header(headers, PERIOD_HEADERS)
            entity_header = find_header(headers, ENTITY_HEADERS)
            shop_header = find_header(headers, SHOP_HEADERS)
            remark_header = find_header(headers, REMARK_HEADERS)
            period_start_header = find_header(headers, PERIOD_START_HEADERS)
            period_end_header = find_header(headers, PERIOD_END_HEADERS)

            if not customer_header or not amount_header:
                raise ValueError('Excel 缺少达人/客户列或应开金额列')

            with get_db_connection() as conn:
                for row_number, raw_row in enumerate(rows_iter, start=2):
                    row = {
                        headers[index]: raw_row[index] if index < len(raw_row) else None
                        for index in range(len(headers))
                        if headers[index]
                    }
                    customer_name = cell_text(row.get(customer_header))
                    amount = parse_amount(row.get(amount_header))
                    platform = cell_text(row.get(platform_header)) if platform_header else default_platform
                    period = cell_text(row.get(period_header)) if period_header else default_period
                    entity_name = cell_text(row.get(entity_header)) if entity_header else ''
                    entity_id = get_entity_id_by_name(conn, entity_name) if entity_name else int(default_entity_id)
                    shop_name = cell_text(row.get(shop_header)) if shop_header else None
                    remark = cell_text(row.get(remark_header)) if remark_header else None
                    period_start = cell_text(row.get(period_start_header)) if period_start_header else default_period_start
                    period_end = cell_text(row.get(period_end_header)) if period_end_header else default_period_end

                    if not customer_name and amount is None:
                        continue
                    if not customer_name or amount is None or not platform or not period or not entity_id:
                        result['skipped_rows'].append({
                            'row_number': row_number,
                            'reason': '缺少达人、金额、平台、期间或开票主体',
                        })
                        continue

                    customer_id, created_customer = find_or_create_customer(conn, customer_name)
                    if created_customer:
                        result['created_customer_count'] += 1

                    existing = conn.execute(
                        """
                        SELECT id FROM expected_amount
                        WHERE customer_id = ?
                          AND entity_id = ?
                          AND platform = ?
                          AND period = ?
                          AND amount = ?
                        """,
                        (customer_id, entity_id, platform, period, amount),
                    ).fetchone()
                    if existing:
                        result['duplicate_skipped_count'] += 1
                        continue

                    conn.execute(
                        """
                        INSERT INTO expected_amount (
                            customer_id, entity_id, platform, period, amount,
                            shop_name, remark, period_start, period_end
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            customer_id,
                            entity_id,
                            platform,
                            period,
                            amount,
                            shop_name or None,
                            remark or None,
                            period_start or None,
                            period_end or None,
                        ),
                    )
                    result['imported_count'] += 1

                conn.commit()

            result['success'] = True
            result['message'] = (
                f"成功导入 {result['imported_count']} 条应开金额记录；"
                f"已存在跳过 {result['duplicate_skipped_count']} 条"
            )
        except Exception as exc:
            result['message'] = f'导入失败：{str(exc)}'

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                e.id,
                c.short_name AS customer_name,
                b.name AS entity_name,
                e.platform,
                e.period,
                e.period_start,
                e.period_end,
                e.amount,
                e.shop_name,
                e.remark,
                e.created_at
            FROM expected_amount e
            LEFT JOIN customer c ON c.id = e.customer_id
            LEFT JOIN billing_entity b ON b.id = e.entity_id
            ORDER BY e.id DESC
            """
        ).fetchall()
        entities = conn.execute(
            "SELECT id, name FROM billing_entity ORDER BY id"
        ).fetchall()

    return render_template(
        'invoicing_expected_amounts.html',
        rows=rows,
        entities=entities,
        result=result,
    )


# ===== 开票主体 CRUD =====

@invoicing_bp.route('/billing-entities')
@module_required('invoicing')
def billing_entities():
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at, updated_at FROM billing_entity ORDER BY id"
        ).fetchall()
    return render_template('invoicing_billing_entities.html', rows=rows)


@invoicing_bp.route('/billing-entities/create', methods=['POST'])
@module_required('invoicing')
def create_billing_entity():
    name = (request.form.get('name') or '').strip()
    if name:
        with get_db_connection() as conn:
            conn.execute("INSERT INTO billing_entity (name) VALUES (?)", (name,))
            conn.commit()
    return redirect(url_for('invoicing.billing_entities'))


@invoicing_bp.route('/billing-entities/<int:entity_id>/update', methods=['POST'])
@module_required('invoicing')
def update_billing_entity(entity_id):
    name = (request.form.get('name') or '').strip()
    if name:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE billing_entity SET name = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (name, entity_id),
            )
            conn.commit()
    return redirect(url_for('invoicing.billing_entities'))


@invoicing_bp.route('/billing-entities/<int:entity_id>/delete', methods=['POST'])
@module_required('invoicing')
def delete_billing_entity(entity_id):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM billing_entity WHERE id = ?", (entity_id,))
        conn.commit()
    return redirect(url_for('invoicing.billing_entities'))


# ===== 客户 CRUD =====

@invoicing_bp.route('/customers')
@module_required('invoicing')
def customers():
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                c.id,
                c.short_name,
                c.full_name,
                c.created_at,
                c.updated_at,
                COALESCE(a.alias_list, '') AS alias_list
            FROM customer c
            LEFT JOIN (
                SELECT customer_id, GROUP_CONCAT(alias, ' / ') AS alias_list
                FROM (
                    SELECT customer_id, alias
                    FROM customer_alias
                    ORDER BY id
                )
                GROUP BY customer_id
            ) a ON a.customer_id = c.id
            ORDER BY c.id
            """
        ).fetchall()
    return render_template('invoicing_customers.html', rows=rows)


@invoicing_bp.route('/customers/create', methods=['POST'])
@module_required('invoicing')
def create_customer():
    short_name = (request.form.get('short_name') or '').strip()
    full_name = (request.form.get('full_name') or '').strip() or None
    if short_name:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO customer (short_name, full_name) VALUES (?, ?)",
                (short_name, full_name),
            )
            conn.commit()
    return redirect(url_for('invoicing.customers'))


@invoicing_bp.route('/customers/<int:customer_id>')
@module_required('invoicing')
def customer_detail(customer_id):
    with get_db_connection() as conn:
        customer = conn.execute(
            "SELECT id, short_name, full_name, created_at, updated_at FROM customer WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if not customer:
            return redirect(url_for('invoicing.customers'))
        aliases = conn.execute(
            "SELECT id, alias, created_at FROM customer_alias WHERE customer_id = ? ORDER BY id",
            (customer_id,),
        ).fetchall()
    return render_template(
        'invoicing_customer_detail.html',
        customer=customer,
        aliases=aliases,
    )


@invoicing_bp.route('/customers/<int:customer_id>/update', methods=['POST'])
@module_required('invoicing')
def update_customer(customer_id):
    short_name = (request.form.get('short_name') or '').strip()
    full_name = (request.form.get('full_name') or '').strip() or None
    if short_name:
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE customer SET short_name = ?, full_name = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                (short_name, full_name, customer_id),
            )
            conn.commit()
    return redirect(url_for('invoicing.customer_detail', customer_id=customer_id))


@invoicing_bp.route('/customers/<int:customer_id>/delete', methods=['POST'])
@module_required('invoicing')
def delete_customer(customer_id):
    with get_db_connection() as conn:
        # 外键未启用，需手动级联删除别名
        conn.execute("DELETE FROM customer_alias WHERE customer_id = ?", (customer_id,))
        conn.execute("DELETE FROM customer WHERE id = ?", (customer_id,))
        conn.commit()
    return redirect(url_for('invoicing.customers'))


# ===== 客户别名 =====

@invoicing_bp.route('/customers/<int:customer_id>/aliases/create', methods=['POST'])
@module_required('invoicing')
def create_alias(customer_id):
    alias = (request.form.get('alias') or '').strip()
    if alias:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT INTO customer_alias (customer_id, alias) VALUES (?, ?)",
                (customer_id, alias),
            )
            conn.commit()
    return redirect(url_for('invoicing.customer_detail', customer_id=customer_id))


@invoicing_bp.route('/aliases/<int:alias_id>/delete', methods=['POST'])
@module_required('invoicing')
def delete_alias(alias_id):
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT customer_id FROM customer_alias WHERE id = ?",
            (alias_id,),
        ).fetchone()
        if row is None:
            return redirect(url_for('invoicing.customers'))
        customer_id = row['customer_id']
        conn.execute("DELETE FROM customer_alias WHERE id = ?", (alias_id,))
        conn.commit()
    return redirect(url_for('invoicing.customer_detail', customer_id=customer_id))
