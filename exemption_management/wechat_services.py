import sqlite3
from datetime import datetime

from auth.services import get_db_connection


WECHAT_STATUSES = {
    'active': '豁免中',
    'ended': '已结束',
}

# 2026-09-16 微信小店“设置豁免列表”三页截图核对结果。
# “待结束”在截至时间之前仍视为豁免中，故以 active 入库。
INITIAL_WECHAT_ROWS = [
    ('带货者', '噜可夫妇在荷兰', 'wx5c5172ca33abb4f8', 'active', '2026-09-04 20:44', '2026-09-30 23:59'),
    ('带货者', '意大利媳妇琳达', 'wx9e56fb8d2fca740e', 'active', '2026-08-20 08:06', '2026-10-20 23:59'),
    ('带货机构', '仙梓文化', 'wxe626dbca04cfa21d', 'active', '2026-09-15 11:07', '2026-12-31 23:59'),
    ('带货者', '糖糖一家在美国', 'wx3d7981dafbeec8b5', 'active', '2026-07-16 21:51', '2027-08-31 23:59'),
    ('带货者', '星彤一家', 'wxb764b4802b303376', 'active', '2026-09-03 19:04', '2027-09-30 23:59'),
    ('带货者', '大兴爱琳娜-我中意你', 'wx6a516ad2f06c630e', 'active', '2026-07-18 16:35', '2027-12-31 23:59'),
    ('带货者', '大香发现新西兰', 'wx3097c51c3c8d821f', 'active', '2026-07-21 10:44', '2027-12-31 23:59'),
    ('带货者', '馒头哥在美国主号', 'wx0d6d2284fae90bdc', 'active', '2026-07-15 05:59', '2028-01-01 23:59'),
    ('带货者', '馒头哥在美国', 'wx9ddf05d490124662', 'active', '2026-07-15 06:00', '2028-01-01 23:59'),
    ('带货者', '萌主在澳洲', 'wx47ba32118644db87', 'active', '2026-07-21 12:18', '2028-03-31 23:59'),
    ('带货者', '小囡和大维新西兰农场主日常', 'wxfa3668a7e80d7c87', 'active', '2026-07-20 12:27', '2028-04-14 23:59'),
    ('带货者', '北大小果在美国', 'wxf06b90144e778620', 'active', '2026-07-14 11:52', '2028-07-06 23:59'),
    ('带货者', '馒头哥一家美国', 'wxe3005e36567c244a', 'active', '2026-07-15 06:00', '2028-08-01 23:59'),
    ('带货者', '北大小果在美国农村', 'wx76cf0fa2803c5da1', 'active', '2026-07-14 11:53', '2028-08-11 23:59'),
    ('带货者', '海芋&kevin的澳洲生活', 'wxaa092f676ac47ba3', 'active', '2026-07-12 13:51', '2029-01-02 23:59'),
    ('带货者', '小潘一家在美国', 'wx02436fab503d5092', 'active', '2026-09-09 17:52', '2026-09-16 23:59'),
    ('带货者', '法拉港靓货', 'wx5d5d31fd1800c515', 'ended', '2026-07-19 16:31', '2026-08-31 23:59'),
    ('带货者', '素玙棉麻原创女装', 'wx86ed008227741b0c', 'ended', '2026-07-19 16:40', '2026-08-31 23:59'),
    ('带货者', '佳佳在巴黎', 'wxc8425ab8521428d7', 'ended', '2026-07-19 16:42', '2026-08-31 23:59'),
    ('带货者', '华姐的美国生活', 'wxd06bfe3f7f9cce89', 'ended', '2026-07-23 20:48', '2026-08-31 23:59'),
    ('带货者', '华姐的美国新生活', 'wxa433bc90e380269f', 'ended', '2026-07-23 20:50', '2026-08-31 23:59'),
]


def _now_text():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def ensure_wechat_table():
    with get_db_connection() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS wechat_creator_exemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_type TEXT NOT NULL DEFAULT '',
                creator_nickname TEXT NOT NULL DEFAULT '',
                creator_uid TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                start_at TEXT NOT NULL DEFAULT '',
                end_at TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE UNIQUE INDEX IF NOT EXISTS idx_wechat_creator_exemptions_unique
            ON wechat_creator_exemptions (creator_uid, start_at, end_at, source)
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS wechat_creator_exemption_seed_state (
                seed_key TEXT PRIMARY KEY,
                seeded_at TEXT NOT NULL
            )
        ''')
        seeded = conn.execute(
            "SELECT 1 FROM wechat_creator_exemption_seed_state WHERE seed_key = 'screenshots_20260916'"
        ).fetchone()
        if not seeded:
            current_time = _now_text()
            for creator_type, nickname, uid, status, start_at, end_at in INITIAL_WECHAT_ROWS:
                conn.execute('''
                    INSERT OR IGNORE INTO wechat_creator_exemptions (
                        creator_type, creator_nickname, creator_uid, status,
                        start_at, end_at, source, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'screenshot', ?, ?)
                ''', (creator_type, nickname, uid, status, start_at, end_at, current_time, current_time))
            conn.execute(
                "INSERT INTO wechat_creator_exemption_seed_state (seed_key, seeded_at) VALUES ('screenshots_20260916', ?)",
                (current_time,),
            )
        conn.commit()


def _normalize_status(value):
    value = (value or '').strip()
    if value not in WECHAT_STATUSES:
        raise ValueError('豁免状态不正确')
    return value


def _normalize_datetime(value, field_label, end_of_day=False):
    value = (value or '').strip().replace('T', ' ')
    if not value:
        return ''
    if len(value) == 10:
        value += ' 23:59' if end_of_day else ' 00:00'
    for fmt in ('%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%d %H:%M')
        except ValueError:
            pass
    raise ValueError(f'{field_label}格式应为 YYYY-MM-DD HH:MM')


def _payload(data):
    creator_type = (data.get('creator_type') or '').strip()
    creator_nickname = (data.get('creator_nickname') or '').strip()
    creator_uid = (data.get('creator_uid') or '').strip()
    status = _normalize_status(data.get('status'))
    start_at = _normalize_datetime(data.get('start_at'), '生效时间')
    end_at = _normalize_datetime(data.get('end_at'), '结束时间', end_of_day=True)
    if not creator_type or not creator_nickname or not creator_uid:
        raise ValueError('合作类型、合作对象昵称和合作对象ID不能为空')
    if not start_at or not end_at:
        raise ValueError('生效时间和结束时间不能为空')
    if start_at > end_at:
        raise ValueError('生效时间不能晚于结束时间')
    return {
        'creator_type': creator_type,
        'creator_nickname': creator_nickname,
        'creator_uid': creator_uid,
        'status': status,
        'start_at': start_at,
        'end_at': end_at,
    }


def _row_to_dict(row):
    item = dict(row)
    item['status_label'] = WECHAT_STATUSES[item['status']]
    return item


def list_wechat_exemptions(filters):
    ensure_wechat_table()
    where, params = ['1 = 1'], []
    keyword = (filters.get('keyword') or '').strip()
    if keyword:
        like = f'%{keyword}%'
        where.append('(creator_type LIKE ? OR creator_nickname LIKE ? OR creator_uid LIKE ?)')
        params.extend([like, like, like])
    status = (filters.get('status') or '').strip()
    if status:
        where.append('status = ?')
        params.append(_normalize_status(status))
    for query_key, column, suffix in (
        ('start_from', 'start_at', ' 00:00'), ('start_to', 'start_at', ' 23:59'),
        ('end_from', 'end_at', ' 00:00'), ('end_to', 'end_at', ' 23:59'),
    ):
        value = (filters.get(query_key) or '').strip()
        if value:
            _normalize_datetime(value, '筛选日期', end_of_day=suffix == ' 23:59')
            operator = '>=' if query_key.endswith('from') else '<='
            where.append(f'{column} {operator} ?')
            params.append(value + suffix)
    with get_db_connection() as conn:
        rows = conn.execute(f'''
            SELECT id, creator_type, creator_nickname, creator_uid, status,
                   start_at, end_at, source, created_at, updated_at
            FROM wechat_creator_exemptions
            WHERE {' AND '.join(where)}
            ORDER BY CASE status WHEN 'active' THEN 0 ELSE 1 END, end_at DESC, start_at DESC, id DESC
        ''', params).fetchall()
    return [_row_to_dict(row) for row in rows]


def _get(record_id, conn):
    row = conn.execute('''
        SELECT id, creator_type, creator_nickname, creator_uid, status,
               start_at, end_at, source, created_at, updated_at
        FROM wechat_creator_exemptions WHERE id = ?
    ''', (record_id,)).fetchone()
    if not row:
        raise ValueError('记录不存在')
    return _row_to_dict(row)


def create_wechat_exemption(data):
    ensure_wechat_table()
    payload = _payload(data)
    current_time = _now_text()
    with get_db_connection() as conn:
        cursor = conn.execute('''
            INSERT INTO wechat_creator_exemptions (
                creator_type, creator_nickname, creator_uid, status, start_at, end_at,
                source, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'manual', ?, ?)
        ''', (*payload.values(), current_time, current_time))
        conn.commit()
        return _get(cursor.lastrowid, conn)


def update_wechat_exemption(record_id, data):
    ensure_wechat_table()
    payload = _payload(data)
    with get_db_connection() as conn:
        cursor = conn.execute('''
            UPDATE wechat_creator_exemptions
            SET creator_type = ?, creator_nickname = ?, creator_uid = ?, status = ?,
                start_at = ?, end_at = ?, updated_at = ?
            WHERE id = ?
        ''', (*payload.values(), _now_text(), record_id))
        if cursor.rowcount == 0:
            raise ValueError('记录不存在')
        conn.commit()
        return _get(record_id, conn)


def stop_wechat_exemption(record_id, end_at):
    ensure_wechat_table()
    end_at = _normalize_datetime(end_at, '结束时间', end_of_day=True) or datetime.now().strftime('%Y-%m-%d %H:%M')
    with get_db_connection() as conn:
        cursor = conn.execute('''
            UPDATE wechat_creator_exemptions
            SET status = 'ended', end_at = ?, updated_at = ? WHERE id = ?
        ''', (end_at, _now_text(), record_id))
        if cursor.rowcount == 0:
            raise ValueError('记录不存在')
        conn.commit()
        return _get(record_id, conn)


def delete_wechat_exemption(record_id):
    ensure_wechat_table()
    with get_db_connection() as conn:
        cursor = conn.execute('DELETE FROM wechat_creator_exemptions WHERE id = ?', (record_id,))
        conn.commit()
    if cursor.rowcount == 0:
        raise ValueError('记录不存在')
