from flask import Blueprint, render_template, request, redirect, url_for, current_app
import os
import sqlite3

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


# ===== 模块首页 =====

@invoicing_bp.route('/')
@module_required('invoicing')
def index():
    return render_template('invoicing_index.html')


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
