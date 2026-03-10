from flask import Blueprint, render_template, jsonify, request
import sqlite3
import os

stocking_bp = Blueprint('stocking', __name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "packaging.db")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


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

    conn.execute("""
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
    conn.execute("""
        UPDATE stock_in_record
        SET label_print_count = COALESCE(label_print_count, 0) + 1,
            last_print_time = datetime('now', 'localtime')
        WHERE stock_in_id = ?
    """, (stock_in_id,))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "message": "补打记录已更新"})