from flask import Blueprint, render_template, request, jsonify, current_app
import sqlite3
import os
import re
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_database_path():
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return db_path
    return os.path.join(BASE_DIR, "data", "main.db")

purchase_bp = Blueprint('purchase', __name__, template_folder='../templates')


# ===== 数据库连接函数 =====
def get_db_connection():
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ===== 通用辅助 =====
def normalize_pack_item_name(raw_name: str) -> str:
    """把原始包材描述归一为系统内部使用的型号名"""
    name = (raw_name or '').strip()
    if not name:
        return ''
    
    # 如果是数字＋号，例如 10号，8号，6号，去掉最后的“号”
    if name.endswith('号') and name[:-1].isdigit():
        name = name[:-1]

    bubble_text = name.replace('×', '*').replace('x', '*').replace('X', '*').replace('＊', '*')
    bubble_text = bubble_text.replace('厘米', 'cm').replace('ＣＭ', 'cm').replace('CM', 'cm')
    if any(keyword in bubble_text for keyword in ['气泡袋', '泡泡袋', '气泡膜袋']):
        if '18*20' in bubble_text:
            return '小泡'
        if '20*30' in bubble_text:
            return '中泡'
        if '25*35' in bubble_text:
            return '大泡'

    mapping = {
        '半高6号': '6.5',
        '半高7号': '7.5',
        '半高8号': '8.5',
        '半高9号': '9.5',
        '半高10号': '10.5',
        '半高11号': '11.5',
        '半高12号': '12.5',
    }
    return mapping.get(name, name)


def extract_pack_item_candidate(item_desc: str) -> str:
    """从采购描述中提取候选包材名"""
    item_desc = (item_desc or '').strip()
    if not item_desc:
        return ''

    # 先按括号 / 分号截断
    candidate = re.split(r'[（(;；]', item_desc, maxsplit=1)[0].strip()

    # 如果还有空格，例如：缠绕膜 年货发货使用 / 气泡柱 透明
    # 先取第一个词，避免把备注一起当成型号
    if ' ' in candidate:
        candidate = candidate.split()[0].strip()

    return normalize_pack_item_name(candidate)


def get_all_pack_item_names(conn):
    rows = conn.execute(
        "SELECT name FROM pack_item ORDER BY sort_no, pack_item_id"
    ).fetchall()
    return [row['name'].strip() for row in rows if (row['name'] or '').strip()]


def get_pack_item_id_by_name(conn, pack_item_name):
    row = conn.execute(
        "SELECT pack_item_id FROM pack_item WHERE name = ? LIMIT 1",
        (pack_item_name,)
    ).fetchone()
    return row['pack_item_id'] if row else None


def get_purchase_row_by_id(conn, purchase_id):
    return conn.execute(
        """
        SELECT purchase_id,
               order_id,
               purchase_date,
               pack_item_id,
               supplier_name,
               bag_count,
               total_quantity,
               total_amount,
               batch_id,
               notes
        FROM purchase_record
        WHERE purchase_id = ?
        LIMIT 1
        """,
        (purchase_id,)
    ).fetchone()


def write_operation_log(conn, request_path, ip_address, operator, operation_group, table_name, record_id, action_type, summary, old_data, new_data):
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute(
        """
        INSERT INTO operation_logs (
            created_at,
            operator,
            operation_group,
            request_path,
            ip_address,
            table_name,
            record_id,
            action_type,
            summary,
            old_data,
            new_data,
            rollback_status,
            rollback_error
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NONE', NULL)
        """,
        (
            created_at,
            operator,
            operation_group,
            request_path,
            ip_address,
            table_name,
            record_id,
            action_type,
            summary,
            json.dumps(old_data, ensure_ascii=False) if old_data is not None else None,
            json.dumps(new_data, ensure_ascii=False) if new_data is not None else None,
        )
    )


def generate_purchase_order_id():
    """订单号为空时自动生成"""
    now_str = datetime.now().strftime('%Y%m%d%H%M%S')
    return f"PCG{now_str}"


def generate_batch_id(conn):
    """自动生成采购批次号：PBYYYYMMDD-001"""
    today_str = datetime.now().strftime('%Y%m%d')
    prefix = f"PB{today_str}-"

    row = conn.execute(
        """
        SELECT batch_id
        FROM purchase_record
        WHERE batch_id LIKE ?
        ORDER BY batch_id DESC
        LIMIT 1
        """,
        (f"{prefix}%",)
    ).fetchone()

    if not row or not row['batch_id']:
        seq = 1
    else:
        last_batch_id = row['batch_id']
        try:
            seq = int(last_batch_id.split('-')[-1]) + 1
        except Exception:
            seq = 1

    return f"{prefix}{seq:03d}"


# ===== 页面 =====
@purchase_bp.route('/')
def purchase():
    print("进入 /purchase/ 路由")
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT pr.purchase_id,
                   pr.order_id,
                   pr.purchase_date,
                   COALESCE(pi.name, '') AS pack_item_name,
                   pr.bag_count,
                   pr.total_quantity AS total_qty,
                   pr.total_amount,
                   pr.batch_id,
                   pr.supplier_name,
                   pr.notes
            FROM purchase_record pr
            LEFT JOIN pack_item pi ON pr.pack_item_id = pi.pack_item_id
            ORDER BY pr.purchase_id DESC
            LIMIT 50
        """).fetchall()
    finally:
        conn.close()

    return render_template('purchase.html', rows=rows)


# ===== 解析采购数据 =====
@purchase_bp.route('/parse_purchase_data', methods=['POST'])
def parse_purchase_data():
    data = request.get_json() or {}
    input_data = data.get('data', '').strip()
    print(f"收到的数据：{input_data}")

    if not input_data:
        return jsonify({
            'success': False,
            'message': '没有可解析的数据'
        }), 400

    lines = [line.strip() for line in input_data.splitlines() if line.strip()]
    if not lines:
        return jsonify({
            'success': False,
            'message': '没有可解析的数据行'
        }), 400

    first_line = lines[0]
    remaining_text = '\n'.join(lines[1:])
    parts = first_line.split('\t')

    purchase_date = parts[0].strip() if len(parts) > 0 else ''
    order_no = parts[1].strip() if len(parts) > 1 else ''
    item_desc = parts[2].strip() if len(parts) > 2 else ''
    total_price = parts[4].strip() if len(parts) > 4 else ''

    piece_qty = ''
    remark = item_desc

    qty_match = re.search(r'(\d+)\s*个', item_desc)
    if qty_match:
        piece_qty = qty_match.group(1)

    pack_item_name = extract_pack_item_candidate(item_desc)

    conn = get_db_connection()
    try:
        known_names = get_all_pack_item_names(conn)
        pack_item_exists = pack_item_name in known_names
    finally:
        conn.close()

    message = '解析成功'
    if pack_item_name and not pack_item_exists:
        message = f'发现新包材型号：{pack_item_name}，请先新增到 pack_item。'

    return jsonify({
        'success': True,
        'message': message,
        'pack_item_exists': pack_item_exists,
        'remaining_text': remaining_text,
        'purchase_date': purchase_date,
        'order_no': order_no,
        'pack_item_name': pack_item_name,
        'piece_qty': piece_qty,
        'total_price': total_price,
        'remark': remark
    })


# ===== 直接新增包材 =====
@purchase_bp.route('/add_pack_item', methods=['POST'])
def add_pack_item():
    data = request.get_json() or {}
    pack_item_name = normalize_pack_item_name((data.get('pack_item_name') or '').strip())

    if not pack_item_name:
        return jsonify({
            'success': False,
            'message': '包材名称不能为空'
        }), 400

    conn = get_db_connection()
    try:
        # 已存在则直接返回
        existing = conn.execute(
            "SELECT pack_item_id, name FROM pack_item WHERE name = ? LIMIT 1",
            (pack_item_name,)
        ).fetchone()

        if existing:
            return jsonify({
                'success': True,
                'message': f'包材已存在：{existing["name"]}',
                'pack_item_id': existing['pack_item_id'],
                'pack_item_name': existing['name'],
                'already_exists': True
            })

        # 新建 sort_no
        row = conn.execute("SELECT COALESCE(MAX(sort_no), 0) + 1 AS next_sort_no FROM pack_item").fetchone()
        next_sort_no = row['next_sort_no'] if row else 1

        cursor = conn.execute(
            """
            INSERT INTO pack_item (name, sort_no, is_active)
            VALUES (?, ?, 1)
            """,
            (pack_item_name, next_sort_no)
        )

        new_pack_item_id = cursor.lastrowid
        new_row = conn.execute(
            "SELECT pack_item_id, name FROM pack_item WHERE pack_item_id = ? LIMIT 1",
            (new_pack_item_id,)
        ).fetchone()

        if new_row is None:
            return jsonify({
                'success': False,
                'message': '新建包材后未找到记录'
            }), 500

        new_data = {
            'pack_item_id': new_row['pack_item_id'],
            'name': new_row['name'],
            'sort_no': next_sort_no,
            'is_active': 1
        }

        write_operation_log(
            conn=conn,
            request_path=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            operator="system",
            operation_group="purchase",
            table_name="pack_item",
            record_id=new_pack_item_id,
            action_type="INSERT",
            summary=f"新增包材：pack_item_id={new_pack_item_id}，name={pack_item_name}",
            old_data=None,
            new_data=new_data,
        )

        conn.commit()

        return jsonify({
            'success': True,
            'message': f'新包材已新增：{pack_item_name}',
            'pack_item_id': new_row['pack_item_id'],
            'pack_item_name': new_row['name'],
            'already_exists': False
        })

    except sqlite3.IntegrityError:
        return jsonify({
            'success': False,
            'message': f'包材已存在或名称重复：{pack_item_name}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'新增包材失败：{str(e)}'
        }), 500
    finally:
        conn.close()


# ===== 提交采购数据 =====
@purchase_bp.route('/submit_purchase', methods=['POST'])
def submit_purchase():
    data = request.get_json() or {}

    purchase_id = (data.get('purchase_id') or '').strip()
    purchase_date = (data.get('purchase_date') or '').strip()
    order_id = (data.get('order_id') or '').strip()
    batch_id = (data.get('batch_id') or '').strip()
    pack_item_name = normalize_pack_item_name((data.get('pack_item_name') or '').strip())
    supplier_name = (data.get('supplier_name') or '').strip()
    notes = (data.get('notes') or '').strip()

    bag_count_raw = str(data.get('bag_count') or '').strip()
    total_quantity_raw = str(data.get('total_quantity') or '').strip()
    total_amount_raw = str(data.get('total_amount') or '').strip()
    per_bag_quantity_raw = str(data.get('per_bag_quantity') or '').strip()

    if not purchase_date:
        return jsonify({'success': False, 'message': '采购日期不能为空'}), 400

    if not pack_item_name:
        return jsonify({'success': False, 'message': '包材型号不能为空'}), 400

    if not supplier_name:
        return jsonify({'success': False, 'message': '供应商不能为空'}), 400

    try:
        bag_count = int(float(bag_count_raw)) if bag_count_raw else 0
    except ValueError:
        return jsonify({'success': False, 'message': '袋数格式不正确'}), 400

    try:
        total_quantity = int(float(total_quantity_raw)) if total_quantity_raw else 0
    except ValueError:
        return jsonify({'success': False, 'message': '总件数格式不正确'}), 400

    try:
        total_amount = float(total_amount_raw) if total_amount_raw else 0.0
    except ValueError:
        return jsonify({'success': False, 'message': '总价格式不正确'}), 400

    # 如果前端没算出总件数，后端兜底
    if total_quantity <= 0 and bag_count > 0 and per_bag_quantity_raw:
        try:
            per_bag_quantity = int(float(per_bag_quantity_raw))
            total_quantity = bag_count * per_bag_quantity
        except ValueError:
            return jsonify({'success': False, 'message': '每袋件数格式不正确'}), 400

    conn = get_db_connection()
    try:
        pack_item_id = get_pack_item_id_by_name(conn, pack_item_name)
        if not pack_item_id:
            return jsonify({
                'success': False,
                'message': f'未找到包材型号：{pack_item_name}。请先新增到 pack_item 后再提交。',
                'need_create_pack_item': True,
                'pack_item_name': pack_item_name
            }), 400

        # --- 更新：如果带有 purchase_id，按主键更新 ---
        if purchase_id:
            if not order_id:
                return jsonify({'success': False, 'message': '修改记录时订单号不能为空'}), 400

            occupied = conn.execute(
                """
                SELECT 1
                FROM purchase_record
                WHERE order_id = ? AND purchase_id <> ?
                LIMIT 1
                """,
                (order_id, purchase_id)
            ).fetchone()
            if occupied:
                return jsonify({'success': False, 'message': f'订单号已被其他记录占用：{order_id}'}), 400

            old_row = get_purchase_row_by_id(conn, purchase_id)
            if old_row is None:
                return jsonify({'success': False, 'message': f'未找到要修改的采购记录：{purchase_id}'}), 404

            conn.execute(
                """
                UPDATE purchase_record
                SET order_id = ?,
                    purchase_date = ?,
                    pack_item_id = ?,
                    supplier_name = ?,
                    bag_count = ?,
                    total_quantity = ?,
                    total_amount = ?,
                    batch_id = ?,
                    notes = ?
                WHERE purchase_id = ?
                """,
                (
                    order_id,
                    purchase_date,
                    pack_item_id,
                    supplier_name,
                    bag_count,
                    total_quantity,
                    total_amount,
                    batch_id,
                    notes,
                    purchase_id
                )
            )

            new_row = get_purchase_row_by_id(conn, purchase_id)
            if new_row is None:
                return jsonify({'success': False, 'message': f'修改后未找到采购记录：{purchase_id}'}), 500

            old_data = dict(old_row)
            new_data = dict(new_row)
            summary = f"修改采购记录：purchase_id={purchase_id}，order_id={old_row['order_id']} -> {new_row['order_id']}"

            write_operation_log(
                conn=conn,
                request_path=request.path,
                ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
                operator="system",
                operation_group="purchase",
                table_name="purchase_record",
                record_id=int(purchase_id),
                action_type="UPDATE",
                summary=summary,
                old_data=old_data,
                new_data=new_data,
            )

            conn.commit()
            return jsonify({
                'success': True,
                'message': '采购记录修改成功',
                'order_id': order_id,
                'batch_id': batch_id,
                'purchase_id': purchase_id
            })

        # --- 新增：purchase_id 为空时插入 ---
        if not order_id:
            order_id = generate_purchase_order_id()
        else:
            duplicated = conn.execute(
                """
                SELECT 1
                FROM purchase_record
                WHERE order_id = ?
                LIMIT 1
                """,
                (order_id,)
            ).fetchone()
            if duplicated:
                return jsonify({'success': False, 'message': f'订单号已存在：{order_id}'}), 400

        if not batch_id:
            batch_id = generate_batch_id(conn)

        cursor = conn.execute("""
            INSERT INTO purchase_record (
                order_id,
                purchase_date,
                pack_item_id,
                supplier_name,
                bag_count,
                total_quantity,
                total_amount,
                batch_id,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id,
            purchase_date,
            pack_item_id,
            supplier_name,
            bag_count,
            total_quantity,
            total_amount,
            batch_id,
            notes
        ))

        new_purchase_id = cursor.lastrowid
        new_row = get_purchase_row_by_id(conn, new_purchase_id)
        if new_row is None:
            return jsonify({'success': False, 'message': '新增后未找到采购记录'}), 500

        new_data = dict(new_row)
        summary = f"新增采购记录：purchase_id={new_purchase_id}，order_id={order_id}"

        write_operation_log(
            conn=conn,
            request_path=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            operator="system",
            operation_group="purchase",
            table_name="purchase_record",
            record_id=new_purchase_id,
            action_type="INSERT",
            summary=summary,
            old_data=None,
            new_data=new_data,
        )

        conn.commit()
        return jsonify({
            'success': True,
            'message': '采购记录提交成功',
            'order_id': order_id,
            'batch_id': batch_id,
            'purchase_id': new_purchase_id
        })
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': f'订单号已存在：{order_id}'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'提交失败：{str(e)}'}), 500
    finally:
        conn.close()
