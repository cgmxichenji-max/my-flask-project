from flask import Blueprint, render_template, redirect, url_for, current_app, session
import json
import os
import sqlite3

from auth.decorators import module_required

logs_bp = Blueprint('logs', __name__, template_folder='../templates')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_database_path():
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return db_path
    return os.path.join(BASE_DIR, 'data', 'main.db')


def get_db_connection():
    db_path = get_database_path()
    conn = sqlite3.connect(db_path)
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


@logs_bp.route('/logs')
@module_required('logs')
def logs():
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


@logs_bp.route('/logs/logout', methods=['POST'])
def logs_logout():
    session.clear()
    return redirect(url_for('auth.login'))


@logs_bp.route('/logs/rollback/<int:log_id>', methods=['POST'])
@module_required('logs')
def rollback_log(log_id):
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
