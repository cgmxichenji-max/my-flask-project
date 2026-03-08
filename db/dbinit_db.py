from .connection import get_connection

def init_database():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            quantity REAL,
            remark TEXT
        )
    """)

    conn.commit()
    conn.close()
