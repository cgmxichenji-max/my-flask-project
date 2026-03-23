from flask import Blueprint, render_template, request, redirect, url_for, jsonify
import sqlite3
import os
from datetime import datetime
import json

from flask import current_app

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_database_path():
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return db_path
    return os.path.join(BASE_DIR, "data", "main.db")

inventory_bp = Blueprint('inventory', __name__, template_folder='../templates')


def get_db_connection():
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def get_snapshot_row(conn, stocktake_ts, spec):
    return conn.execute(
        """
        SELECT id, stocktake_ts, spec, qty, source
        FROM pack_stock_snapshot
        WHERE stocktake_ts = ? AND spec = ?
        """,
        (stocktake_ts, spec)
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

        # 一、区间内总入库袋数：仍然按起点~终点统计
        stock_in_row = conn.execute(
            """
            SELECT COALESCE(SUM(s.bag), 0) AS stock_in_bag
            FROM stock_in_record s
            JOIN purchase_record p
              ON s.purchase_id = p.purchase_id
            WHERE p.pack_item_id = ?
              AND s.in_date > ?
              AND s.in_date <= ?
            """,
            (pack_item_id, start_ts, end_ts)
        ).fetchone()

        stock_in_bag = int(stock_in_row['stock_in_bag'] or 0)
        consumed_qty = start_qty + stock_in_bag - end_qty

        # 二、最近一条入库记录：只要求在终点时间之前，不再受起点时间限制
        latest_row = conn.execute(
            """
            SELECT
                s.stock_in_id,
                s.in_date,
                s.bag,
                s.quantity
            FROM stock_in_record s
            JOIN purchase_record p
              ON s.purchase_id = p.purchase_id
            WHERE p.pack_item_id = ?
              AND s.in_date <= ?
            ORDER BY s.in_date DESC, s.stock_in_id DESC
            LIMIT 1
            """,
            (pack_item_id, end_ts)
        ).fetchone()

        estimated_piece = 0
        piece_per_bag = None
        latest_in_date = None

        if latest_row is not None:
            latest_bag = int(latest_row['bag'] or 0)
            latest_quantity = int(latest_row['quantity'] or 0)
            latest_in_date = latest_row['in_date']

            if latest_bag > 0:
                piece_per_bag = latest_quantity / latest_bag
                estimated_piece = round(consumed_qty * piece_per_bag)

        return jsonify({
            "ok": True,
            "result": {
                "start_qty": start_qty,
                "end_qty": end_qty,
                "stock_in_qty": stock_in_bag,
                "consumed_qty": consumed_qty,
                "estimated_piece": estimated_piece,
                "piece_per_bag": piece_per_bag,
                "latest_in_date": latest_in_date
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
        old_row = get_snapshot_row(conn, stocktake_ts, spec)

        conn.execute("""
            INSERT INTO pack_stock_snapshot (stocktake_ts, spec, qty, source)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(stocktake_ts, spec)
            DO UPDATE SET
                qty = excluded.qty,
                source = excluded.source
        """, (stocktake_ts, spec, quantity, "manual"))

        new_row = get_snapshot_row(conn, stocktake_ts, spec)
        if new_row is None:
            raise RuntimeError("盘点快照写入后未找到对应记录")

        new_data = {
            "id": new_row["id"],
            "stocktake_ts": new_row["stocktake_ts"],
            "spec": new_row["spec"],
            "qty": new_row["qty"],
            "source": new_row["source"],
        }

        if old_row is None:
            action_type = "INSERT"
            old_data = None
            summary = f"新增盘点记录：{spec} @ {stocktake_ts} -> {new_row['qty']}"
        else:
            action_type = "UPDATE"
            old_data = {
                "id": old_row["id"],
                "stocktake_ts": old_row["stocktake_ts"],
                "spec": old_row["spec"],
                "qty": old_row["qty"],
                "source": old_row["source"],
            }
            summary = f"修改盘点记录：{spec} @ {stocktake_ts}，{old_row['qty']} -> {new_row['qty']}"

        write_operation_log(
            conn=conn,
            request_path=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            operator="system",
            operation_group="inventory",
            table_name="pack_stock_snapshot",
            record_id=new_row["id"],
            action_type=action_type,
            summary=summary,
            old_data=old_data,
            new_data=new_data,
        )

        conn.commit()
        return redirect(url_for('inventory.inventory', pack_item_id=pack_item_id, quantity=quantity))
    finally:
        conn.close()
