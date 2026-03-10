from flask import Blueprint, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "packaging.db")

inventory_bp = Blueprint('inventory', __name__, template_folder='../templates')


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def parse_ts(value):
    if not value:
        return None
    value = value.strip().replace('T', ' ')
    if len(value) == 16:
        value += ':00'
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


def format_duration_label(start_dt, end_dt):
    total_seconds = int((end_dt - start_dt).total_seconds())
    if total_seconds < 0:
        total_seconds = 0

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    if hours == 0 and minutes == 0:
        return f"间隔 {days} 天"
    if minutes == 0:
        return f"间隔 {days} 天 {hours} 小时"
    return f"间隔 {days} 天 {hours} 小时 {minutes} 分"

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

@inventory_bp.route('/api/analysis/options', methods=['POST'])
def analysis_options():
    data = request.get_json(silent=True) or {}
    pack_item_id = str(data.get('pack_item_id', '')).strip()
    stocktake_ts_raw = str(data.get('stocktake_ts', '')).strip()

    if not pack_item_id or not stocktake_ts_raw:
        return jsonify({"ok": False, "error": "缺少包材或盘点时间"}), 400

    try:
        end_dt = parse_ts(stocktake_ts_raw)
        end_ts = end_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return jsonify({"ok": False, "error": "盘点时间格式错误"}), 400

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT name FROM pack_item WHERE pack_item_id = ?",
            (pack_item_id,)
        ).fetchone()
        if row is None:
            return jsonify({"ok": False, "error": "包材不存在"}), 400

        spec = row['name']
        rows = conn.execute(
            """
            SELECT stocktake_ts, qty
            FROM pack_stock_snapshot
            WHERE spec = ?
              AND stocktake_ts < ?
            ORDER BY stocktake_ts DESC
            """,
            (spec, end_ts)
        ).fetchall()

        options = []
        for r in rows:
            start_ts = r['stocktake_ts']
            try:
                start_dt = parse_ts(start_ts)
            except Exception:
                continue

            label = f"{start_ts}（{format_duration_label(start_dt, end_dt)}）"
            options.append({
                "stocktake_ts": start_ts,
                "label": label
            })

        return jsonify({"ok": True, "options": options})
    finally:
        conn.close()


@inventory_bp.route('/api/analysis/run', methods=['POST'])
def analysis_run():
    data = request.get_json(silent=True) or {}
    pack_item_id = str(data.get('pack_item_id', '')).strip()
    start_stocktake_ts_raw = str(data.get('start_stocktake_ts', '')).strip()
    end_stocktake_ts_raw = str(data.get('end_stocktake_ts', '')).strip()

    if not pack_item_id or not start_stocktake_ts_raw or not end_stocktake_ts_raw:
        return jsonify({"ok": False, "error": "缺少分析参数"}), 400

    try:
        start_dt = parse_ts(start_stocktake_ts_raw)
        end_dt = parse_ts(end_stocktake_ts_raw)
        start_ts = start_dt.strftime('%Y-%m-%d %H:%M:%S')
        end_ts = end_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return jsonify({"ok": False, "error": "时间格式错误"}), 400

    if start_dt >= end_dt:
        return jsonify({"ok": False, "error": "起点时间必须早于终点时间"}), 400

    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT name FROM pack_item WHERE pack_item_id = ?",
            (pack_item_id,)
        ).fetchone()
        if row is None:
            return jsonify({"ok": False, "error": "包材不存在"}), 400

        spec = row['name']

        start_row = conn.execute(
            """
            SELECT qty
            FROM pack_stock_snapshot
            WHERE spec = ? AND stocktake_ts = ?
            """,
            (spec, start_ts)
        ).fetchone()

        end_row = conn.execute(
            """
            SELECT qty
            FROM pack_stock_snapshot
            WHERE spec = ? AND stocktake_ts = ?
            """,
            (spec, end_ts)
        ).fetchone()

        if start_row is None:
            return jsonify({"ok": False, "error": "起点库存记录不存在"}), 400
        if end_row is None:
            return jsonify({"ok": False, "error": "终点库存记录不存在"}), 400

        start_qty = int(start_row['qty'] or 0)
        end_qty = int(end_row['qty'] or 0)

        stock_in_row = conn.execute(
            """
            SELECT COALESCE(SUM(s.quantity), 0) AS stock_in_qty
            FROM stock_in_record s
            JOIN purchase_record p
              ON s.purchase_id = p.purchase_id
            WHERE p.pack_item_id = ?
              AND s.in_date > ?
              AND s.in_date <= ?
            """,
            (pack_item_id, start_ts, end_ts)
        ).fetchone()

        stock_in_qty = int(stock_in_row['stock_in_qty'] or 0)
        consumed_qty = start_qty + stock_in_qty - end_qty

        return jsonify({
            "ok": True,
            "result": {
                "start_qty": start_qty,
                "end_qty": end_qty,
                "stock_in_qty": stock_in_qty,
                "consumed_qty": consumed_qty
            }
        })
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
