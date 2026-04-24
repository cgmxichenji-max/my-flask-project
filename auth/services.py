import os
import sqlite3
from datetime import datetime

from flask import current_app, g
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODULE_KEYS = ('inventory', 'purchase', 'stockin', 'logs', 'wechat_shop')
MODULE_LABELS = {
    'inventory': '库存盘点',
    'purchase': '采购入库',
    'stockin': '操作入库',
    'logs': '操作日志',
    'wechat_shop': '微信小店',
}


def get_database_path():
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return db_path
    return os.path.join(BASE_DIR, 'data', 'main.db')


def get_db_connection():
    conn = sqlite3.connect(get_database_path())
    conn.row_factory = sqlite3.Row
    return conn


def now_text():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def row_to_dict(row):
    return dict(row) if row else None


def get_user_by_id(user_id):
    if not user_id:
        return None
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash, is_admin, is_active,
                   created_at, updated_at, last_login_at
            FROM user
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return row_to_dict(row)


def get_user_by_username(username):
    with get_db_connection() as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash, is_admin, is_active,
                   created_at, updated_at, last_login_at
            FROM user
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
    return row_to_dict(row)


def list_users():
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, username, is_admin, is_active, created_at, updated_at, last_login_at
            FROM user
            ORDER BY id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def authenticate_user(username, password):
    user = get_user_by_username((username or '').strip())
    if not user or not user['is_active']:
        return None
    if not check_password_hash(user['password_hash'], password or ''):
        return None
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE user SET last_login_at = ?, updated_at = ? WHERE id = ?",
            (now_text(), now_text(), user['id']),
        )
        conn.commit()
    return get_user_by_id(user['id'])


def validate_password(password):
    if len(password or '') < 6:
        return '密码长度至少 6 位'
    return ''


def change_user_password(user_id, old_password, new_password):
    error = validate_password(new_password)
    if error:
        return False, error
    user = get_user_by_id(user_id)
    if not user:
        return False, '用户不存在'
    if not check_password_hash(user['password_hash'], old_password or ''):
        return False, '旧密码错误'
    set_user_password(user_id, new_password)
    return True, ''


def set_user_password(user_id, password):
    error = validate_password(password)
    if error:
        return False, error
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE user SET password_hash = ?, updated_at = ? WHERE id = ?",
            (generate_password_hash(password), now_text(), user_id),
        )
        conn.commit()
    return True, ''


def normalize_module_keys(module_keys):
    return [key for key in module_keys if key in MODULE_KEYS]


def get_user_permissions(user_id):
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT module_key FROM user_module_permission WHERE user_id = ? ORDER BY module_key",
            (user_id,),
        ).fetchall()
    return [row['module_key'] for row in rows]


def set_user_permissions(user_id, module_keys, granted_by_user_id=None):
    module_keys = normalize_module_keys(module_keys)
    with get_db_connection() as conn:
        conn.execute("DELETE FROM user_module_permission WHERE user_id = ?", (user_id,))
        granted_at = now_text()
        for module_key in module_keys:
            conn.execute(
                """
                INSERT INTO user_module_permission (
                    user_id, module_key, granted_at, granted_by_user_id
                )
                VALUES (?, ?, ?, ?)
                """,
                (user_id, module_key, granted_at, granted_by_user_id),
            )
        conn.commit()


def create_user(username, password, is_admin, module_keys, granted_by_user_id=None):
    username = (username or '').strip()
    if not username:
        return False, '用户名不能为空', None
    error = validate_password(password)
    if error:
        return False, error, None
    if get_user_by_username(username):
        return False, '用户名已存在', None

    now = now_text()
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO user (
                username, password_hash, is_admin, is_active,
                created_at, updated_at, last_login_at
            )
            VALUES (?, ?, ?, 1, ?, ?, NULL)
            """,
            (username, generate_password_hash(password), 1 if is_admin else 0, now, now),
        )
        conn.commit()
        user_id = cursor.lastrowid

    if not is_admin:
        set_user_permissions(user_id, module_keys, granted_by_user_id)
    return True, '', user_id


def update_user(user_id, is_admin, is_active, module_keys, current_user_id, reset_password=''):
    user = get_user_by_id(user_id)
    if not user:
        return False, '用户不存在'

    if user_id == current_user_id and (not is_admin or not is_active):
        return False, '不能取消自己的管理员身份或禁用自己'

    if reset_password:
        error = validate_password(reset_password)
        if error:
            return False, error

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE user SET is_admin = ?, is_active = ?, updated_at = ? WHERE id = ?",
            (1 if is_admin else 0, 1 if is_active else 0, now_text(), user_id),
        )
        if reset_password:
            conn.execute(
                "UPDATE user SET password_hash = ?, updated_at = ? WHERE id = ?",
                (generate_password_hash(reset_password), now_text(), user_id),
            )
        conn.commit()

    if is_admin:
        set_user_permissions(user_id, [], current_user_id)
    else:
        set_user_permissions(user_id, module_keys, current_user_id)
    return True, ''


def has_module_permission(user, module_key):
    if not user or not user.get('is_active'):
        return False
    if user.get('is_admin'):
        return True
    if module_key not in MODULE_KEYS:
        return False
    return module_key in get_user_permissions(user['id'])


def get_current_operator_name():
    user = getattr(g, 'current_user', None)
    if user and user.get('username'):
        return user['username']
    return 'anonymous'
