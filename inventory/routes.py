from flask import Blueprint, render_template, request, redirect, url_for
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "packaging.db")

inventory_bp = Blueprint('inventory', __name__, template_folder='../templates')


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


@inventory_bp.route('/')
def inventory():
    conn = get_db_connection()
    try:
        items = conn.execute("""
            SELECT pack_item_id, name
            FROM pack_item
            WHERE is_active = 1
            ORDER BY
                CASE
                    WHEN name = '大泡' THEN 2
                    WHEN name = '中泡' THEN 3
                    WHEN name = '小泡' THEN 4
                    WHEN name GLOB '[0-9]*' THEN 1
                    ELSE 5
                END,
                CAST(name AS REAL),
                pack_item_id
        """).fetchall()

        N = 30
        times = conn.execute(f"""
            SELECT stocktake_ts
            FROM pack_stock_snapshot
            GROUP BY stocktake_ts
            ORDER BY stocktake_ts DESC
            LIMIT {N}
        """).fetchall()
        time_list = [r["stocktake_ts"] for r in times]

        if time_list:
            placeholders = ",".join(["?"] * len(time_list))
            rows = conn.execute(f"""
                SELECT stocktake_ts, spec, qty
                FROM pack_stock_snapshot
                WHERE stocktake_ts IN ({placeholders})
            """, time_list).fetchall()
        else:
            rows = []

        col_specs = [r["name"] for r in items]
        table = {t: {spec: "" for spec in col_specs} for t in time_list}
        for r in rows:
            t = r["stocktake_ts"]
            spec = r["spec"]
            qty = r["qty"]
            if t in table and spec in table[t]:
                table[t][spec] = qty

        return render_template(
            "inventory.html",
            items=items,
            col_specs=col_specs,
            time_list=time_list,
            table=table
        )
    finally:
        conn.close()


@inventory_bp.route('/add', methods=['POST'])
@inventory_bp.route('/add_inventory', methods=['POST'])
def add_inventory():
    pack_item_id = request.form.get('pack_item_id', '').strip()
    quantity = request.form.get('quantity', '').strip()
    stocktake_ts = request.form.get('stocktake_ts', '').strip()

    if stocktake_ts:
        stocktake_ts = stocktake_ts.replace('T', ' ')
        if len(stocktake_ts) == 16:
            stocktake_ts += ':00'

    if not stocktake_ts or not pack_item_id or quantity == '':
        return "输入不能为空", 400

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT name FROM pack_item WHERE pack_item_id = ?",
            (pack_item_id,)
        ).fetchone()
        if row is None:
            return "包材不存在", 400

        spec = row["name"]
        conn.execute("""
            INSERT INTO pack_stock_snapshot (stocktake_ts, spec, qty, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(stocktake_ts, spec)
            DO UPDATE SET
                qty = excluded.qty,
                source = excluded.source
        """, (stocktake_ts, spec, quantity, "manual"))

        conn.commit()
        return redirect(url_for('inventory.inventory', pack_item_id=pack_item_id, quantity=quantity))
    finally:
        conn.close()
