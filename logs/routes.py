from flask import Blueprint, render_template, redirect, url_for, request, session
import json
import os
import sqlite3

logs_bp = Blueprint('logs', __name__, template_folder='../templates')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, 'data', 'packaging.db')

LOGS_PASSWORD = 'chenxi98'
LOGS_SESSION_KEY = 'logs_authenticated'


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_primary_key_name(table_name):
    primary_key_map = {
        'purchase_record': 'purchase_id',
        'pack_item': 'pack_item_id',
        'pack_stock_snapshot': 'rowid',
        'stock_in_record': 'stock_in_id',
    }
    return primary_key_map.get(table_name, 'id')


def is_logs_authenticated():
    return session.get(LOGS_SESSION_KEY) is True


def render_logs_login_page(error_message=''):
    error_html = f'<p style="color:#c62828;margin:0 0 12px;">{error_message}</p>' if error_message else ''
    return f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>操作日志验证</title>
        <style>
            body {{
                font-family: "Microsoft YaHei", Arial, sans-serif;
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f5f5f5;
            }}
            .card {{
                width: 360px;
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.12);
                padding: 28px;
            }}
            h1 {{
                margin: 0 0 18px;
                font-size: 24px;
            }}
            label {{
                display: block;
                margin-bottom: 8px;
                font-size: 14px;
            }}
            input[type="password"] {{
                width: 100%;
                box-sizing: border-box;
                padding: 10px 12px;
                font-size: 14px;
                margin-bottom: 14px;
            }}
            button {{
                width: 100%;
                padding: 10px 12px;
                font-size: 14px;
                border: none;
                background: #2e7d32;
                color: #fff;
                border-radius: 6px;
                cursor: pointer;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>操作日志验证</h1>
            {error_html}
            <form method="post" action="/logs/login">
                <label for="logs_password">请输入密码</label>
                <input id="logs_password" name="password" type="password" autocomplete="current-password">
                <button type="submit">进入操作日志</button>
            </form>
        </div>
    </body>
    </html>
    """


@logs_bp.route('/logs/login', methods=['GET', 'POST'])
def logs_login():
    if request.method == 'POST':
        password = (request.form.get('password') or '').strip()
        if password == LOGS_PASSWORD:
            session[LOGS_SESSION_KEY] = True
            return redirect(url_for('logs.logs'))
        return render_logs_login_page('密码错误')

    if is_logs_authenticated():
        return redirect(url_for('logs.logs'))
    return render_logs_login_page()


@logs_bp.route('/logs/logout', methods=['POST'])
def logs_logout():
    session.pop(LOGS_SESSION_KEY, None)
    return redirect(url_for('logs.logs_login'))


@logs_bp.route('/logs')
def logs():
    if not is_logs_authenticated():
        return redirect(url_for('logs.logs_login'))
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                created_at,
                operator,
                operation_group,
                request_path,
                ip_address,
                table_name,
                record_id,
                action_type,
                summary,
                rollback_status
            FROM operation_logs
            ORDER BY id DESC
            """
        ).fetchall()
    finally:
        conn.close()

    return render_template('logs.html', rows=rows)


@logs_bp.route('/logs/rollback/<int:log_id>', methods=['POST'])
def rollback_log(log_id):
    if not is_logs_authenticated():
        return redirect(url_for('logs.logs_login'))
    conn = get_db_connection()
    try:
        log_row = conn.execute(
            """
            SELECT
                id,
                table_name,
                record_id,
                action_type,
                old_data,
                rollback_status
            FROM operation_logs
            WHERE id = ?
            """,
            (log_id,)
        ).fetchone()

        if log_row is None or log_row['rollback_status'] != 'NONE':
            return redirect(url_for('logs.logs'))

        table_name = (log_row['table_name'] or '').strip()
        record_id = log_row['record_id']
        action_type = (log_row['action_type'] or '').strip().upper()
        old_data_raw = log_row['old_data']

        if not table_name:
            raise ValueError('table_name 为空')
        primary_key_name = get_primary_key_name(table_name)
        old_data = json.loads(old_data_raw) if old_data_raw else None

        if action_type == 'INSERT':
            cur = conn.execute(
                f"DELETE FROM {table_name} WHERE {primary_key_name} = ?",
                (record_id,)
            )
            if cur.rowcount == 0:
                raise ValueError('目标记录不存在')
        elif action_type == 'UPDATE':
            if not old_data:
                raise ValueError('old_data 为空')
            update_fields = {
                key: value
                for key, value in old_data.items()
                if key != primary_key_name
            }
            if not update_fields:
                raise ValueError('old_data 无可恢复字段')

            set_clause = ', '.join([f"{key} = ?" for key in update_fields.keys()])
            values = list(update_fields.values()) + [record_id]
            cur = conn.execute(
                f"UPDATE {table_name} SET {set_clause} WHERE {primary_key_name} = ?",
                values
            )
            if cur.rowcount == 0:
                raise ValueError('目标记录不存在')
        elif action_type == 'DELETE':
            if not old_data:
                raise ValueError('old_data 为空')
            columns = list(old_data.keys())
            if primary_key_name not in columns:
                raise ValueError(f'old_data 缺少主键字段: {primary_key_name}')
            placeholders = ', '.join(['?'] * len(columns))
            column_clause = ', '.join(columns)
            values = [old_data[column] for column in columns]
            conn.execute(
                f"INSERT INTO {table_name} ({column_clause}) VALUES ({placeholders})",
                values
            )
        else:
            raise ValueError(f'不支持的 action_type: {action_type}')

        conn.execute(
            """
            UPDATE operation_logs
            SET rollback_status = 'DONE',
                rollback_error = NULL
            WHERE id = ?
            """,
            (log_id,)
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        conn.execute(
            """
            UPDATE operation_logs
            SET rollback_status = 'FAILED',
                rollback_error = ?
            WHERE id = ?
            """,
            (str(exc), log_id)
        )
        conn.commit()
    finally:
        conn.close()

    return redirect(url_for('logs.logs'))
