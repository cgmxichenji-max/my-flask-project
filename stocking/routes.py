from flask import Blueprint, render_template, jsonify, request, current_app
import sqlite3
import os
import json
from datetime import datetime

stocking_bp = Blueprint('stocking', __name__)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_database_path():
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return db_path
    return os.path.join(BASE_DIR, "data", "main.db")


def get_db_connection():
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_stock_in_row_by_id(conn, stock_in_id):
    return conn.execute(
        """
        SELECT stock_in_id,
               purchase_id,
               in_date,
               bag,
               quantity,
               label_copies,
               label_print_count,
               last_print_time,
               notes
        FROM stock_in_record
        WHERE stock_in_id = ?
        LIMIT 1
        """,
        (stock_in_id,)
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


@stocking_bp.route('/')
def stockin_page():
    return render_template('stock_in.html')


@stocking_bp.route('/api/pending')
def get_pending_list():
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            p.purchase_id,
            p.purchase_date,
            p.order_id,
            p.supplier_name,
            p.bag_count AS purchase_bag_count,
            p.total_quantity AS purchase_total_quantity,
            p.notes,
            pi.name AS pack_item_name,

            COALESCE(SUM(s.bag), 0) AS stocked_bag_sum,
            COALESCE(SUM(s.quantity), 0) AS stocked_quantity_sum,

            p.bag_count - COALESCE(SUM(s.bag), 0) AS remaining_bag,
            p.total_quantity - COALESCE(SUM(s.quantity), 0) AS remaining_quantity

        FROM purchase_record p
        LEFT JOIN stock_in_record s
            ON p.purchase_id = s.purchase_id
        LEFT JOIN pack_item pi
            ON p.pack_item_id = pi.pack_item_id
        GROUP BY p.purchase_id
        HAVING remaining_bag > 0 OR remaining_quantity > 0
        ORDER BY p.purchase_date DESC
    """).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])


@stocking_bp.route('/api/stocked')
def get_stocked_list():
    conn = get_db_connection()

    rows = conn.execute("""
        SELECT
            s.stock_in_id,
            s.purchase_id,
            s.in_date,
            s.bag,
            s.quantity,
            s.label_copies,
            s.label_print_count,
            s.last_print_time,
            s.notes,

            p.order_id,
            p.supplier_name,
            p.bag_count AS purchase_bag_count,
            p.total_quantity AS purchase_total_quantity,
            p.notes AS spec_note,
            pi.name AS pack_item_name

        FROM stock_in_record s
        LEFT JOIN purchase_record p
            ON s.purchase_id = p.purchase_id
        LEFT JOIN pack_item pi
            ON p.pack_item_id = pi.pack_item_id
        ORDER BY datetime(s.in_date) DESC, s.stock_in_id DESC
    """).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])


@stocking_bp.route('/api/submit', methods=['POST'])
def submit_stockin():
    data = request.get_json()

    purchase_id = data.get("purchase_id")
    in_date = data.get("in_date")
    bag = data.get("bag")
    quantity = data.get("quantity")
    label_copies = data.get("label_copies")
    notes = data.get("notes", "")

    conn = get_db_connection()
    initial_print_count = 1 if (label_copies or 0) > 0 else 0

    cursor = conn.execute("""
        INSERT INTO stock_in_record (
            purchase_id,
            in_date,
            bag,
            quantity,
            label_copies,
            label_print_count,
            last_print_time,
            notes
        )
        VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'), ?)
    """, (
        purchase_id,
        in_date,
        bag,
        quantity,
        label_copies,
        initial_print_count,
        notes
    ))

    new_stock_in_id = cursor.lastrowid
    new_row = get_stock_in_row_by_id(conn, new_stock_in_id)
    if new_row is None:
        conn.close()
        return jsonify({"ok": False, "message": "入库后未找到记录"}), 500

    write_operation_log(
        conn=conn,
        request_path=request.path,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        operator="system",
        operation_group="stockin",
        table_name="stock_in_record",
        record_id=new_stock_in_id,
        action_type="INSERT",
        summary=f"新增入库记录：stock_in_id={new_stock_in_id}，purchase_id={purchase_id}",
        old_data=None,
        new_data=dict(new_row),
    )

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "入库成功"})


@stocking_bp.route('/api/reprint', methods=['POST'])
def mark_reprint():
    data = request.get_json()

    stock_in_id = data.get("stock_in_id")
    if not stock_in_id:
        return jsonify({"ok": False, "message": "缺少 stock_in_id"}), 400

    conn = get_db_connection()
    old_row = get_stock_in_row_by_id(conn, stock_in_id)
    if old_row is None:
        conn.close()
        return jsonify({"ok": False, "message": f"未找到入库记录：{stock_in_id}"}), 404

    conn.execute("""
        UPDATE stock_in_record
        SET label_print_count = COALESCE(label_print_count, 0) + 1,
            last_print_time = datetime('now', 'localtime')
        WHERE stock_in_id = ?
    """, (stock_in_id,))

    new_row = get_stock_in_row_by_id(conn, stock_in_id)
    if new_row is None:
        conn.close()
        return jsonify({"ok": False, "message": f"补打后未找到入库记录：{stock_in_id}"}), 500

    write_operation_log(
        conn=conn,
        request_path=request.path,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        operator="system",
        operation_group="stockin",
        table_name="stock_in_record",
        record_id=stock_in_id,
        action_type="UPDATE",
        summary=f"补打标签：stock_in_id={stock_in_id}，print_count={old_row['label_print_count']} -> {new_row['label_print_count']}",
        old_data=dict(old_row),
        new_data=dict(new_row),
    )

    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "补打记录已更新"})