import os
import sqlite3
from datetime import datetime

from flask import current_app
from werkzeug.security import generate_password_hash


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


def ensure_tables():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_module_permission (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                module_key TEXT NOT NULL,
                granted_at TEXT NOT NULL,
                granted_by_user_id INTEGER,
                UNIQUE(user_id, module_key),
                FOREIGN KEY (user_id) REFERENCES user(id)
            )
            """
        )
        conn.commit()


def ensure_default_admin():
    with get_db_connection() as conn:
        admin_exists = conn.execute(
            "SELECT 1 FROM user WHERE is_admin = 1 LIMIT 1"
        ).fetchone()
        if admin_exists:
            return

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            """
            INSERT INTO user (
                username, password_hash, is_admin, is_active,
                created_at, updated_at, last_login_at
            )
            VALUES (?, ?, 1, 1, ?, ?, NULL)
            """,
            (
                'GeorgeJi',
                generate_password_hash('GeorgeJi123456'),
                now,
                now,
            ),
        )
        conn.commit()
        print("  >>> 首次启动：管理员 GeorgeJi 使用临时密码 GeorgeJi123456，请立刻登录后修改")
