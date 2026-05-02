from io import BytesIO
from pathlib import Path
from typing import Any
from datetime import datetime
import sqlite3

import pandas as pd
from openpyxl.utils import get_column_letter
from flask import current_app
import re
from werkzeug.datastructures import FileStorage
from common.excel_utils import (
    is_excel_filename,
    normalize_header_text,
    normalize_columns,
    check_columns_match,
)

from wechat_shop.table_schemas import (
    ORDER_COLUMN_MAPPING,
    ORDER_REQUIRED_COLUMNS,
    ORDER_COLUMN_TYPES,
    WECHAT_ORDER_TABLE_NAME,
    FUND_FLOW_COLUMN_MAPPING,
    FUND_FLOW_REQUIRED_COLUMNS,
    FUND_FLOW_COLUMN_TYPES,
    WECHAT_FUND_FLOW_TABLE_NAME,
    AFTER_SALES_COLUMN_MAPPING,
    AFTER_SALES_REQUIRED_COLUMNS,
    AFTER_SALES_COLUMN_TYPES,
    WECHAT_AFTER_SALES_TABLE_NAME,
)



TEXT_SOURCE_COLUMNS = {
    '订单号',
    '交易单号',
    '快递单号',
    '收件人手机',
    '商品编码（平台）',
    '商品编码(平台)',
    '商品编码(自定义)',
    'SKU编码(自定义)',
    'sku编码(自定义)',
    '礼物单号',
    'gift_order_no',
    'custom_product_code',
    'custom_sku_code',
    '流水单号',
    '关联订单号',
    '关联售后单号',
    '关联提现单号',
    '关联保单号',
    '关联礼物单号',
    '售后单号',
    '订单编号',
    '发货物流单号',
    '退换货物流单号',
    '商家退换货联系人电话',
    '商品编码（平台）',
    '商品编码(自定义)',
}


ORDER_DEDUP_KEY_COLUMNS = [
    'order_no',
    'platform_product_code',
    'product_attributes',
]

FUND_FLOW_DEDUP_KEY_COLUMNS = [
    'flow_no',
    'booking_time',
    'transaction_type',
    'related_order_no',
]

AFTER_SALES_DEDUP_KEY_COLUMNS = [
    'after_sales_no',
    'after_sales_apply_time',
]


# ===================== 数据状态表定义与操作 =====================
DATA_STATUS_TABLE_NAME = 'wechat_shop_data_status'

DATA_STATUS_CONFIG = {
    'orders': {
        'table_name': '订单表',
        'source_table': WECHAT_ORDER_TABLE_NAME,
        'date_field': 'order_created_at',
    },
    'fund_flows': {
        'table_name': '资金流水表',
        'source_table': WECHAT_FUND_FLOW_TABLE_NAME,
        'date_field': 'booking_time',
    },
    'aftersales': {
        'table_name': '售后表',
        'source_table': WECHAT_AFTER_SALES_TABLE_NAME,
        'date_field': 'after_sales_apply_time',
    },
}

# === EXPORT_TABLE_CONFIG block inserted here ===

EXPORT_TABLE_CONFIG = {
    'orders': {
        'table_name': '订单表',
        'source_table': WECHAT_ORDER_TABLE_NAME,
        'date_field': 'order_created_at',
        'allowed_fields': list(ORDER_COLUMN_TYPES.keys()),
        'column_types': ORDER_COLUMN_TYPES,
    },
    'fund_flows': {
        'table_name': '资金流水表',
        'source_table': WECHAT_FUND_FLOW_TABLE_NAME,
        'date_field': 'booking_time',
        'allowed_fields': list(FUND_FLOW_COLUMN_TYPES.keys()),
        'column_types': FUND_FLOW_COLUMN_TYPES,
    },
    'aftersales': {
        'table_name': '售后表',
        'source_table': WECHAT_AFTER_SALES_TABLE_NAME,
        'date_field': 'after_sales_apply_time',
        'allowed_fields': list(AFTER_SALES_COLUMN_TYPES.keys()),
        'column_types': AFTER_SALES_COLUMN_TYPES,
    },
}

# === EXPORT_HEADER_MAPPING block inserted here ===
EXPORT_HEADER_MAPPING = {
    'orders': {english_name: chinese_name for chinese_name, english_name in ORDER_COLUMN_MAPPING.items()},
    'fund_flows': {english_name: chinese_name for chinese_name, english_name in FUND_FLOW_COLUMN_MAPPING.items()},
    'aftersales': {english_name: chinese_name for chinese_name, english_name in AFTER_SALES_COLUMN_MAPPING.items()},
}


def _ensure_data_status_seeded(conn: sqlite3.Connection) -> None:
    """确保数据状态表存在 3 条基础记录。"""
    cursor = conn.cursor()
    cursor.execute(
        f'''
        CREATE TABLE IF NOT EXISTS {DATA_STATUS_TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_key TEXT NOT NULL UNIQUE,
            table_name TEXT NOT NULL,
            record_count INTEGER DEFAULT 0,
            min_date TEXT,
            max_date TEXT,
            last_import_time TEXT
        );
        '''
    )

    for table_key, config in DATA_STATUS_CONFIG.items():
        cursor.execute(
            f'''
            INSERT OR IGNORE INTO {DATA_STATUS_TABLE_NAME}
            (table_key, table_name, record_count)
            VALUES (?, ?, 0)
            ''',
            (table_key, config['table_name']),
        )

    conn.commit()



def _update_data_status(table_key: str) -> None:
    """按表标识刷新当前数据状态。"""
    config = DATA_STATUS_CONFIG.get(table_key)
    if not config:
        return

    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        _ensure_data_status_seeded(conn)
        cursor = conn.cursor()
        cursor.execute(
            f'''
            UPDATE {DATA_STATUS_TABLE_NAME}
            SET
                table_name = ?,
                record_count = (SELECT COUNT(*) FROM {config['source_table']}),
                min_date = (SELECT MIN({config['date_field']}) FROM {config['source_table']}),
                max_date = (SELECT MAX({config['date_field']}) FROM {config['source_table']}),
                last_import_time = datetime('now', 'localtime')
            WHERE table_key = ?
            ''',
            (config['table_name'], table_key),
        )
        conn.commit()


def _build_file_summary_text(file_info: dict[str, Any]) -> str:
    """把单个文件摘要拼成前端当前文本框可直接显示的文字。"""
    lines = [
        f"文件：{file_info['filename']}",
        f"行数：{file_info['row_count']}",
        f"列数：{file_info['column_count']}",
        f"列名：{'，'.join(file_info['columns'])}",
    ]
    return '\n'.join(lines)




def _get_database_path() -> Path:
    """获取 SQLite 数据库路径，优先读取 Flask 配置，未配置时回退到 data/wechat_shop.db。"""
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return Path(db_path)

    return Path(current_app.root_path) / 'data' / 'wechat_shop.db'


def _get_upload_source_filename(file_obj: Any) -> str:
    """兼容浏览器上传流和服务器暂存文件对象。"""
    return str(getattr(file_obj, 'filename', '') or '').strip()


def _read_upload_source_bytes(file_obj: Any) -> bytes:
    """读取 Excel 内容；优先读取暂存文件，避免导入阶段依赖请求流。"""
    path = getattr(file_obj, 'path', None)
    if path:
        return Path(path).read_bytes()
    return file_obj.read()


def _reset_upload_source(file_obj: Any) -> None:
    """旧上传流需要复位；暂存文件无需处理。"""
    stream = getattr(file_obj, 'stream', None)
    if stream is not None:
        stream.seek(0)

# === Begin export to excel helpers ===
def _normalize_export_datetime_text(value: str | None) -> str | None:
    """把前端传入的日期/时间文本统一转换为可用于 SQLite 比较的字符串。"""
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace('T', ' ').replace('/', '-').strip()
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if fmt == '%Y-%m-%d':
                return dt.strftime('%Y-%m-%d 00:00:00')
            if fmt == '%Y-%m-%d %H:%M':
                return dt.strftime('%Y-%m-%d %H:%M:00')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

    return normalized




def _build_export_download_name(table_key: str, start_time: str | None, end_time: str | None) -> str:
    """生成导出文件名。"""
    table_name_map = {
        'orders': '订单表',
        'fund_flows': '资金流水表',
        'aftersales': '售后表',
    }
    table_name = table_name_map.get(table_key, '导出数据')

    def _safe_part(value: str | None) -> str:
        if not value:
            return '全部时间'
        return re.sub(r'[\\/:*?"<>|\s]+', '_', value)

    return f"{table_name}_{_safe_part(start_time)}_到_{_safe_part(end_time)}.xlsx"


# ===== Excel导出列宽自适应辅助函数 =====
def _get_excel_display_width(value: Any) -> int:
    """按中英文混合文本估算 Excel 显示宽度。"""
    if value is None:
        return 0

    text = str(value)
    width = 0
    for ch in text:
        width += 2 if ord(ch) > 127 else 1
    return width



def _auto_adjust_excel_columns(worksheet) -> None:
    """按表头和单元格内容自动调整列宽，并限制最大宽度避免过宽。"""
    min_width = 10
    max_width = 40

    for column_index, column_cells in enumerate(worksheet.iter_cols(), start=1):
        max_display_width = 0

        for cell in column_cells:
            cell_width = _get_excel_display_width(cell.value)
            if cell_width > max_display_width:
                max_display_width = cell_width

        adjusted_width = min(max(max_display_width + 2, min_width), max_width)
        column_letter = get_column_letter(column_index)
        worksheet.column_dimensions[column_letter].width = adjusted_width



def _normalize_filter_logic(value: Any) -> str:
    """把前端传来的逻辑连接符标准化为 SQL 可用值。"""
    text = str(value or '').strip().lower()
    return 'OR' if text == 'or' else 'AND'



def _normalize_filter_operator(value: Any) -> str:
    """把前端传来的运算符标准化。"""
    return str(value or '').strip().lower()


def _try_parse_numeric_value(value: Any) -> float | None:
    """尝试把筛选值解析为数字；失败则返回 None。"""
    text = str(value or '').strip()
    if text == '':
        return None

    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _is_numeric_column(column_name: str, column_types: dict[str, str]) -> bool:
    """判断字段是否为数值列。"""
    column_type = str(column_types.get(column_name, '')).upper()
    return column_type in {'REAL', 'INTEGER', 'NUMERIC', 'FLOAT', 'DECIMAL'}


def _is_datetime_column(column_name: str) -> bool:
    """按字段名判断是否为日期时间列。"""
    text = str(column_name or '').strip().lower()
    return text.endswith('_at') or text.endswith('_time') or text == 'booking_time'


def _normalize_filter_datetime_text(value: Any, boundary: str = 'start') -> str | None:
    """把筛选条件中的日期/时间文本标准化为可比较的字符串。"""
    text = str(value or '').strip()
    if text == '':
        return None

    normalized = text.replace('T', ' ').replace('/', '-').strip()
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(normalized, fmt)
            if fmt == '%Y-%m-%d':
                if boundary == 'end':
                    return dt.strftime('%Y-%m-%d 23:59:59')
                return dt.strftime('%Y-%m-%d 00:00:00')
            if fmt == '%Y-%m-%d %H:%M':
                return dt.strftime('%Y-%m-%d %H:%M:00')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue

    return normalized


def _build_datetime_compare_expr(column_name: str) -> str:
    """构造日期字段比较表达式，统一把库内的 / 替换为 -。"""
    return f"REPLACE(CAST({column_name} AS TEXT), '/', '-')"



def _build_filter_sql_parts(
    filter_conditions: list[dict[str, Any]],
    allowed_fields: set[str],
    column_types: dict[str, str],
) -> tuple[list[str], list[Any]]:
    """把筛选条件转换为 SQL 片段与参数。"""
    sql_parts: list[str] = []
    sql_params: list[Any] = []

    for raw_condition in filter_conditions:
        if not isinstance(raw_condition, dict):
            continue

        field_name = str(raw_condition.get('field') or '').strip()
        operator = _normalize_filter_operator(raw_condition.get('operator'))
        logic = _normalize_filter_logic(raw_condition.get('logic'))
        raw_value = raw_condition.get('value')
        value_text = '' if raw_value is None else str(raw_value).strip()

        if not field_name:
            continue
        if field_name not in allowed_fields:
            raise ValueError(f'存在非法筛选字段：{field_name}')

        if operator not in {
            'eq', 'ne', 'contains', 'not_contains',
            'gt', 'gte', 'lt', 'lte',
            'is_empty', 'is_not_empty',
        }:
            raise ValueError(f'存在非法筛选条件：{operator}')

        is_numeric_field = _is_numeric_column(field_name, column_types)
        is_datetime_field = _is_datetime_column(field_name)

        clause = ''
        params: list[Any] = []

        if operator == 'eq':
            if value_text == '':
                continue
            if is_datetime_field:
                start_value = _normalize_filter_datetime_text(value_text, 'start')
                end_value = _normalize_filter_datetime_text(value_text, 'end')
                compare_expr = _build_datetime_compare_expr(field_name)
                clause = f"({compare_expr} >= ? AND {compare_expr} <= ?)"
                params = [start_value, end_value]
            else:
                numeric_value = _try_parse_numeric_value(value_text) if is_numeric_field else None
                if is_numeric_field and numeric_value is not None:
                    clause = f"CAST({field_name} AS REAL) = ?"
                    params = [numeric_value]
                else:
                    clause = f"CAST({field_name} AS TEXT) = ?"
                    params = [value_text]
        elif operator == 'ne':
            if value_text == '':
                continue
            if is_datetime_field:
                start_value = _normalize_filter_datetime_text(value_text, 'start')
                end_value = _normalize_filter_datetime_text(value_text, 'end')
                compare_expr = _build_datetime_compare_expr(field_name)
                clause = f"({compare_expr} < ? OR {compare_expr} > ?)"
                params = [start_value, end_value]
            else:
                numeric_value = _try_parse_numeric_value(value_text) if is_numeric_field else None
                if is_numeric_field and numeric_value is not None:
                    clause = f"CAST({field_name} AS REAL) <> ?"
                    params = [numeric_value]
                else:
                    clause = f"CAST({field_name} AS TEXT) <> ?"
                    params = [value_text]
        elif operator == 'contains':
            if value_text == '':
                continue
            clause = f"CAST({field_name} AS TEXT) LIKE ?"
            params = [f"%{value_text}%"]
        elif operator == 'not_contains':
            if value_text == '':
                continue
            clause = f"CAST({field_name} AS TEXT) NOT LIKE ?"
            params = [f"%{value_text}%"]
        elif operator == 'gt':
            if value_text == '':
                continue
            if is_datetime_field:
                compare_value = _normalize_filter_datetime_text(value_text, 'end')
                compare_expr = _build_datetime_compare_expr(field_name)
                clause = f"{compare_expr} > ?"
                params = [compare_value]
            else:
                numeric_value = _try_parse_numeric_value(value_text) if is_numeric_field else None
                if is_numeric_field and numeric_value is not None:
                    clause = f"CAST({field_name} AS REAL) > ?"
                    params = [numeric_value]
                else:
                    clause = f"CAST({field_name} AS TEXT) > ?"
                    params = [value_text]
        elif operator == 'gte':
            if value_text == '':
                continue
            if is_datetime_field:
                compare_value = _normalize_filter_datetime_text(value_text, 'start')
                compare_expr = _build_datetime_compare_expr(field_name)
                clause = f"{compare_expr} >= ?"
                params = [compare_value]
            else:
                numeric_value = _try_parse_numeric_value(value_text) if is_numeric_field else None
                if is_numeric_field and numeric_value is not None:
                    clause = f"CAST({field_name} AS REAL) >= ?"
                    params = [numeric_value]
                else:
                    clause = f"CAST({field_name} AS TEXT) >= ?"
                    params = [value_text]
        elif operator == 'lt':
            if value_text == '':
                continue
            if is_datetime_field:
                compare_value = _normalize_filter_datetime_text(value_text, 'start')
                compare_expr = _build_datetime_compare_expr(field_name)
                clause = f"{compare_expr} < ?"
                params = [compare_value]
            else:
                numeric_value = _try_parse_numeric_value(value_text) if is_numeric_field else None
                if is_numeric_field and numeric_value is not None:
                    clause = f"CAST({field_name} AS REAL) < ?"
                    params = [numeric_value]
                else:
                    clause = f"CAST({field_name} AS TEXT) < ?"
                    params = [value_text]
        elif operator == 'lte':
            if value_text == '':
                continue
            if is_datetime_field:
                compare_value = _normalize_filter_datetime_text(value_text, 'end')
                compare_expr = _build_datetime_compare_expr(field_name)
                clause = f"{compare_expr} <= ?"
                params = [compare_value]
            else:
                numeric_value = _try_parse_numeric_value(value_text) if is_numeric_field else None
                if is_numeric_field and numeric_value is not None:
                    clause = f"CAST({field_name} AS REAL) <= ?"
                    params = [numeric_value]
                else:
                    clause = f"CAST({field_name} AS TEXT) <= ?"
                    params = [value_text]
        elif operator == 'is_empty':
            clause = f"({field_name} IS NULL OR TRIM(CAST({field_name} AS TEXT)) = '')"
        elif operator == 'is_not_empty':
            clause = f"({field_name} IS NOT NULL AND TRIM(CAST({field_name} AS TEXT)) <> '')"

        if not clause:
            continue

        if not sql_parts:
            sql_parts.append(clause)
        else:
            sql_parts.append(f"{logic} {clause}")
        sql_params.extend(params)

    return sql_parts, sql_params


def export_data_to_excel(
    table_key: str,
    start_time: str | None,
    end_time: str | None,
    selected_fields: list[str],
    filter_conditions: list[dict[str, Any]] | None = None,
) -> tuple[BytesIO, str]:
    """按表、时间范围、字段选择从数据库导出 Excel。"""
    config = EXPORT_TABLE_CONFIG.get(table_key)
    if not config:
        raise ValueError('不支持的导出表类型')

    if not selected_fields:
        raise ValueError('请至少选择一个导出字段')

    allowed_fields = set(config['allowed_fields'])
    column_types = config.get('column_types', {})
    invalid_fields = [field for field in selected_fields if field not in allowed_fields]
    if invalid_fields:
        raise ValueError(f"存在无效导出字段：{', '.join(invalid_fields)}")

    start_text = _normalize_export_datetime_text(start_time)
    end_text = _normalize_export_datetime_text(end_time)

    if start_text and end_text and start_text > end_text:
        raise ValueError('开始时间不能大于结束时间')
    if filter_conditions is None:
        filter_conditions = []

    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    fields_sql = ', '.join(selected_fields)
    sql = f"SELECT {fields_sql} FROM {config['source_table']}"
    where_parts: list[str] = []
    params: list[Any] = []

    date_compare_expr = _build_datetime_compare_expr(config['date_field'])

    if start_text:
        where_parts.append(f"{date_compare_expr} >= ?")
        params.append(start_text)

    if end_text:
        where_parts.append(f"{date_compare_expr} <= ?")
        params.append(end_text)

    if not isinstance(filter_conditions, list):
        raise ValueError('筛选条件格式不正确')

    filter_sql_parts, filter_sql_params = _build_filter_sql_parts(
        filter_conditions=filter_conditions,
        allowed_fields=allowed_fields,
        column_types=column_types,
    )
    if filter_sql_parts:
        where_parts.append('(' + ' '.join(filter_sql_parts) + ')')
        params.extend(filter_sql_params)

    if where_parts:
        sql += ' WHERE ' + ' AND '.join(where_parts)

    sql += f" ORDER BY {config['date_field']} ASC, id ASC"

    print('export_data_to_excel -> filter_conditions =', filter_conditions)
    print('export_data_to_excel -> sql =', sql)
    print('export_data_to_excel -> params =', params)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (config['source_table'],),
        )
        table_exists = cursor.fetchone() is not None
        if not table_exists:
            raise ValueError(f"数据表不存在：{config['source_table']}")

        df = pd.read_sql_query(sql, conn, params=params)

    header_mapping = EXPORT_HEADER_MAPPING.get(table_key, {})
    renamed_columns: list[str] = []
    used_headers: dict[str, int] = {}

    for column_name in df.columns.tolist():
        base_header = header_mapping.get(column_name, column_name)
        if base_header not in used_headers:
            used_headers[base_header] = 1
            renamed_columns.append(base_header)
        else:
            used_headers[base_header] += 1
            renamed_columns.append(f"{base_header}_{used_headers[base_header]}")

    df.columns = renamed_columns

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='导出结果')
        worksheet = writer.sheets['导出结果']
        _auto_adjust_excel_columns(worksheet)
    output.seek(0)

    download_name = _build_export_download_name(table_key, start_text, end_text)
    return output, download_name



def _build_create_table_sql(table_name: str, column_types: dict[str, str]) -> str:
    """根据字段类型定义生成 CREATE TABLE SQL。"""
    column_defs: list[str] = []

    for column_name, column_type in column_types.items():
        if column_name == 'order_no':
            column_defs.append(f'{column_name} {column_type} NOT NULL')
        else:
            column_defs.append(f'{column_name} {column_type}')

    columns_sql = ',\n    '.join(column_defs)
    return f'''CREATE TABLE IF NOT EXISTS {table_name} (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    {columns_sql}\n);'''


def _get_existing_table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    """读取 SQLite 现有表字段。"""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    rows = cursor.fetchall()
    return [row[1] for row in rows]



def _sync_order_table_columns(conn: sqlite3.Connection) -> list[str]:
    """若订单表缺少新字段，则自动补列。"""
    existing_columns = _get_existing_table_columns(conn, WECHAT_ORDER_TABLE_NAME)
    added_columns: list[str] = []
    cursor = conn.cursor()

    for column_name, column_type in ORDER_COLUMN_TYPES.items():
        if column_name not in existing_columns:
            cursor.execute(
                f"ALTER TABLE {WECHAT_ORDER_TABLE_NAME} ADD COLUMN {column_name} {column_type}"
            )
            added_columns.append(column_name)

    if added_columns:
        conn.commit()

    return added_columns




def _clean_numeric_value(value: Any) -> Any:
    """清洗金额/比例类字段，尽量转成可写入 SQLite REAL 的值。"""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return value

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(',', '')
    text = text.replace('¥', '')
    text = text.replace('￥', '')
    text = text.replace('%', '')
    text = re.sub(r'\s+', '', text)

    try:
        return float(text)
    except ValueError:
        return None


# ---------------- 新增文本字段清洗和 dtype mapping 辅助函数 ----------------

def _clean_text_value(value: Any) -> Any:
    """清洗文本类字段，尽量避免长数字被写成科学计数法。"""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        if value.is_integer():
            return format(value, '.0f')
        return format(value, 'f').rstrip('0').rstrip('.')

    return str(value).strip()


def _build_text_dtype_mapping(excel_buffer: BytesIO) -> dict[str, str]:
    """先读取表头，为关键文本字段构造 dtype 映射，避免 Excel 长数字被自动转成浮点数。"""
    header_df = pd.read_excel(excel_buffer, nrows=0)
    excel_buffer.seek(0)

    normalized_text_columns = {normalize_header_text(col) for col in TEXT_SOURCE_COLUMNS}
    dtype_mapping: dict[str, str] = {}

    for raw_column_name in header_df.columns.tolist():
        if normalize_header_text(raw_column_name) in normalized_text_columns:
            dtype_mapping[raw_column_name] = 'string'

    return dtype_mapping


def _ensure_order_table_exists() -> tuple[bool, str]:
    """确保微信订单表存在；不存在则自动创建，已存在则自动补齐缺失字段。"""
    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    table_exists = False
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (WECHAT_ORDER_TABLE_NAME,),
        )
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            create_sql = _build_create_table_sql(WECHAT_ORDER_TABLE_NAME, ORDER_COLUMN_TYPES)
            cursor.execute(create_sql)
            conn.commit()
            print(f'[wechat_shop] 数据库路径：{db_path}')
            return True, f'订单表不存在，已自动创建：{WECHAT_ORDER_TABLE_NAME}（数据库：{db_path.name}）'

        added_columns = _sync_order_table_columns(conn)
        print(f'[wechat_shop] 数据库路径：{db_path}')
        if added_columns:
            return False, f'订单表已存在：{WECHAT_ORDER_TABLE_NAME}，并已补齐字段：{", ".join(added_columns)}（数据库：{db_path.name}）'

    return False, f'订单表已存在：{WECHAT_ORDER_TABLE_NAME}（数据库：{db_path.name}）'


def _prepare_orders_dataframe_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """按数据库表结构整理订单 DataFrame，确保字段齐全、顺序一致、类型尽量可落库。"""
    db_columns = list(ORDER_COLUMN_TYPES.keys())
    prepared_df = df.copy()

    for column_name in db_columns:
        if column_name not in prepared_df.columns:
            prepared_df[column_name] = None

    prepared_df = prepared_df[db_columns]

    for column_name, column_type in ORDER_COLUMN_TYPES.items():
        # 强制指定部分字段为文本（即使 schema 写成 REAL 也纠正）
        if column_name in {
            'transaction_no',
            'tracking_no',
            'gift_order_no',
            'custom_product_code',
            'custom_sku_code',
        }:
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_text_value)
            continue

        # 修正费率字段：应为文本，不是数值
        if column_name == 'promoter_commission_rate':
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_text_value)
            continue

        if column_type == 'REAL':
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_numeric_value)
        elif column_type == 'INTEGER':
            prepared_df[column_name] = (
                prepared_df[column_name]
                .apply(_clean_numeric_value)
                .apply(lambda x: int(x) if x is not None else None)
            )
        else:
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_text_value)

    return prepared_df




def _build_order_dedup_key(row: pd.Series) -> str | None:
    """构造商品维度防重键：订单号 + 平台商品编码 + 商品属性。

    其中：
    - 订单号、平台商品编码必须存在
    - 商品属性允许为空；为空时也视为一种合法商品形态
    """
    required_columns = ['order_no', 'platform_product_code']
    required_parts: list[str] = []

    for column_name in required_columns:
        value = row.get(column_name)
        cleaned_value = _clean_text_value(value)
        if cleaned_value is None or str(cleaned_value).strip() == '':
            return None
        required_parts.append(str(cleaned_value).strip())

    product_attributes = _clean_text_value(row.get('product_attributes'))
    product_attributes_part = '' if product_attributes is None else str(product_attributes).strip()

    return '||'.join([required_parts[0], required_parts[1], product_attributes_part])


def _get_existing_order_keys(conn: sqlite3.Connection) -> set[str]:
    """读取数据库中已存在的商品维度防重键，用于防重导入。"""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT order_no, platform_product_code, product_attributes FROM {WECHAT_ORDER_TABLE_NAME}"
    )
    rows = cursor.fetchall()

    existing_keys: set[str] = set()
    for row in rows:
        row_dict = {
            'order_no': row[0],
            'platform_product_code': row[1],
            'product_attributes': row[2],
        }
        dedup_key = _build_order_dedup_key(pd.Series(row_dict))
        if dedup_key:
            existing_keys.add(dedup_key)

    return existing_keys




def _deduplicate_orders_df(merged_df: pd.DataFrame, conn: sqlite3.Connection) -> tuple[pd.DataFrame, int, int]:
    """按商品维度防重：订单号 + 平台商品编码 + 商品属性。"""
    missing_key_columns = [col for col in ORDER_DEDUP_KEY_COLUMNS if col not in merged_df.columns]
    if missing_key_columns:
        return merged_df, 0, 0

    working_df = merged_df.copy()
    working_df['_dedup_key'] = working_df.apply(_build_order_dedup_key, axis=1)

    valid_key_mask = working_df['_dedup_key'].notna() & (working_df['_dedup_key'].astype(str).str.strip() != '')
    batch_valid_df = working_df[valid_key_mask].copy()
    batch_unique_df = batch_valid_df.drop_duplicates(subset=['_dedup_key'], keep='first')
    batch_duplicate_count = int(len(batch_valid_df) - len(batch_unique_df))

    empty_key_df = working_df[~valid_key_mask].copy()
    combined_df = pd.concat([batch_unique_df, empty_key_df], ignore_index=True)

    existing_keys = _get_existing_order_keys(conn)
    if not existing_keys:
        final_df = combined_df.drop(columns=['_dedup_key'], errors='ignore')
        return final_df, batch_duplicate_count, 0

    valid_after_batch_mask = combined_df['_dedup_key'].notna() & (combined_df['_dedup_key'].astype(str).str.strip() != '')
    valid_after_batch_df = combined_df[valid_after_batch_mask].copy()
    non_key_df = combined_df[~valid_after_batch_mask].copy()

    db_filtered_df = valid_after_batch_df[~valid_after_batch_df['_dedup_key'].isin(existing_keys)].copy()
    db_duplicate_count = int(len(valid_after_batch_df) - len(db_filtered_df))

    final_df = pd.concat([db_filtered_df, non_key_df], ignore_index=True)
    final_df = final_df.drop(columns=['_dedup_key'], errors='ignore')
    return final_df, batch_duplicate_count, db_duplicate_count



def _write_orders_to_db(dataframes: list[pd.DataFrame]) -> tuple[int, str]:
    """将订单数据写入 SQLite，返回写入行数和结果消息。"""
    if not dataframes:
        return 0, '没有可写入的数据'

    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    prepared_frames = [_prepare_orders_dataframe_for_db(df) for df in dataframes]
    merged_df = pd.concat(prepared_frames, ignore_index=True)

    with sqlite3.connect(db_path) as conn:
        _sync_order_table_columns(conn)
        deduped_df, batch_duplicate_count, db_duplicate_count = _deduplicate_orders_df(merged_df, conn)

        if deduped_df.empty:
            message_parts = ['没有可写入的新数据']
            if batch_duplicate_count > 0:
                message_parts.append(f'本次文件内重复商品行已跳过：{batch_duplicate_count} 条')
            if db_duplicate_count > 0:
                message_parts.append(f'数据库中已存在商品行已跳过：{db_duplicate_count} 条')
            return 0, '；'.join(message_parts) + f'（数据库：{db_path.name}）'

        deduped_df.to_sql(WECHAT_ORDER_TABLE_NAME, conn, if_exists='append', index=False)

    message_parts = [f'成功写入 {len(deduped_df)} 行数据']
    if batch_duplicate_count > 0:
        message_parts.append(f'本次文件内重复商品行已跳过：{batch_duplicate_count} 条')
    if db_duplicate_count > 0:
        message_parts.append(f'数据库中已存在商品行已跳过：{db_duplicate_count} 条')

    return int(len(deduped_df)), '；'.join(message_parts) + f'（数据库：{db_path.name}）'


# ===================== 资金流水相关辅助函数 =====================

def _build_fund_flow_create_table_sql(table_name: str, column_types: dict[str, str]) -> str:
    """根据资金流水字段类型定义生成 CREATE TABLE SQL。"""
    column_defs: list[str] = []

    for column_name, column_type in column_types.items():
        column_defs.append(f'{column_name} {column_type}')

    columns_sql = ',\n    '.join(column_defs)
    return f'''CREATE TABLE IF NOT EXISTS {table_name} (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    {columns_sql}\n);'''



def _ensure_fund_flow_table_exists() -> tuple[bool, str]:
    """确保微信资金流水表存在；不存在则自动创建，已存在则自动补齐缺失字段。"""
    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    table_exists = False
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (WECHAT_FUND_FLOW_TABLE_NAME,),
        )
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            create_sql = _build_fund_flow_create_table_sql(WECHAT_FUND_FLOW_TABLE_NAME, FUND_FLOW_COLUMN_TYPES)
            cursor.execute(create_sql)
            conn.commit()
            return True, f'资金流水表不存在，已自动创建：{WECHAT_FUND_FLOW_TABLE_NAME}（数据库：{db_path.name}）'

        existing_columns = _get_existing_table_columns(conn, WECHAT_FUND_FLOW_TABLE_NAME)
        added_columns: list[str] = []
        for column_name, column_type in FUND_FLOW_COLUMN_TYPES.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE {WECHAT_FUND_FLOW_TABLE_NAME} ADD COLUMN {column_name} {column_type}"
                )
                added_columns.append(column_name)

        if added_columns:
            conn.commit()
            return False, f'资金流水表已存在：{WECHAT_FUND_FLOW_TABLE_NAME}，并已补齐字段：{", ".join(added_columns)}（数据库：{db_path.name}）'

    return False, f'资金流水表已存在：{WECHAT_FUND_FLOW_TABLE_NAME}（数据库：{db_path.name}）'



def _prepare_fund_flow_dataframe_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """按数据库表结构整理资金流水 DataFrame。"""
    db_columns = list(FUND_FLOW_COLUMN_TYPES.keys())
    prepared_df = df.copy()

    for column_name in db_columns:
        if column_name not in prepared_df.columns:
            prepared_df[column_name] = None

    prepared_df = prepared_df[db_columns]

    for column_name, column_type in FUND_FLOW_COLUMN_TYPES.items():
        if column_name in {
            'flow_no',
            'related_order_no',
            'related_after_sales_no',
            'related_withdrawal_no',
            'related_policy_no',
            'related_gift_no',
        }:
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_text_value)
            continue

        if column_type == 'REAL':
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_numeric_value)
        else:
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_text_value)

    return prepared_df



def _build_fund_flow_dedup_key(row: pd.Series) -> str | None:
    """构造资金流水防重键：流水单号 + 记账时间 + 动帐类型 + 关联订单号。"""
    parts: list[str] = []

    for column_name in FUND_FLOW_DEDUP_KEY_COLUMNS:
        value = row.get(column_name)
        cleaned_value = _clean_text_value(value)
        if cleaned_value is None or str(cleaned_value).strip() == '':
            return None
        parts.append(str(cleaned_value).strip())

    return '||'.join(parts)



def _get_existing_fund_flow_keys(conn: sqlite3.Connection) -> set[str]:
    """读取数据库中已存在的资金流水防重键。"""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT flow_no, booking_time, transaction_type, related_order_no FROM {WECHAT_FUND_FLOW_TABLE_NAME}"
    )
    rows = cursor.fetchall()

    existing_keys: set[str] = set()
    for row in rows:
        row_dict = {
            'flow_no': row[0],
            'booking_time': row[1],
            'transaction_type': row[2],
            'related_order_no': row[3],
        }
        dedup_key = _build_fund_flow_dedup_key(pd.Series(row_dict))
        if dedup_key:
            existing_keys.add(dedup_key)

    return existing_keys



def _deduplicate_fund_flow_df(merged_df: pd.DataFrame, conn: sqlite3.Connection) -> tuple[pd.DataFrame, int, int]:
    """按资金流水维度防重：流水单号 + 记账时间 + 动帐类型 + 关联订单号。"""
    missing_key_columns = [col for col in FUND_FLOW_DEDUP_KEY_COLUMNS if col not in merged_df.columns]
    if missing_key_columns:
        return merged_df, 0, 0

    working_df = merged_df.copy()
    working_df['_dedup_key'] = working_df.apply(_build_fund_flow_dedup_key, axis=1)

    valid_key_mask = working_df['_dedup_key'].notna() & (working_df['_dedup_key'].astype(str).str.strip() != '')
    batch_valid_df = working_df[valid_key_mask].copy()
    batch_unique_df = batch_valid_df.drop_duplicates(subset=['_dedup_key'], keep='first')
    batch_duplicate_count = int(len(batch_valid_df) - len(batch_unique_df))

    empty_key_df = working_df[~valid_key_mask].copy()
    combined_df = pd.concat([batch_unique_df, empty_key_df], ignore_index=True)

    existing_keys = _get_existing_fund_flow_keys(conn)
    if not existing_keys:
        final_df = combined_df.drop(columns=['_dedup_key'], errors='ignore')
        return final_df, batch_duplicate_count, 0

    valid_after_batch_mask = combined_df['_dedup_key'].notna() & (combined_df['_dedup_key'].astype(str).str.strip() != '')
    valid_after_batch_df = combined_df[valid_after_batch_mask].copy()
    non_key_df = combined_df[~valid_after_batch_mask].copy()

    db_filtered_df = valid_after_batch_df[~valid_after_batch_df['_dedup_key'].isin(existing_keys)].copy()
    db_duplicate_count = int(len(valid_after_batch_df) - len(db_filtered_df))

    final_df = pd.concat([db_filtered_df, non_key_df], ignore_index=True)
    final_df = final_df.drop(columns=['_dedup_key'], errors='ignore')
    return final_df, batch_duplicate_count, db_duplicate_count



def _write_fund_flow_to_db(dataframes: list[pd.DataFrame]) -> tuple[int, str]:
    """将资金流水数据写入 SQLite，返回写入行数和结果消息。"""
    if not dataframes:
        return 0, '没有可写入的资金流水数据'

    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    prepared_frames = [_prepare_fund_flow_dataframe_for_db(df) for df in dataframes]
    merged_df = pd.concat(prepared_frames, ignore_index=True)

    with sqlite3.connect(db_path) as conn:
        existing_columns = _get_existing_table_columns(conn, WECHAT_FUND_FLOW_TABLE_NAME)
        for column_name, column_type in FUND_FLOW_COLUMN_TYPES.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE {WECHAT_FUND_FLOW_TABLE_NAME} ADD COLUMN {column_name} {column_type}"
                )
        conn.commit()

        deduped_df, batch_duplicate_count, db_duplicate_count = _deduplicate_fund_flow_df(merged_df, conn)

        if deduped_df.empty:
            message_parts = ['没有可写入的新资金流水数据']
            if batch_duplicate_count > 0:
                message_parts.append(f'本次文件内重复流水已跳过：{batch_duplicate_count} 条')
            if db_duplicate_count > 0:
                message_parts.append(f'数据库中已存在流水已跳过：{db_duplicate_count} 条')
            return 0, '；'.join(message_parts) + f'（数据库：{db_path.name}）'

        deduped_df.to_sql(WECHAT_FUND_FLOW_TABLE_NAME, conn, if_exists='append', index=False)

    message_parts = [f'成功写入 {len(deduped_df)} 行资金流水数据']
    if batch_duplicate_count > 0:
        message_parts.append(f'本次文件内重复流水已跳过：{batch_duplicate_count} 条')
    if db_duplicate_count > 0:
        message_parts.append(f'数据库中已存在流水已跳过：{db_duplicate_count} 条')

    return int(len(deduped_df)), '；'.join(message_parts) + f'（数据库：{db_path.name}）'



def read_fund_flow_excel_files(files: list[FileStorage]) -> dict[str, Any]:
    """读取微信资金流水 Excel 文件，校验、映射、写库。"""
    valid_files: list[FileStorage] = []
    invalid_files: list[str] = []
    failed_files: list[dict[str, str]] = []
    file_summaries: list[dict[str, Any]] = []
    prepared_dataframes: list[pd.DataFrame] = []
    base_columns: list[str] | None = None
    base_filename: str | None = None
    has_structure_mismatch = False

    for file_obj in files:
        filename = _get_upload_source_filename(file_obj)
        if not filename:
            invalid_files.append('未命名文件')
            continue

        if not is_excel_filename(filename):
            invalid_files.append(filename)
            continue

        valid_files.append(file_obj)

    if not valid_files:
        return {
            'success': False,
            'message': '没有有效的Excel文件（.xlsx/.xls）',
            'file_count': 0,
            'files': [],
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    for file_obj in valid_files:
        filename = _get_upload_source_filename(file_obj)

        try:
            file_bytes = _read_upload_source_bytes(file_obj)
            excel_buffer = BytesIO(file_bytes)
            dtype_mapping = _build_text_dtype_mapping(excel_buffer)
            df = pd.read_excel(excel_buffer, dtype=dtype_mapping if dtype_mapping else None)
            df.columns = [normalize_header_text(col) for col in df.columns.tolist()]
            current_columns = normalize_columns(df.columns.tolist())

            normalized_required_columns = [normalize_header_text(col) for col in FUND_FLOW_REQUIRED_COLUMNS]
            normalized_column_mapping = {
                normalize_header_text(chinese_name): english_name
                for chinese_name, english_name in FUND_FLOW_COLUMN_MAPPING.items()
            }

            missing_required = [col for col in normalized_required_columns if col not in current_columns]
            if missing_required:
                failed_files.append({
                    'filename': filename,
                    'error': f"缺少必需字段：{', '.join(missing_required)}",
                })
                continue

            df = df.rename(columns=normalized_column_mapping)
            mapped_columns = normalize_columns(df.columns.tolist())

            current_summary = {
                'filename': filename,
                'row_count': int(len(df)),
                'column_count': int(len(df.columns)),
                'columns': mapped_columns,
            }

            if base_columns is None:
                base_columns = current_columns
                base_filename = filename
                file_summaries.append(current_summary)
                prepared_dataframes.append(df)
            else:
                columns_match, missing_columns, extra_columns = check_columns_match(
                    base_columns,
                    current_columns,
                )

                if not columns_match:
                    error_parts: list[str] = []
                    if missing_columns:
                        error_parts.append(f"缺少列：{', '.join(missing_columns)}")
                    if extra_columns:
                        error_parts.append(f"多出列：{', '.join(extra_columns)}")
                    if not missing_columns and not extra_columns:
                        error_parts.append('列名顺序不一致')

                    failed_files.append({
                        'filename': filename,
                        'error': f"列结构不一致（基准文件：{base_filename}；{'；'.join(error_parts)}）",
                    })
                    has_structure_mismatch = True
                    file_summaries.append(current_summary)
                    prepared_dataframes.append(df)
                    continue

                file_summaries.append(current_summary)
                prepared_dataframes.append(df)
        except Exception as exc:
            failed_files.append({
                'filename': filename,
                'error': str(exc),
            })
        finally:
            _reset_upload_source(file_obj)

    success_count = len(file_summaries)

    if has_structure_mismatch:
        message_parts: list[str] = ['本次资金流水导入已终止']

        for summary in file_summaries:
            message_parts.append('')
            message_parts.append(_build_file_summary_text(summary))

        if failed_files:
            message_parts.append('')
            message_parts.append('读取失败：')
            for failed in failed_files:
                message_parts.append(f"- {failed['filename']}（{failed['error']}）")

        if invalid_files:
            message_parts.append('')
            message_parts.append(f"无效文件：{'，'.join(invalid_files)}")

        return {
            'success': False,
            'message': '\n'.join(message_parts),
            'file_count': success_count,
            'files': file_summaries,
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    if success_count == 0:
        message_parts: list[str] = ['资金流水文件已接收，但读取失败']

        if failed_files:
            message_parts.append('')
            message_parts.append('读取失败：')
            for failed in failed_files:
                message_parts.append(f"- {failed['filename']}（{failed['error']}）")

        if invalid_files:
            message_parts.append('')
            message_parts.append(f"无效文件：{'，'.join(invalid_files)}")

        return {
            'success': False,
            'message': '\n'.join(message_parts),
            'file_count': 0,
            'files': [],
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    try:
        table_created, table_message = _ensure_fund_flow_table_exists()
        written_rows, write_message = _write_fund_flow_to_db(prepared_dataframes)
        if written_rows > 0:
            _update_data_status('fund_flows')
    except Exception as exc:
        db_path = _get_database_path()
        return {
            'success': False,
            'message': f'写入资金流水数据库失败：{str(exc)}\n数据库路径：{db_path}',
            'file_count': success_count,
            'files': file_summaries,
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    message = f'成功读取 {success_count} 个资金流水文件'
    if table_message:
        message += f'\n{table_message}'
    if write_message:
        message += f'\n{write_message}'

    return {
        'success': True,
        'message': message,
        'file_count': success_count,
        'files': file_summaries,
        'invalid_files': invalid_files,
        'failed_files': failed_files,
        'table_created': table_created,
        'table_message': table_message,
        'written_rows': written_rows,
        'write_message': write_message,
    }


def read_order_excel_files(files: list[FileStorage]) -> dict[str, Any]:
    """
    第一阶段：
    接收前端上传的多个订单 Excel 文件，
    先读取每个文件的基础信息，不做数据库写入。

    当前返回：
    - success
    - message
    - file_count
    - files
    - invalid_files
    - failed_files
    """
    valid_files: list[FileStorage] = []
    invalid_files: list[str] = []
    failed_files: list[dict[str, str]] = []
    file_summaries: list[dict[str, Any]] = []
    prepared_dataframes: list[pd.DataFrame] = []
    base_columns: list[str] | None = None
    base_filename: str | None = None
    has_structure_mismatch = False
    table_created = False
    table_message = ''

    for file_obj in files:
        filename = _get_upload_source_filename(file_obj)
        if not filename:
            invalid_files.append('未命名文件')
            continue

        if not is_excel_filename(filename):
            invalid_files.append(filename)
            continue

        valid_files.append(file_obj)

    if not valid_files:
        return {
            'success': False,
            'message': '没有有效的Excel文件（.xlsx/.xls）',
            'file_count': 0,
            'files': [],
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    for file_obj in valid_files:
        filename = _get_upload_source_filename(file_obj)

        try:
            file_bytes = _read_upload_source_bytes(file_obj)
            excel_buffer = BytesIO(file_bytes)
            dtype_mapping = _build_text_dtype_mapping(excel_buffer)
            df = pd.read_excel(excel_buffer, dtype=dtype_mapping if dtype_mapping else None)
            df.columns = [normalize_header_text(col) for col in df.columns.tolist()]
            current_columns = normalize_columns(df.columns.tolist())

            normalized_required_columns = [normalize_header_text(col) for col in ORDER_REQUIRED_COLUMNS]
            normalized_column_mapping = {
                normalize_header_text(chinese_name): english_name
                for chinese_name, english_name in ORDER_COLUMN_MAPPING.items()
            }

            # ===== 新增：必需字段校验 =====
            missing_required = [col for col in normalized_required_columns if col not in current_columns]
            if missing_required:
                failed_files.append({
                    'filename': filename,
                    'error': f"缺少必需字段：{', '.join(missing_required)}",
                })
                continue

            # ===== 新增：列名映射（中文 -> 英文） =====
            df = df.rename(columns=normalized_column_mapping)
            mapped_columns = normalize_columns(df.columns.tolist())

            current_summary = {
                'filename': filename,
                'row_count': int(len(df)),
                'column_count': int(len(df.columns)),
                'columns': mapped_columns,
            }

            if base_columns is None:
                base_columns = current_columns
                base_filename = filename
                file_summaries.append(current_summary)
                prepared_dataframes.append(df)
            else:
                columns_match, missing_columns, extra_columns = check_columns_match(
                    base_columns,
                    current_columns,
                )

                if not columns_match:
                    error_parts: list[str] = []
                    if missing_columns:
                        error_parts.append(f"缺少列：{', '.join(missing_columns)}")
                    if extra_columns:
                        error_parts.append(f"多出列：{', '.join(extra_columns)}")
                    if not missing_columns and not extra_columns:
                        error_parts.append('列名顺序不一致')

                    failed_files.append({
                        'filename': filename,
                        'error': f"列结构不一致（基准文件：{base_filename}；{'；'.join(error_parts)}）",
                    })
                    has_structure_mismatch = True
                    file_summaries.append(current_summary)
                    prepared_dataframes.append(df)
                    continue

                file_summaries.append(current_summary)
                prepared_dataframes.append(df)
        except Exception as exc:
            failed_files.append({
                'filename': filename,
                'error': str(exc),
            })
        finally:
            _reset_upload_source(file_obj)

    success_count = len(file_summaries)

    if has_structure_mismatch:
        message_parts: list[str] = ['本次导入已终止']

        for summary in file_summaries:
            message_parts.append('')
            message_parts.append(_build_file_summary_text(summary))

        if failed_files:
            message_parts.append('')
            message_parts.append('读取失败：')
            for failed in failed_files:
                message_parts.append(f"- {failed['filename']}（{failed['error']}）")

        if invalid_files:
            message_parts.append('')
            message_parts.append(f"无效文件：{'，'.join(invalid_files)}")

        return {
            'success': False,
            'message': '\n'.join(message_parts),
            'file_count': success_count,
            'files': file_summaries,
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    if success_count == 0:
        message_parts: list[str] = ['文件已接收，但读取失败']

        if failed_files:
            message_parts.append('')
            message_parts.append('读取失败：')
            for failed in failed_files:
                message_parts.append(f"- {failed['filename']}（{failed['error']}）")

        if invalid_files:
            message_parts.append('')
            message_parts.append(f"无效文件：{'，'.join(invalid_files)}")

        return {
            'success': False,
            'message': '\n'.join(message_parts),
            'file_count': 0,
            'files': [],
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    try:
        table_created, table_message = _ensure_order_table_exists()
        written_rows, write_message = _write_orders_to_db(prepared_dataframes)
        if written_rows > 0:
            _update_data_status('orders')
    except Exception as exc:
        db_path = _get_database_path()
        return {
            'success': False,
            'message': f'写入数据库失败：{str(exc)}\n数据库路径：{db_path}',
            'file_count': success_count,
            'files': file_summaries,
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    message = f'成功读取 {success_count} 个订单文件'
    if table_message:
        message += f'\n{table_message}'
    if write_message:
        message += f'\n{write_message}'

    return {
        'success': True,
        'message': message,
        'file_count': success_count,
        'files': file_summaries,
        'invalid_files': invalid_files,
        'failed_files': failed_files,
        'table_created': table_created,
        'table_message': table_message,
        'written_rows': written_rows,
        'write_message': write_message,
    }
#########################################################
# 售后导入相关辅助函数和主入口
#########################################################


def _build_after_sales_create_table_sql(table_name: str, column_types: dict[str, str]) -> str:
    """根据售后字段类型定义生成 CREATE TABLE SQL。"""
    column_defs: list[str] = []

    for column_name, column_type in column_types.items():
        column_defs.append(f'{column_name} {column_type}')

    columns_sql = ',\n    '.join(column_defs)
    return f'''CREATE TABLE IF NOT EXISTS {table_name} (\n    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    {columns_sql}\n);'''



def _ensure_after_sales_table_exists() -> tuple[bool, str]:
    """确保微信售后表存在；不存在则自动创建，已存在则自动补齐缺失字段。"""
    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    table_exists = False
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (WECHAT_AFTER_SALES_TABLE_NAME,),
        )
        table_exists = cursor.fetchone() is not None

        if not table_exists:
            create_sql = _build_after_sales_create_table_sql(WECHAT_AFTER_SALES_TABLE_NAME, AFTER_SALES_COLUMN_TYPES)
            cursor.execute(create_sql)
            conn.commit()
            return True, f'售后表不存在，已自动创建：{WECHAT_AFTER_SALES_TABLE_NAME}（数据库：{db_path.name}）'

        existing_columns = _get_existing_table_columns(conn, WECHAT_AFTER_SALES_TABLE_NAME)
        added_columns: list[str] = []
        for column_name, column_type in AFTER_SALES_COLUMN_TYPES.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE {WECHAT_AFTER_SALES_TABLE_NAME} ADD COLUMN {column_name} {column_type}"
                )
                added_columns.append(column_name)

        if added_columns:
            conn.commit()
            return False, f'售后表已存在：{WECHAT_AFTER_SALES_TABLE_NAME}，并已补齐字段：{", ".join(added_columns)}（数据库：{db_path.name}）'

    return False, f'售后表已存在：{WECHAT_AFTER_SALES_TABLE_NAME}（数据库：{db_path.name}）'



def _prepare_after_sales_dataframe_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """按数据库表结构整理售后 DataFrame。"""
    db_columns = list(AFTER_SALES_COLUMN_TYPES.keys())
    prepared_df = df.copy()

    for column_name in db_columns:
        if column_name not in prepared_df.columns:
            prepared_df[column_name] = None

    prepared_df = prepared_df[db_columns]

    for column_name, column_type in AFTER_SALES_COLUMN_TYPES.items():
        if column_name in {
            'after_sales_no',
            'platform_product_code',
            'custom_product_code',
            'custom_sku_code',
            'order_no',
            'delivery_tracking_no',
            'return_tracking_no',
            'merchant_contact_phone',
        }:
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_text_value)
            continue

        if column_type == 'REAL':
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_numeric_value)
        elif column_type == 'INTEGER':
            prepared_df[column_name] = (
                prepared_df[column_name]
                .apply(_clean_numeric_value)
                .apply(lambda x: int(x) if x is not None else None)
            )
        else:
            prepared_df[column_name] = prepared_df[column_name].apply(_clean_text_value)

    return prepared_df



def _build_after_sales_dedup_key(row: pd.Series) -> str | None:
    """构造售后防重键：售后单号 + 售后申请时间。"""
    parts: list[str] = []

    for column_name in AFTER_SALES_DEDUP_KEY_COLUMNS:
        value = row.get(column_name)
        cleaned_value = _clean_text_value(value)
        if cleaned_value is None or str(cleaned_value).strip() == '':
            return None
        parts.append(str(cleaned_value).strip())

    return '||'.join(parts)



def _get_existing_after_sales_keys(conn: sqlite3.Connection) -> set[str]:
    """读取数据库中已存在的售后防重键。"""
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT after_sales_no, after_sales_apply_time FROM {WECHAT_AFTER_SALES_TABLE_NAME}"
    )
    rows = cursor.fetchall()

    existing_keys: set[str] = set()
    for row in rows:
        row_dict = {
            'after_sales_no': row[0],
            'after_sales_apply_time': row[1],
        }
        dedup_key = _build_after_sales_dedup_key(pd.Series(row_dict))
        if dedup_key:
            existing_keys.add(dedup_key)

    return existing_keys



def _deduplicate_after_sales_df(merged_df: pd.DataFrame, conn: sqlite3.Connection) -> tuple[pd.DataFrame, int, int]:
    """按售后维度防重：售后单号 + 售后申请时间。"""
    missing_key_columns = [col for col in AFTER_SALES_DEDUP_KEY_COLUMNS if col not in merged_df.columns]
    if missing_key_columns:
        return merged_df, 0, 0

    working_df = merged_df.copy()
    working_df['_dedup_key'] = working_df.apply(_build_after_sales_dedup_key, axis=1)

    valid_key_mask = working_df['_dedup_key'].notna() & (working_df['_dedup_key'].astype(str).str.strip() != '')
    batch_valid_df = working_df[valid_key_mask].copy()
    batch_unique_df = batch_valid_df.drop_duplicates(subset=['_dedup_key'], keep='first')
    batch_duplicate_count = int(len(batch_valid_df) - len(batch_unique_df))

    empty_key_df = working_df[~valid_key_mask].copy()
    combined_df = pd.concat([batch_unique_df, empty_key_df], ignore_index=True)

    existing_keys = _get_existing_after_sales_keys(conn)
    if not existing_keys:
        final_df = combined_df.drop(columns=['_dedup_key'], errors='ignore')
        return final_df, batch_duplicate_count, 0

    valid_after_batch_mask = combined_df['_dedup_key'].notna() & (combined_df['_dedup_key'].astype(str).str.strip() != '')
    valid_after_batch_df = combined_df[valid_after_batch_mask].copy()
    non_key_df = combined_df[~valid_after_batch_mask].copy()

    db_filtered_df = valid_after_batch_df[~valid_after_batch_df['_dedup_key'].isin(existing_keys)].copy()
    db_duplicate_count = int(len(valid_after_batch_df) - len(db_filtered_df))

    final_df = pd.concat([db_filtered_df, non_key_df], ignore_index=True)
    final_df = final_df.drop(columns=['_dedup_key'], errors='ignore')
    return final_df, batch_duplicate_count, db_duplicate_count



def _write_after_sales_to_db(dataframes: list[pd.DataFrame]) -> tuple[int, str]:
    """将售后数据写入 SQLite，返回写入行数和结果消息。"""
    if not dataframes:
        return 0, '没有可写入的售后数据'

    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    prepared_frames = [_prepare_after_sales_dataframe_for_db(df) for df in dataframes]
    merged_df = pd.concat(prepared_frames, ignore_index=True)

    with sqlite3.connect(db_path) as conn:
        existing_columns = _get_existing_table_columns(conn, WECHAT_AFTER_SALES_TABLE_NAME)
        for column_name, column_type in AFTER_SALES_COLUMN_TYPES.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE {WECHAT_AFTER_SALES_TABLE_NAME} ADD COLUMN {column_name} {column_type}"
                )
        conn.commit()

        deduped_df, batch_duplicate_count, db_duplicate_count = _deduplicate_after_sales_df(merged_df, conn)

        if deduped_df.empty:
            message_parts = ['没有可写入的新售后数据']
            if batch_duplicate_count > 0:
                message_parts.append(f'本次文件内重复售后已跳过：{batch_duplicate_count} 条')
            if db_duplicate_count > 0:
                message_parts.append(f'数据库中已存在售后已跳过：{db_duplicate_count} 条')
            return 0, '；'.join(message_parts) + f'（数据库：{db_path.name}）'

        deduped_df.to_sql(WECHAT_AFTER_SALES_TABLE_NAME, conn, if_exists='append', index=False)

    message_parts = [f'成功写入 {len(deduped_df)} 行售后数据']
    if batch_duplicate_count > 0:
        message_parts.append(f'本次文件内重复售后已跳过：{batch_duplicate_count} 条')
    if db_duplicate_count > 0:
        message_parts.append(f'数据库中已存在售后已跳过：{db_duplicate_count} 条')

    return int(len(deduped_df)), '；'.join(message_parts) + f'（数据库：{db_path.name}）'



def read_after_sales_excel_files(files: list[FileStorage]) -> dict[str, Any]:
    """读取微信售后 Excel 文件，校验、映射、写库。"""
    valid_files: list[FileStorage] = []
    invalid_files: list[str] = []
    failed_files: list[dict[str, str]] = []
    file_summaries: list[dict[str, Any]] = []
    prepared_dataframes: list[pd.DataFrame] = []
    base_columns: list[str] | None = None
    base_filename: str | None = None
    has_structure_mismatch = False

    for file_obj in files:
        filename = _get_upload_source_filename(file_obj)
        if not filename:
            invalid_files.append('未命名文件')
            continue

        if not is_excel_filename(filename):
            invalid_files.append(filename)
            continue

        valid_files.append(file_obj)

    if not valid_files:
        return {
            'success': False,
            'message': '没有有效的Excel文件（.xlsx/.xls）',
            'file_count': 0,
            'files': [],
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    for file_obj in valid_files:
        filename = _get_upload_source_filename(file_obj)

        try:
            file_bytes = _read_upload_source_bytes(file_obj)
            excel_buffer = BytesIO(file_bytes)
            dtype_mapping = _build_text_dtype_mapping(excel_buffer)
            df = pd.read_excel(excel_buffer, dtype=dtype_mapping if dtype_mapping else None)
            df.columns = [normalize_header_text(col) for col in df.columns.tolist()]
            current_columns = normalize_columns(df.columns.tolist())

            normalized_required_columns = [normalize_header_text(col) for col in AFTER_SALES_REQUIRED_COLUMNS]
            normalized_column_mapping = {
                normalize_header_text(chinese_name): english_name
                for chinese_name, english_name in AFTER_SALES_COLUMN_MAPPING.items()
            }

            missing_required = [col for col in normalized_required_columns if col not in current_columns]
            if missing_required:
                failed_files.append({
                    'filename': filename,
                    'error': f"缺少必需字段：{', '.join(missing_required)}",
                })
                continue

            df = df.rename(columns=normalized_column_mapping)
            mapped_columns = normalize_columns(df.columns.tolist())

            current_summary = {
                'filename': filename,
                'row_count': int(len(df)),
                'column_count': int(len(df.columns)),
                'columns': mapped_columns,
            }

            if base_columns is None:
                base_columns = current_columns
                base_filename = filename
                file_summaries.append(current_summary)
                prepared_dataframes.append(df)
            else:
                columns_match, missing_columns, extra_columns = check_columns_match(
                    base_columns,
                    current_columns,
                )

                if not columns_match:
                    error_parts: list[str] = []
                    if missing_columns:
                        error_parts.append(f"缺少列：{', '.join(missing_columns)}")
                    if extra_columns:
                        error_parts.append(f"多出列：{', '.join(extra_columns)}")
                    if not missing_columns and not extra_columns:
                        error_parts.append('列名顺序不一致')

                    failed_files.append({
                        'filename': filename,
                        'error': f"列结构不一致（基准文件：{base_filename}；{'；'.join(error_parts)}）",
                    })
                    has_structure_mismatch = True
                    file_summaries.append(current_summary)
                    prepared_dataframes.append(df)
                    continue

                file_summaries.append(current_summary)
                prepared_dataframes.append(df)
        except Exception as exc:
            failed_files.append({
                'filename': filename,
                'error': str(exc),
            })
        finally:
            _reset_upload_source(file_obj)

    success_count = len(file_summaries)

    if has_structure_mismatch:
        message_parts: list[str] = ['本次售后导入已终止']

        for summary in file_summaries:
            message_parts.append('')
            message_parts.append(_build_file_summary_text(summary))

        if failed_files:
            message_parts.append('')
            message_parts.append('读取失败：')
            for failed in failed_files:
                message_parts.append(f"- {failed['filename']}（{failed['error']}）")

        if invalid_files:
            message_parts.append('')
            message_parts.append(f"无效文件：{'，'.join(invalid_files)}")

        return {
            'success': False,
            'message': '\n'.join(message_parts),
            'file_count': success_count,
            'files': file_summaries,
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    if success_count == 0:
        message_parts: list[str] = ['售后文件已接收，但读取失败']

        if failed_files:
            message_parts.append('')
            message_parts.append('读取失败：')
            for failed in failed_files:
                message_parts.append(f"- {failed['filename']}（{failed['error']}）")

        if invalid_files:
            message_parts.append('')
            message_parts.append(f"无效文件：{'，'.join(invalid_files)}")

        return {
            'success': False,
            'message': '\n'.join(message_parts),
            'file_count': 0,
            'files': [],
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    try:
        table_created, table_message = _ensure_after_sales_table_exists()
        written_rows, write_message = _write_after_sales_to_db(prepared_dataframes)
        if written_rows > 0:
            _update_data_status('aftersales')
    except Exception as exc:
        db_path = _get_database_path()
        return {
            'success': False,
            'message': f'写入售后数据库失败：{str(exc)}\n数据库路径：{db_path}',
            'file_count': success_count,
            'files': file_summaries,
            'invalid_files': invalid_files,
            'failed_files': failed_files,
        }

    message = f'成功读取 {success_count} 个售后文件'
    if table_message:
        message += f'\n{table_message}'
    if write_message:
        message += f'\n{write_message}'

    return {
        'success': True,
        'message': message,
        'file_count': success_count,
        'files': file_summaries,
        'invalid_files': invalid_files,
        'failed_files': failed_files,
        'table_created': table_created,
        'table_message': table_message,
        'written_rows': written_rows,
        'write_message': write_message,
    }
