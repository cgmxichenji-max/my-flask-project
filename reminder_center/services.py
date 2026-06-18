import calendar
import json
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from auth.services import get_db_connection


BEIJING_TZ = ZoneInfo('Asia/Shanghai')


def beijing_now():
    return datetime.now(BEIJING_TZ)


def beijing_today():
    return beijing_now().date()


def now_text():
    return beijing_now().strftime('%Y-%m-%d %H:%M:%S')


def ensure_tables():
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminder_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_key TEXT NOT NULL UNIQUE,
                reminder_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                is_enabled INTEGER NOT NULL DEFAULT 1,
                config_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.commit()
    ensure_default_settings()


def ensure_default_settings():
    current_time = now_text()
    defaults = [
        (
            'global_broadcast',
            'global',
            '广播总开关',
            '',
            1,
            {},
        ),
        (
            'exemption_expiry',
            'exemption_expiry',
            '豁免到期提醒',
            '',
            1,
            {'days_before': 7},
        ),
    ]
    with get_db_connection() as conn:
        for reminder_key, reminder_type, title, message, is_enabled, config in defaults:
            conn.execute(
                """
                INSERT OR IGNORE INTO reminder_settings (
                    reminder_key, reminder_type, title, message, is_enabled,
                    config_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reminder_key,
                    reminder_type,
                    title,
                    message,
                    is_enabled,
                    json.dumps(config, ensure_ascii=False),
                    current_time,
                    current_time,
                ),
            )
        conn.commit()


def parse_config(raw_config):
    try:
        config = json.loads(raw_config or '{}')
    except Exception:
        config = {}
    if not isinstance(config, dict):
        return {}
    return config


def row_to_dict(row):
    item = dict(row)
    item['is_enabled'] = bool(item.get('is_enabled'))
    item['config'] = parse_config(item.get('config_json'))
    return item


def get_settings():
    ensure_tables()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, reminder_key, reminder_type, title, message, is_enabled,
                   config_json, created_at, updated_at
            FROM reminder_settings
            ORDER BY
                CASE reminder_type
                    WHEN 'global' THEN 0
                    WHEN 'exemption_expiry' THEN 1
                    ELSE 2
                END,
                id
            """
        ).fetchall()

    result = {
        'global': None,
        'exemption_expiry': None,
        'monthly': [],
    }
    for row in rows:
        item = row_to_dict(row)
        if item['reminder_key'] == 'global_broadcast':
            result['global'] = item
        elif item['reminder_key'] == 'exemption_expiry':
            result['exemption_expiry'] = item
        elif item['reminder_type'] == 'monthly':
            result['monthly'].append(item)
    return result


def bool_from_payload(value):
    return 1 if value in (True, 'true', '1', 1, 'on', 'yes') else 0


def int_in_range(value, field_label, min_value, max_value):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{field_label}必须是数字') from exc
    if parsed < min_value or parsed > max_value:
        raise ValueError(f'{field_label}必须在 {min_value}-{max_value} 之间')
    return parsed


def update_global_setting(data):
    ensure_tables()
    is_enabled = bool_from_payload(data.get('is_enabled'))
    current_time = now_text()
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE reminder_settings
            SET is_enabled = ?, updated_at = ?
            WHERE reminder_key = 'global_broadcast'
            """,
            (is_enabled, current_time),
        )
        conn.commit()


def update_exemption_setting(data):
    ensure_tables()
    is_enabled = bool_from_payload(data.get('is_enabled'))
    days_before = int_in_range(data.get('days_before'), '提前天数', 0, 365)
    current_time = now_text()
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE reminder_settings
            SET is_enabled = ?, config_json = ?, updated_at = ?
            WHERE reminder_key = 'exemption_expiry'
            """,
            (
                is_enabled,
                json.dumps({'days_before': days_before}, ensure_ascii=False),
                current_time,
            ),
        )
        conn.commit()


def validate_monthly_payload(data):
    title = (data.get('title') or '').strip()
    message = (data.get('message') or '').strip()
    if not title:
        raise ValueError('提醒标题不能为空')
    day_of_month = int_in_range(data.get('day_of_month'), '每月日期', 1, 31)
    lead_days = int_in_range(data.get('lead_days') or 0, '提前天数', 0, 31)
    return {
        'title': title,
        'message': message,
        'is_enabled': bool_from_payload(data.get('is_enabled')),
        'day_of_month': day_of_month,
        'lead_days': lead_days,
    }


def create_monthly_reminder(data):
    ensure_tables()
    payload = validate_monthly_payload(data)
    current_time = now_text()
    config = {
        'day_of_month': payload['day_of_month'],
        'lead_days': payload['lead_days'],
    }
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO reminder_settings (
                reminder_key, reminder_type, title, message, is_enabled,
                config_json, created_at, updated_at
            )
            VALUES (?, 'monthly', ?, ?, ?, ?, ?, ?)
            """,
            (
                f"monthly_{uuid.uuid4().hex}",
                payload['title'],
                payload['message'],
                payload['is_enabled'],
                json.dumps(config, ensure_ascii=False),
                current_time,
                current_time,
            ),
        )
        row_id = cursor.lastrowid
        conn.execute(
            "UPDATE reminder_settings SET reminder_key = ? WHERE id = ?",
            (f'monthly_{row_id}', row_id),
        )
        conn.commit()
    return row_id


def update_monthly_reminder(record_id, data):
    ensure_tables()
    payload = validate_monthly_payload(data)
    current_time = now_text()
    config = {
        'day_of_month': payload['day_of_month'],
        'lead_days': payload['lead_days'],
    }
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE reminder_settings
            SET title = ?, message = ?, is_enabled = ?, config_json = ?, updated_at = ?
            WHERE id = ? AND reminder_type = 'monthly'
            """,
            (
                payload['title'],
                payload['message'],
                payload['is_enabled'],
                json.dumps(config, ensure_ascii=False),
                current_time,
                record_id,
            ),
        )
        if cursor.rowcount == 0:
            raise ValueError('提醒不存在')
        conn.commit()


def delete_monthly_reminder(record_id):
    ensure_tables()
    with get_db_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM reminder_settings WHERE id = ? AND reminder_type = 'monthly'",
            (record_id,),
        )
        if cursor.rowcount == 0:
            raise ValueError('提醒不存在')
        conn.commit()


def get_global_enabled():
    settings = get_settings()
    global_setting = settings.get('global')
    return bool(global_setting and global_setting.get('is_enabled'))


def get_active_reminders():
    ensure_tables()
    if not get_global_enabled():
        return []

    settings = get_settings()
    reminders = []
    today = beijing_today()
    exemption_setting = settings.get('exemption_expiry') or {}
    if exemption_setting.get('is_enabled'):
        reminders.extend(get_exemption_expiry_reminders(
            today,
            int(exemption_setting.get('config', {}).get('days_before', 7) or 7),
        ))
    reminders.extend(get_monthly_reminders(today, settings.get('monthly') or []))
    return reminders


def get_exemption_expiry_reminders(today, days_before):
    from exemption_management.services import BRANDS, ensure_tables as ensure_exemption_tables

    ensure_exemption_tables()
    end_limit = today + timedelta(days=days_before)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT brand, creator_nickname, creator_uid, end_date
            FROM creator_exemptions
            WHERE status = 'active'
              AND end_date >= ?
              AND end_date <= ?
            ORDER BY end_date ASC, brand ASC, creator_nickname ASC
            """,
            (today.isoformat(), end_limit.isoformat()),
        ).fetchall()

    reminders = []
    for row in rows:
        try:
            end_date = date.fromisoformat(row['end_date'])
        except ValueError:
            continue
        days_left = (end_date - today).days
        day_text = '今天到期' if days_left == 0 else f'{days_left} 天后到期'
        brand_label = BRANDS.get(row['brand'], row['brand'])
        reminders.append({
            'type': 'exemption_expiry',
            'title': '豁免到期',
            'message': (
                f"{brand_label}：{row['creator_nickname']}（UID {row['creator_uid']}）"
                f"将于 {row['end_date']} 到期，{day_text}"
            ),
            'date': row['end_date'],
            'days_left': days_left,
        })
    return reminders


def monthly_target_date(year, month, day_of_month):
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day_of_month, last_day))


def add_months(value, months):
    month = value.month - 1 + months
    year = value.year + month // 12
    month = month % 12 + 1
    return date(year, month, 1)


def get_monthly_reminders(today, monthly_settings):
    reminders = []
    for setting in monthly_settings:
        if not setting.get('is_enabled'):
            continue
        config = setting.get('config') or {}
        day_of_month = int(config.get('day_of_month') or 1)
        lead_days = int(config.get('lead_days') or 0)
        candidate_months = [
            date(today.year, today.month, 1),
            add_months(today, 1),
        ]
        matched_target = None
        matched_days_left = None
        for month_date in candidate_months:
            target = monthly_target_date(month_date.year, month_date.month, day_of_month)
            days_left = (target - today).days
            if 0 <= days_left <= lead_days:
                matched_target = target
                matched_days_left = days_left
                break
        if matched_target is None:
            continue
        day_text = '今天提醒' if matched_days_left == 0 else f'{matched_days_left} 天后提醒'
        message = setting.get('message') or setting.get('title') or ''
        reminders.append({
            'type': 'monthly',
            'title': setting.get('title') or '月度提醒',
            'message': f"{message}（{matched_target.isoformat()}，{day_text}）",
            'date': matched_target.isoformat(),
            'days_left': matched_days_left,
        })
    return reminders
