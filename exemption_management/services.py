import sqlite3
from datetime import datetime

from auth.services import get_db_connection


BRANDS = {
    'chantelle': '香娜露儿',
    'mulianman': '慕莲蔓',
}

STATUSES = {
    'active': '生效中',
    'ended': '已结束',
}

INITIAL_CHANTELLE_ROWS = [
    ('抖音火山', '槿头媳妇在荷兰', '80394817841', 'active', '2026-06-11', '2027-06-06'),
    ('抖音火山', '多多在美国💜直播返场', '1223134245050462', 'active', '2026-06-09', '2027-06-03'),
    ('抖音火山', '槿头栀子荷兰之旅', '159870621319596', 'active', '2026-06-07', '2027-06-07'),
    ('抖音火山', '槿头栀子哥粉丝号', '749195393775816', 'active', '2026-06-07', '2027-06-07'),
    ('抖音火山', '小汤圆杂物社', '652458384692736', 'active', '2026-06-07', '2027-06-07'),
    ('抖音火山', '槿头栀子哥分享', '3503492585236779', 'active', '2026-06-07', '2027-06-07'),
    ('抖音火山', '去爬山吗', '7485656288120439868', 'active', '2026-06-04', '2027-06-06'),
    ('抖音火山', '槿头栀子全球漫游-南桥', '7415146958724170810', 'active', '2026-05-29', '2027-01-02'),
    ('抖音火山', '槿头栀子在旅行', '123574915439271', 'active', '2026-05-29', '2027-01-02'),
    ('抖音火山', '123', '51431592792', 'active', '2026-05-29', '2027-01-02'),
    ('抖音火山', '槿头栀子全球旅行', '64258397949', 'active', '2026-05-29', '2027-01-02'),
    ('抖音火山', '槿头栀子游地球-南乔', '7599868757226505265', 'active', '2026-05-29', '2027-01-02'),
    ('抖音火山', '槿头栀子环游地球', '7600243479125476411', 'active', '2026-05-29', '2027-01-02'),
    ('抖音火山', '槿头栀子游世界', '7580249395830441009', 'active', '2026-05-29', '2027-01-02'),
    ('抖音火山', '大罐头🇺🇸周游列国', '449047759426736', 'active', '2026-05-29', '2027-01-03'),
    ('抖音火山', '大罐头环游世界各地', '1467206536280651', 'active', '2026-05-29', '2027-01-03'),
    ('抖音火山', '槿头栀子带你看世界', '917467379012952', 'active', '2026-05-29', '2027-01-03'),
    ('抖音火山', '大罐头环游世界', '913027001497456', 'active', '2026-05-29', '2027-01-03'),
    ('抖音火山', '槿头栀子世界游', '312701126449651', 'active', '2026-05-29', '2027-01-03'),
    ('抖音火山', '槿头栀子日常分享', '1883882621250714', 'active', '2026-05-29', '2027-01-03'),
    ('抖音火山', '多多逛美国', '3811345180394618', 'active', '2026-04-29', '2027-04-30'),
    ('抖音火山', '多多在美国💗全球臻品', '2348993299352606', 'active', '2026-04-29', '2027-04-17'),
    ('抖音火山', '多多在美国💗日常分享', '3396842150693930', 'active', '2026-04-29', '2027-04-17'),
    ('抖音火山', '多多在美国💜', '60368420274', 'active', '2026-04-20', '2027-10-15'),
    ('抖音火山', '河南妞一家在美国', '7451188346312983611', 'active', '2026-04-15', '2026-07-18'),
    ('抖音火山', '狗剩的快乐生活（河南妞）', '2131328945619795', 'active', '2026-04-15', '2026-06-30'),
    ('抖音火山', '河南妞在伦敦小号', '1515572379003460', 'active', '2026-04-15', '2026-06-30'),
    ('抖音火山', '河南妞在伦敦12号海口消博会', '80757483825', 'active', '2026-04-15', '2026-06-30'),
    ('抖音火山', '槿头栀子在荷兰', '71723310288', 'active', '2026-04-14', '2029-04-06'),
    ('抖音火山', '澳洲YoYo💕图图', '62683098024', 'ended', '2026-04-14', '2026-06-13'),
    ('抖音火山', '老冯在瑞士', '3659590538366589', 'ended', '2026-04-14', '2026-06-13'),
    ('抖音火山', '文和好女婿传媒', '61145259792', 'ended', '2026-04-17', '2026-06-12'),
    ('抖音火山', '小周周的澳洲生活', '96631240417', 'ended', '2026-04-23', '2026-06-12'),
    ('抖音火山', '王议在泰国', '2528529075405656', 'ended', '2026-04-18', '2026-06-12'),
    ('抖音火山', '山东龙口晓枕在比利时ᴮᴱ', '60349880302', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '混血儿郑博宇（安夏妈妈本人小号）', '68085476475', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '混血儿郑安夏（安夏妈妈本人小号）', '71245335392', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '是小老虎呀（安夏博宇妈妈本人小号）', '2804219013507051', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '安夏、博宇爸爸——高铁（中文名字）', '2528498007424884', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '安夏博宇妈妈', '96244896419', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', 'CNBE中比混血姐弟 安夏、博宇', '95630046239', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '是小熊猫呀（安夏博宇妈妈本人小号）', '1555173800687707', 'ended', '2026-04-25', '2026-05-06'),
    ('抖音火山', '老五在北美', '82059309068', 'ended', '2026-04-14', '2026-05-06'),
    ('抖音火山', '小燕子《在加拿大》', '1027360699459337', 'ended', '2026-04-14', '2026-05-06'),
    ('抖音火山', '三宝妈在澳洲', '3135449810077460', 'ended', '2026-04-20', '2026-05-06'),
    ('抖音火山', '伊笙诺言在澳洲', '100690973083', 'ended', '2026-04-20', '2026-05-06'),
    ('抖音火山', '小马哥在澳洲', '96008512143', 'ended', '2026-04-14', '2026-05-06'),
    ('抖音火山', '惠妍美学', '4366914708584135', 'ended', '2026-04-18', '2026-05-06'),
    ('抖音火山', 'fanfan在德国', '108803392918', 'ended', '2026-04-14', '2026-06-06'),
    ('抖音火山', '新西兰的文文姐', '100611312669', 'ended', '2026-03-13', '2026-03-13'),
    ('抖音火山', '小燕子《在加拿大》', '1027360699459337', 'ended', '2026-02-24', '2026-03-13'),
    ('抖音火山', '老冯在瑞士', '3659590538366589', 'ended', '2026-02-27', '2026-03-13'),
    ('抖音火山', '@老五', '82059309068', 'ended', '2026-02-28', '2026-03-13'),
    ('抖音火山', 'kiki勇闯奎', '63679616849', 'ended', '2026-03-05', '2026-03-13'),
    ('抖音火山', 'kiki老婆子用心推荐', '3659635977365640', 'ended', '2026-03-05', '2026-03-13'),
    ('抖音火山', 'kiki老婆子用心种草', '1350638243155311', 'ended', '2026-03-05', '2026-03-13'),
    ('抖音火山', '慢头哥在美国', '3597223066870504', 'ended', '2026-03-06', '2026-03-13'),
    ('抖音火山', '槿头媳妇在荷兰', '80394817841', 'ended', '2026-03-10', '2026-03-13'),
    ('抖音火山', '新西兰的文文姐生活🇳🇿', '2744833914185839', 'ended', '2026-03-13', '2026-03-13'),
    ('抖音火山', '槿头栀子在荷兰', '71723310288', 'ended', '2026-02-24', '2026-03-13'),
]

INITIAL_MULIANMAN_ROWS = [
    ('抖音火山', '混血儿郑博宇（安夏妈妈本人小号）', '68085476475', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '混血儿郑安夏（安夏妈妈本人小号）', '71245335392', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '是小老虎呀（安夏博宇妈妈本人小号）', '2804219013507051', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', 'CNBE中比混血姐弟 安夏、博宇', '95630046239', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '山东龙口晓枕在比利时ᴮᴱ', '60349880302', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '安夏博宇妈妈', '96244896419', 'ended', '2026-04-24', '2026-05-06'),
    ('抖音火山', '是小熊猫呀（安夏博宇妈妈本人小号）', '1555173800687707', 'ended', '2026-04-25', '2026-05-06'),
    ('抖音火山', '安夏、博宇爸爸——高铁（中文名字）', '2528498007424884', 'ended', '2026-04-25', '2026-05-06'),
    ('抖音火山', '槿头栀子在荷兰', '71723310288', 'ended', '2026-02-28', '2026-03-13'),
]

INITIAL_ROWS_BY_BRAND = {
    'chantelle': INITIAL_CHANTELLE_ROWS,
    'mulianman': INITIAL_MULIANMAN_ROWS,
}


def now_text():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def ensure_tables():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS creator_exemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand TEXT NOT NULL,
                creator_channel TEXT NOT NULL DEFAULT '',
                creator_nickname TEXT NOT NULL DEFAULT '',
                creator_uid TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                start_date TEXT NOT NULL DEFAULT '',
                end_date TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'manual',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_creator_exemptions_initial_unique
            ON creator_exemptions (
                brand, creator_channel, creator_uid, start_date, end_date, source
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS creator_exemption_seed_state (
                brand TEXT PRIMARY KEY,
                seeded_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    seed_initial_data()


def seed_initial_data():
    with get_db_connection() as conn:
        for brand, rows in INITIAL_ROWS_BY_BRAND.items():
            seed_brand_initial_data(conn, brand, rows)
        conn.commit()


def seed_brand_initial_data(conn, brand, rows):
    seeded = conn.execute(
        """
        SELECT 1
        FROM creator_exemption_seed_state
        WHERE brand = ?
        """,
        (brand,),
    ).fetchone()
    if seeded:
        return

    current_time = now_text()
    existing = conn.execute(
        """
        SELECT COUNT(*) AS total
        FROM creator_exemptions
        WHERE brand = ? AND source = 'screenshot'
        """,
        (brand,),
    ).fetchone()
    if existing and existing['total']:
        conn.execute(
            """
            INSERT OR IGNORE INTO creator_exemption_seed_state (brand, seeded_at)
            VALUES (?, ?)
            """,
            (brand, current_time),
        )
        return

    for channel, nickname, uid, status, start_date, end_date in rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO creator_exemptions (
                brand, creator_channel, creator_nickname, creator_uid, status,
                start_date, end_date, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'screenshot', ?, ?)
            """,
            (
                brand, channel, nickname, uid, status,
                start_date, end_date, current_time, current_time,
            ),
        )
    conn.execute(
        """
        INSERT OR IGNORE INTO creator_exemption_seed_state (brand, seeded_at)
        VALUES (?, ?)
        """,
        (brand, current_time),
    )


def normalize_brand(value):
    value = (value or '').strip()
    if value not in BRANDS:
        raise ValueError('品牌不正确')
    return value


def normalize_status(value):
    value = (value or '').strip()
    if value not in STATUSES:
        raise ValueError('豁免状态不正确')
    return value


def normalize_date(value, field_label):
    value = (value or '').strip()
    if not value:
        return ''
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError as exc:
        raise ValueError(f'{field_label}格式应为 YYYY-MM-DD') from exc
    return value


def validate_payload(data):
    brand = normalize_brand(data.get('brand'))
    status = normalize_status(data.get('status'))
    start_date = normalize_date(data.get('start_date'), '生效日期')
    end_date = normalize_date(data.get('end_date'), '结束日期')
    creator_channel = (data.get('creator_channel') or '').strip()
    creator_nickname = (data.get('creator_nickname') or '').strip()
    creator_uid = (data.get('creator_uid') or '').strip()

    if not creator_channel:
        raise ValueError('达人渠道不能为空')
    if not creator_nickname:
        raise ValueError('达人昵称不能为空')
    if not creator_uid:
        raise ValueError('达人UID不能为空')
    if not start_date:
        raise ValueError('生效日期不能为空')
    if not end_date:
        raise ValueError('结束日期不能为空')
    if start_date > end_date:
        raise ValueError('生效日期不能晚于结束日期')

    return {
        'brand': brand,
        'creator_channel': creator_channel,
        'creator_nickname': creator_nickname,
        'creator_uid': creator_uid,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
    }


def row_to_dict(row):
    item = dict(row)
    item['brand_label'] = BRANDS.get(item['brand'], item['brand'])
    item['status_label'] = STATUSES.get(item['status'], item['status'])
    return item


def list_exemptions(filters):
    ensure_tables()
    brand = normalize_brand(filters.get('brand') or 'chantelle')
    params = [brand]
    where = ['brand = ?']

    keyword = (filters.get('keyword') or '').strip()
    if keyword:
        like_value = f'%{keyword}%'
        where.append(
            '(creator_channel LIKE ? OR creator_nickname LIKE ? OR creator_uid LIKE ?)'
        )
        params.extend([like_value, like_value, like_value])

    status = (filters.get('status') or '').strip()
    if status:
        status = normalize_status(status)
        where.append('status = ?')
        params.append(status)

    for field in ('start_from', 'start_to', 'end_from', 'end_to'):
        if filters.get(field):
            normalize_date(filters.get(field), '筛选日期')

    if filters.get('start_from'):
        where.append('start_date >= ?')
        params.append(filters['start_from'])
    if filters.get('start_to'):
        where.append('start_date <= ?')
        params.append(filters['start_to'])
    if filters.get('end_from'):
        where.append('end_date >= ?')
        params.append(filters['end_from'])
    if filters.get('end_to'):
        where.append('end_date <= ?')
        params.append(filters['end_to'])

    sql = f"""
        SELECT id, brand, creator_channel, creator_nickname, creator_uid, status,
               start_date, end_date, source, created_at, updated_at
        FROM creator_exemptions
        WHERE {' AND '.join(where)}
        ORDER BY
            CASE status WHEN 'active' THEN 0 ELSE 1 END,
            end_date DESC,
            start_date DESC,
            id DESC
    """
    with get_db_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_dict(row) for row in rows]


def create_exemption(data):
    ensure_tables()
    payload = validate_payload(data)
    current_time = now_text()
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO creator_exemptions (
                brand, creator_channel, creator_nickname, creator_uid, status,
                start_date, end_date, source, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?, ?)
            """,
            (
                payload['brand'],
                payload['creator_channel'],
                payload['creator_nickname'],
                payload['creator_uid'],
                payload['status'],
                payload['start_date'],
                payload['end_date'],
                current_time,
                current_time,
            ),
        )
        conn.commit()
        return get_exemption(cursor.lastrowid, conn)


def get_exemption(record_id, conn=None):
    sql = """
        SELECT id, brand, creator_channel, creator_nickname, creator_uid, status,
               start_date, end_date, source, created_at, updated_at
        FROM creator_exemptions
        WHERE id = ?
    """
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    try:
        row = conn.execute(sql, (record_id,)).fetchone()
    finally:
        if close_conn:
            conn.close()
    if not row:
        raise ValueError('记录不存在')
    return row_to_dict(row)


def update_exemption(record_id, data):
    ensure_tables()
    payload = validate_payload(data)
    current_time = now_text()
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE creator_exemptions
            SET brand = ?, creator_channel = ?, creator_nickname = ?,
                creator_uid = ?, status = ?, start_date = ?, end_date = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload['brand'],
                payload['creator_channel'],
                payload['creator_nickname'],
                payload['creator_uid'],
                payload['status'],
                payload['start_date'],
                payload['end_date'],
                current_time,
                record_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError('记录不存在')
        conn.commit()
        return get_exemption(record_id, conn)


def stop_exemption(record_id, end_date):
    ensure_tables()
    end_date = normalize_date(end_date, '结束日期') or datetime.now().strftime('%Y-%m-%d')
    current_time = now_text()
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE creator_exemptions
            SET status = 'ended', end_date = ?, updated_at = ?
            WHERE id = ?
            """,
            (end_date, current_time, record_id),
        )
        if cursor.rowcount == 0:
            raise ValueError('记录不存在')
        conn.commit()
        return get_exemption(record_id, conn)


def delete_exemption(record_id):
    ensure_tables()
    with get_db_connection() as conn:
        try:
            cursor = conn.execute('DELETE FROM creator_exemptions WHERE id = ?', (record_id,))
            conn.commit()
        except sqlite3.Error as exc:
            raise ValueError(f'删除失败：{exc}') from exc
    if cursor.rowcount == 0:
        raise ValueError('记录不存在')
