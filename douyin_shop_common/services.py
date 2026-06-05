"""抖音店铺公共服务层——读取 CSV/xlsx，写入 SQLite，导出 Excel。

所有函数接受 ShopConfig 对象，内含表名前缀，
供香娜露儿和幕莲蔓两个店铺复用相同逻辑。
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.utils import get_column_letter
from flask import current_app
from werkzeug.datastructures import FileStorage

from .table_schemas import (
    ORDERS_COLUMN_MAPPING,
    ORDERS_COLUMN_TYPES,
    ORDERS_REQUIRED_COLUMNS,
    ORDERS_DEDUP_KEY_COLUMNS,
    ORDERS_TEXT_SOURCE_COLUMNS,
    FUND_FLOW_COLUMN_MAPPING,
    FUND_FLOW_COLUMN_TYPES,
    FUND_FLOW_REQUIRED_COLUMNS,
    FUND_FLOW_DEDUP_KEY_COLUMNS,
    FUND_FLOW_TEXT_SOURCE_COLUMNS,
    COMMISSION_COLUMN_MAPPING,
    COMMISSION_COLUMN_TYPES,
    COMMISSION_REQUIRED_COLUMNS,
    COMMISSION_DEDUP_KEY_COLUMNS,
    COMMISSION_TEXT_SOURCE_COLUMNS,
    MERCHANT_COLUMN_MAPPING,
    MERCHANT_COLUMN_TYPES,
    MERCHANT_REQUIRED_COLUMNS,
    MERCHANT_DEDUP_KEY_COLUMNS,
    MERCHANT_TEXT_SOURCE_COLUMNS,
    DATA_STATUS_CONFIG,
    EXPORT_TABLE_CONFIG,
)


@dataclass(frozen=True)
class ShopConfig:
    shop_name: str       # 蓝图名，如 'douyin_chantelle'
    display_name: str    # 页面显示名，如 '香娜露儿（抖音）'
    module_key: str      # 权限 key，如 'douyin_shop_chantelle'
    table_prefix: str    # 表名前缀，如 'dy_chantelle'

    @property
    def orders_table(self) -> str:
        return f'{self.table_prefix}_orders'

    @property
    def fund_flow_table(self) -> str:
        return f'{self.table_prefix}_fund_flow'

    @property
    def commission_table(self) -> str:
        return f'{self.table_prefix}_commission'

    @property
    def merchant_table(self) -> str:
        return f'{self.table_prefix}_merchant'

    @property
    def data_status_table(self) -> str:
        return f'{self.table_prefix}_data_status'


# ===================== 工具函数 =====================

def _normalize_header(value: Any) -> str:
    return unicodedata.normalize('NFKC', str(value)).strip()


def _clean_text_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return format(value, '.0f')
        return format(value, 'f').rstrip('0').rstrip('.')
    return str(value).strip()


def _clean_numeric_value(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return value
    text = re.sub(r'[,¥￥%\s]', '', str(value).strip())
    try:
        return float(text)
    except ValueError:
        return None


def _get_database_path() -> Path:
    db_path = current_app.config.get('DATABASE_PATH')
    if db_path:
        return Path(db_path)
    return Path(current_app.root_path) / 'data' / 'main.db'


def _get_upload_source_filename(file_obj: Any) -> str:
    return str(getattr(file_obj, 'filename', '') or '').strip()


def _read_upload_source_bytes(file_obj: Any) -> bytes:
    path = getattr(file_obj, 'path', None)
    if path:
        return Path(path).read_bytes()
    return file_obj.read()


def _reset_upload_source(file_obj: Any) -> None:
    stream = getattr(file_obj, 'stream', None)
    if stream is not None:
        stream.seek(0)


def _get_excel_display_width(value: Any) -> int:
    if value is None:
        return 0
    text = str(value)
    return sum(2 if ord(ch) > 127 else 1 for ch in text)


def _auto_adjust_excel_columns(worksheet) -> None:
    min_width, max_width = 10, 40
    for column_index, column_cells in enumerate(worksheet.iter_cols(), start=1):
        max_w = max((_get_excel_display_width(c.value) for c in column_cells), default=0)
        adjusted = min(max(max_w + 2, min_width), max_width)
        worksheet.column_dimensions[get_column_letter(column_index)].width = adjusted


# ===================== 建表 & 状态表 =====================

def _build_create_table_sql(table_name: str, column_types: dict[str, str]) -> str:
    col_defs = [f'{col} {typ}' for col, typ in column_types.items()]
    return (
        f'CREATE TABLE IF NOT EXISTS {table_name} (\n'
        f'    id INTEGER PRIMARY KEY AUTOINCREMENT,\n'
        f'    ' + ',\n    '.join(col_defs) + '\n);'
    )


def _get_existing_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f'PRAGMA table_info({table_name})').fetchall()
    return [row[1] for row in rows]


def _sync_table_columns(conn: sqlite3.Connection, table_name: str, column_types: dict[str, str]) -> list[str]:
    existing = set(_get_existing_columns(conn, table_name))
    added: list[str] = []
    for col, typ in column_types.items():
        if col not in existing:
            conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {col} {typ}')
            added.append(col)
    if added:
        conn.commit()
    return added


def _ensure_table(conn: sqlite3.Connection, table_name: str, column_types: dict[str, str]) -> tuple[bool, str]:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
    ).fetchone()
    if row is None:
        conn.execute(_build_create_table_sql(table_name, column_types))
        conn.commit()
        return True, f'已自动创建表：{table_name}'
    added = _sync_table_columns(conn, table_name, column_types)
    if added:
        return False, f'表 {table_name} 已存在，补充字段：{", ".join(added)}'
    return False, f'表 {table_name} 已存在'


def _ensure_data_status_table(conn: sqlite3.Connection, status_table: str) -> None:
    conn.execute(f'''
        CREATE TABLE IF NOT EXISTS {status_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_key TEXT NOT NULL UNIQUE,
            table_name TEXT NOT NULL,
            record_count INTEGER DEFAULT 0,
            min_date TEXT,
            max_date TEXT,
            last_import_time TEXT
        )
    ''')
    for key, cfg in DATA_STATUS_CONFIG.items():
        conn.execute(
            f'INSERT OR IGNORE INTO {status_table} (table_key, table_name, record_count) VALUES (?,?,0)',
            (key, cfg['table_name']),
        )
    conn.commit()


def ensure_all_tables(config: ShopConfig) -> None:
    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _ensure_table(conn, config.orders_table, ORDERS_COLUMN_TYPES)
        _ensure_table(conn, config.fund_flow_table, FUND_FLOW_COLUMN_TYPES)
        _ensure_table(conn, config.commission_table, COMMISSION_COLUMN_TYPES)
        _ensure_table(conn, config.merchant_table, MERCHANT_COLUMN_TYPES)
        _ensure_data_status_table(conn, config.data_status_table)


def _update_data_status(table_key: str, config: ShopConfig) -> str:
    cfg = DATA_STATUS_CONFIG.get(table_key)
    if not cfg:
        return ''
    table_map = {
        'orders': config.orders_table,
        'fund_flow': config.fund_flow_table,
        'commission': config.commission_table,
        'merchant': config.merchant_table,
    }
    source_table = table_map.get(table_key, '')
    if not source_table:
        return ''
    try:
        db_path = _get_database_path()
        with sqlite3.connect(db_path) as conn:
            _ensure_data_status_table(conn, config.data_status_table)
            conn.execute(f'''
                UPDATE {config.data_status_table}
                SET
                    table_name = ?,
                    record_count = (SELECT COUNT(*) FROM {source_table}),
                    min_date = (SELECT MIN({cfg["date_field"]}) FROM {source_table}),
                    max_date = (SELECT MAX({cfg["date_field"]}) FROM {source_table}),
                    last_import_time = datetime('now', 'localtime')
                WHERE table_key = ?
            ''', (cfg['table_name'], table_key))
            conn.commit()
        return ''
    except Exception as exc:
        return f'提示：数据已写入，但刷新数据状态失败，请刷新页面确认。错误：{exc}'


def get_data_status_rows(config: ShopConfig) -> list[dict]:
    """读取数据状态行；首次访问时自动建表并植入 4 条空行（与 wechat_shop 行为一致）。"""
    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            _ensure_data_status_table(conn, config.data_status_table)
            rows = conn.execute(f'''
                SELECT table_key, table_name, record_count, min_date, max_date, last_import_time
                FROM {config.data_status_table}
                ORDER BY CASE table_key
                    WHEN 'orders' THEN 1 WHEN 'fund_flow' THEN 2
                    WHEN 'commission' THEN 3 WHEN 'merchant' THEN 4 ELSE 9 END
            ''').fetchall()
            return [dict(r) for r in rows]
    except Exception:
        return []


# ===================== 防重键辅助 =====================

def _build_dedup_key(row: pd.Series, key_columns: list[str]) -> str | None:
    parts: list[str] = []
    for col in key_columns:
        val = _clean_text_value(row.get(col))
        if val is None or str(val).strip() == '':
            return None
        parts.append(str(val).strip())
    return '||'.join(parts)


def _get_existing_keys(conn: sqlite3.Connection, table_name: str, key_columns: list[str]) -> set[str]:
    cols_sql = ', '.join(key_columns)
    rows = conn.execute(f'SELECT {cols_sql} FROM {table_name}').fetchall()
    keys: set[str] = set()
    for row in rows:
        row_dict = dict(zip(key_columns, row))
        key = _build_dedup_key(pd.Series(row_dict), key_columns)
        if key:
            keys.add(key)
    return keys


def _deduplicate_df(
    df: pd.DataFrame,
    conn: sqlite3.Connection,
    table_name: str,
    key_columns: list[str],
) -> tuple[pd.DataFrame, int, int]:
    if not all(col in df.columns for col in key_columns):
        return df, 0, 0

    work = df.copy()
    work['_dedup_key'] = work.apply(lambda r: _build_dedup_key(r, key_columns), axis=1)
    valid_mask = work['_dedup_key'].notna() & (work['_dedup_key'].astype(str).str.strip() != '')

    batch_valid = work[valid_mask]
    batch_unique = batch_valid.drop_duplicates(subset=['_dedup_key'], keep='first')
    batch_dups = int(len(batch_valid) - len(batch_unique))

    empty_key = work[~valid_mask]
    combined = pd.concat([batch_unique, empty_key], ignore_index=True)

    existing_keys = _get_existing_keys(conn, table_name, key_columns)
    if not existing_keys:
        return combined.drop(columns=['_dedup_key'], errors='ignore'), batch_dups, 0

    valid_after = combined['_dedup_key'].notna() & (combined['_dedup_key'].astype(str).str.strip() != '')
    valid_df = combined[valid_after]
    no_key_df = combined[~valid_after]
    filtered = valid_df[~valid_df['_dedup_key'].isin(existing_keys)]
    db_dups = int(len(valid_df) - len(filtered))
    final = pd.concat([filtered, no_key_df], ignore_index=True)
    return final.drop(columns=['_dedup_key'], errors='ignore'), batch_dups, db_dups


# ===================== DataFrame 准备 =====================

def _prepare_df_for_db(df: pd.DataFrame, column_types: dict[str, str], text_fields: set[str]) -> pd.DataFrame:
    db_cols = list(column_types.keys())
    out = df.copy()
    for col in db_cols:
        if col not in out.columns:
            out[col] = None
    out = out[db_cols]
    for col, typ in column_types.items():
        if col in text_fields:
            out[col] = out[col].apply(_clean_text_value)
        elif typ == 'REAL':
            out[col] = out[col].apply(_clean_numeric_value)
        elif typ == 'INTEGER':
            out[col] = (
                out[col].apply(_clean_numeric_value)
                .apply(lambda x: int(x) if x is not None else None)
            )
        else:
            out[col] = out[col].apply(_clean_text_value)
    return out


# ===================== CSV 读取辅助 =====================

def _build_csv_dtype_mapping(header_row: list[str], text_source_cols: set[str]) -> dict[str, str]:
    normalized_text = {_normalize_header(c) for c in text_source_cols}
    return {
        col: 'string'
        for col in header_row
        if _normalize_header(col) in normalized_text
    }


def _read_orders_csv(file_bytes: bytes) -> pd.DataFrame:
    """读取订单 CSV，第2行起是数据，需要 strip 所有值。"""
    buf = BytesIO(file_bytes)
    # 先读取表头以构建 dtype
    header_df = pd.read_csv(buf, nrows=0, encoding='utf-8-sig')
    buf.seek(0)
    dtype_map = _build_csv_dtype_mapping(header_df.columns.tolist(), ORDERS_TEXT_SOURCE_COLUMNS)
    df = pd.read_csv(buf, dtype=dtype_map if dtype_map else None,
                     encoding='utf-8-sig', low_memory=False)
    df.columns = [_normalize_header(c) for c in df.columns]
    return df


def _read_fund_flow_csv(file_bytes: bytes) -> pd.DataFrame:
    """读取资金结算 CSV，跳过第2行（字段说明行），数据从第3行开始。"""
    buf = BytesIO(file_bytes)
    header_df = pd.read_csv(buf, nrows=0, encoding='utf-8-sig')
    buf.seek(0)
    dtype_map = _build_csv_dtype_mapping(header_df.columns.tolist(), FUND_FLOW_TEXT_SOURCE_COLUMNS)
    # skiprows=[1] 跳过索引=1（第2行）的说明行，保留表头行
    df = pd.read_csv(buf, skiprows=[1], dtype=dtype_map if dtype_map else None,
                     encoding='utf-8-sig', low_memory=False)
    df.columns = [_normalize_header(c) for c in df.columns]
    return df


def _read_commission_xlsx(file_bytes: bytes) -> pd.DataFrame:
    buf = BytesIO(file_bytes)
    header_df = pd.read_excel(buf, nrows=0)
    buf.seek(0)
    dtype_map = _build_csv_dtype_mapping(header_df.columns.tolist(), COMMISSION_TEXT_SOURCE_COLUMNS)
    df = pd.read_excel(buf, dtype=dtype_map if dtype_map else None)
    df.columns = [_normalize_header(c) for c in df.columns]
    return df


def _read_merchant_xlsx(file_bytes: bytes) -> pd.DataFrame:
    buf = BytesIO(file_bytes)
    header_df = pd.read_excel(buf, nrows=0)
    buf.seek(0)
    dtype_map = _build_csv_dtype_mapping(header_df.columns.tolist(), MERCHANT_TEXT_SOURCE_COLUMNS)
    df = pd.read_excel(buf, dtype=dtype_map if dtype_map else None)
    df.columns = [_normalize_header(c) for c in df.columns]
    return df


# ===================== 写库通用函数 =====================

def _write_df_to_table(
    dfs: list[pd.DataFrame],
    config: ShopConfig,
    table_name: str,
    column_types: dict[str, str],
    key_columns: list[str],
    text_fields: set[str],
    table_key: str,
    label: str,
) -> tuple[int, str]:
    if not dfs:
        return 0, f'没有可写入的{label}数据'
    db_path = _get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    prepared = [_prepare_df_for_db(df, column_types, text_fields) for df in dfs]
    merged = pd.concat(prepared, ignore_index=True)

    with sqlite3.connect(db_path) as conn:
        _ensure_table(conn, table_name, column_types)
        deduped, batch_dups, db_dups = _deduplicate_df(merged, conn, table_name, key_columns)
        if deduped.empty:
            parts = [f'没有可写入的新{label}数据']
            if batch_dups:
                parts.append(f'本次文件内重复已跳过：{batch_dups} 条')
            if db_dups:
                parts.append(f'数据库已存在已跳过：{db_dups} 条')
            return 0, '；'.join(parts)
        deduped.to_sql(table_name, conn, if_exists='append', index=False)

    status_warn = _update_data_status(table_key, config)
    parts = [f'成功写入 {len(deduped)} 行{label}数据']
    if batch_dups:
        parts.append(f'本次文件内重复已跳过：{batch_dups} 条')
    if db_dups:
        parts.append(f'数据库已存在已跳过：{db_dups} 条')
    if status_warn:
        parts.append(status_warn)
    return int(len(deduped)), '；'.join(parts)


# ===================== 导入入口函数 =====================

def _file_is_csv(filename: str) -> bool:
    return filename.lower().endswith('.csv')


def _file_is_excel(filename: str) -> bool:
    return filename.lower().endswith(('.xlsx', '.xls'))


def _build_precheck_failed(title: str, summaries: list, invalid: list, failed: list) -> dict:
    parts = [f'{title}预检未通过，未写入数据库']
    for s in summaries:
        parts += ['', f"文件：{s['filename']}", f"行数：{s['row_count']}",
                  f"列数：{s['column_count']}", f"列名：{'，'.join(s['columns'])}"]
    if failed:
        parts += ['', '预检失败：'] + [f"- {f['filename']}（{f['error']}）" for f in failed]
    if invalid:
        parts += ['', f"无效文件：{'，'.join(invalid)}"]
    return {
        'success': False, 'message': '\n'.join(parts),
        'file_count': len(summaries), 'files': summaries,
        'invalid_files': invalid, 'failed_files': failed,
        'precheck_failed': True, 'written_rows': 0,
    }


def import_orders_files(files: list, config: ShopConfig) -> dict[str, Any]:
    col_mapping = {_normalize_header(k): v for k, v in ORDERS_COLUMN_MAPPING.items()}
    required = [_normalize_header(c) for c in ORDERS_REQUIRED_COLUMNS]
    text_fields = {v for k, v in ORDERS_COLUMN_MAPPING.items()
                   if _normalize_header(k) in {_normalize_header(c) for c in ORDERS_TEXT_SOURCE_COLUMNS}}

    valid, invalid, failed, summaries, prepared = [], [], [], [], []
    base_cols: list[str] | None = None

    for file_obj in files:
        fn = _get_upload_source_filename(file_obj)
        if not fn:
            invalid.append('未命名文件')
            continue
        if not (_file_is_csv(fn) or _file_is_excel(fn)):
            invalid.append(fn)
            continue
        valid.append(file_obj)

    if not valid:
        return {'success': False, 'message': '没有有效的文件（支持 .csv / .xlsx）',
                'file_count': 0, 'files': [], 'invalid_files': invalid, 'failed_files': failed}

    for file_obj in valid:
        fn = _get_upload_source_filename(file_obj)
        try:
            file_bytes = _read_upload_source_bytes(file_obj)
            if _file_is_csv(fn):
                df = _read_orders_csv(file_bytes)
            else:
                buf = BytesIO(file_bytes)
                df = pd.read_excel(buf)
                df.columns = [_normalize_header(c) for c in df.columns]

            cur_cols = df.columns.tolist()
            missing_req = [c for c in required if c not in cur_cols]
            if missing_req:
                failed.append({'filename': fn, 'error': f'缺少必需字段：{", ".join(missing_req)}'})
                continue

            df = df.rename(columns=col_mapping)
            summary = {'filename': fn, 'row_count': len(df), 'column_count': len(df.columns),
                       'columns': df.columns.tolist()}

            if base_cols is None:
                base_cols = cur_cols
                summaries.append(summary)
                prepared.append(df)
            else:
                if set(cur_cols) != set(base_cols):
                    failed.append({'filename': fn, 'error': '列结构与首个文件不一致'})
                    summaries.append(summary)
                    continue
                summaries.append(summary)
                prepared.append(df)
        except Exception as exc:
            failed.append({'filename': fn, 'error': str(exc)})
        finally:
            _reset_upload_source(file_obj)

    if failed:
        return _build_precheck_failed('订单导入', summaries, invalid, failed)

    if not prepared:
        return {'success': False, 'message': '读取失败，没有可导入的数据',
                'file_count': 0, 'files': summaries, 'invalid_files': invalid, 'failed_files': failed}

    try:
        written, msg = _write_df_to_table(
            prepared, config, config.orders_table, ORDERS_COLUMN_TYPES,
            ORDERS_DEDUP_KEY_COLUMNS, text_fields, 'orders', '订单',
        )
    except Exception as exc:
        return {'success': False, 'message': f'写入订单数据库失败：{exc}',
                'file_count': len(summaries), 'files': summaries,
                'invalid_files': invalid, 'failed_files': failed}

    message = f'成功读取 {len(summaries)} 个订单文件\n{msg}'
    return {'success': True, 'message': message, 'file_count': len(summaries),
            'files': summaries, 'invalid_files': invalid, 'failed_files': failed,
            'written_rows': written}


def import_fund_flow_files(files: list, config: ShopConfig) -> dict[str, Any]:
    col_mapping = {_normalize_header(k): v for k, v in FUND_FLOW_COLUMN_MAPPING.items()}
    required = [_normalize_header(c) for c in FUND_FLOW_REQUIRED_COLUMNS]
    text_fields = {v for k, v in FUND_FLOW_COLUMN_MAPPING.items()
                   if _normalize_header(k) in {_normalize_header(c) for c in FUND_FLOW_TEXT_SOURCE_COLUMNS}}

    valid, invalid, failed, summaries, prepared = [], [], [], [], []

    for file_obj in files:
        fn = _get_upload_source_filename(file_obj)
        if not fn:
            invalid.append('未命名文件')
            continue
        if not (_file_is_csv(fn) or _file_is_excel(fn)):
            invalid.append(fn)
            continue
        valid.append(file_obj)

    if not valid:
        return {'success': False, 'message': '没有有效的文件（支持 .csv）',
                'file_count': 0, 'files': [], 'invalid_files': invalid, 'failed_files': failed}

    for file_obj in valid:
        fn = _get_upload_source_filename(file_obj)
        try:
            file_bytes = _read_upload_source_bytes(file_obj)
            if _file_is_csv(fn):
                df = _read_fund_flow_csv(file_bytes)
            else:
                buf = BytesIO(file_bytes)
                # xlsx 同样跳过第2行
                df = pd.read_excel(buf, skiprows=[1])
                df.columns = [_normalize_header(c) for c in df.columns]

            cur_cols = df.columns.tolist()
            missing_req = [c for c in required if c not in cur_cols]
            if missing_req:
                failed.append({'filename': fn, 'error': f'缺少必需字段：{", ".join(missing_req)}'})
                continue

            df = df.rename(columns=col_mapping)
            summaries.append({'filename': fn, 'row_count': len(df), 'column_count': len(df.columns),
                               'columns': df.columns.tolist()})
            prepared.append(df)
        except Exception as exc:
            failed.append({'filename': fn, 'error': str(exc)})
        finally:
            _reset_upload_source(file_obj)

    if failed:
        return _build_precheck_failed('资金结算导入', summaries, invalid, failed)

    if not prepared:
        return {'success': False, 'message': '读取失败，没有可导入的数据',
                'file_count': 0, 'files': summaries, 'invalid_files': invalid, 'failed_files': failed}

    try:
        written, msg = _write_df_to_table(
            prepared, config, config.fund_flow_table, FUND_FLOW_COLUMN_TYPES,
            FUND_FLOW_DEDUP_KEY_COLUMNS, text_fields, 'fund_flow', '资金结算',
        )
    except Exception as exc:
        return {'success': False, 'message': f'写入资金结算数据库失败：{exc}',
                'file_count': len(summaries), 'files': summaries,
                'invalid_files': invalid, 'failed_files': failed}

    message = f'成功读取 {len(summaries)} 个资金结算文件\n{msg}'
    return {'success': True, 'message': message, 'file_count': len(summaries),
            'files': summaries, 'invalid_files': invalid, 'failed_files': failed,
            'written_rows': written}


def import_commission_files(files: list, config: ShopConfig) -> dict[str, Any]:
    col_mapping = {_normalize_header(k): v for k, v in COMMISSION_COLUMN_MAPPING.items()}
    required = [_normalize_header(c) for c in COMMISSION_REQUIRED_COLUMNS]
    text_fields = {v for k, v in COMMISSION_COLUMN_MAPPING.items()
                   if _normalize_header(k) in {_normalize_header(c) for c in COMMISSION_TEXT_SOURCE_COLUMNS}}

    valid, invalid, failed, summaries, prepared = [], [], [], [], []

    for file_obj in files:
        fn = _get_upload_source_filename(file_obj)
        if not fn:
            invalid.append('未命名文件')
            continue
        if not _file_is_excel(fn):
            invalid.append(fn)
            continue
        valid.append(file_obj)

    if not valid:
        return {'success': False, 'message': '没有有效的 Excel 文件（.xlsx/.xls）',
                'file_count': 0, 'files': [], 'invalid_files': invalid, 'failed_files': failed}

    for file_obj in valid:
        fn = _get_upload_source_filename(file_obj)
        try:
            file_bytes = _read_upload_source_bytes(file_obj)
            df = _read_commission_xlsx(file_bytes)
            cur_cols = df.columns.tolist()
            missing_req = [c for c in required if c not in cur_cols]
            if missing_req:
                failed.append({'filename': fn, 'error': f'缺少必需字段：{", ".join(missing_req)}'})
                continue
            df = df.rename(columns=col_mapping)
            summaries.append({'filename': fn, 'row_count': len(df), 'column_count': len(df.columns),
                               'columns': df.columns.tolist()})
            prepared.append(df)
        except Exception as exc:
            failed.append({'filename': fn, 'error': str(exc)})
        finally:
            _reset_upload_source(file_obj)

    if failed:
        return _build_precheck_failed('佣金明细导入', summaries, invalid, failed)

    if not prepared:
        return {'success': False, 'message': '读取失败，没有可导入的数据',
                'file_count': 0, 'files': summaries, 'invalid_files': invalid, 'failed_files': failed}

    try:
        written, msg = _write_df_to_table(
            prepared, config, config.commission_table, COMMISSION_COLUMN_TYPES,
            COMMISSION_DEDUP_KEY_COLUMNS, text_fields, 'commission', '佣金明细',
        )
    except Exception as exc:
        return {'success': False, 'message': f'写入佣金明细数据库失败：{exc}',
                'file_count': len(summaries), 'files': summaries,
                'invalid_files': invalid, 'failed_files': failed}

    message = f'成功读取 {len(summaries)} 个佣金明细文件\n{msg}'
    return {'success': True, 'message': message, 'file_count': len(summaries),
            'files': summaries, 'invalid_files': invalid, 'failed_files': failed,
            'written_rows': written}


def import_merchant_files(files: list, config: ShopConfig) -> dict[str, Any]:
    col_mapping = {_normalize_header(k): v for k, v in MERCHANT_COLUMN_MAPPING.items()}
    required = [_normalize_header(c) for c in MERCHANT_REQUIRED_COLUMNS]
    text_fields = {v for k, v in MERCHANT_COLUMN_MAPPING.items()
                   if _normalize_header(k) in {_normalize_header(c) for c in MERCHANT_TEXT_SOURCE_COLUMNS}}

    valid, invalid, failed, summaries, prepared = [], [], [], [], []

    for file_obj in files:
        fn = _get_upload_source_filename(file_obj)
        if not fn:
            invalid.append('未命名文件')
            continue
        if not _file_is_excel(fn):
            invalid.append(fn)
            continue
        valid.append(file_obj)

    if not valid:
        return {'success': False, 'message': '没有有效的 Excel 文件（.xlsx/.xls）',
                'file_count': 0, 'files': [], 'invalid_files': invalid, 'failed_files': failed}

    for file_obj in valid:
        fn = _get_upload_source_filename(file_obj)
        try:
            file_bytes = _read_upload_source_bytes(file_obj)
            df = _read_merchant_xlsx(file_bytes)
            if df.empty:
                summaries.append({'filename': fn, 'row_count': 0, 'column_count': len(df.columns),
                                   'columns': df.columns.tolist()})
                continue
            cur_cols = df.columns.tolist()
            missing_req = [c for c in required if c not in cur_cols]
            if missing_req:
                failed.append({'filename': fn, 'error': f'缺少必需字段：{", ".join(missing_req)}'})
                continue
            df = df.rename(columns=col_mapping)
            summaries.append({'filename': fn, 'row_count': len(df), 'column_count': len(df.columns),
                               'columns': df.columns.tolist()})
            prepared.append(df)
        except Exception as exc:
            failed.append({'filename': fn, 'error': str(exc)})
        finally:
            _reset_upload_source(file_obj)

    if failed:
        return _build_precheck_failed('招商明细导入', summaries, invalid, failed)

    if not prepared:
        msg = f'成功读取 {len(summaries)} 个文件，本月无招商数据，不写入数据库' if summaries else '读取失败，没有可导入的数据'
        return {'success': True if summaries else False, 'message': msg,
                'file_count': len(summaries), 'files': summaries,
                'invalid_files': invalid, 'failed_files': failed, 'written_rows': 0}

    try:
        written, msg = _write_df_to_table(
            prepared, config, config.merchant_table, MERCHANT_COLUMN_TYPES,
            MERCHANT_DEDUP_KEY_COLUMNS, text_fields, 'merchant', '招商明细',
        )
    except Exception as exc:
        return {'success': False, 'message': f'写入招商明细数据库失败：{exc}',
                'file_count': len(summaries), 'files': summaries,
                'invalid_files': invalid, 'failed_files': failed}

    message = f'成功读取 {len(summaries)} 个招商明细文件\n{msg}'
    return {'success': True, 'message': message, 'file_count': len(summaries),
            'files': summaries, 'invalid_files': invalid, 'failed_files': failed,
            'written_rows': written}


# ===================== 导出 =====================

def _normalize_export_dt(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip().replace('T', ' ').replace('/', '-')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
        try:
            from datetime import datetime
            dt = datetime.strptime(text, fmt)
            if fmt == '%Y-%m-%d':
                return dt.strftime('%Y-%m-%d 00:00:00')
            if fmt == '%Y-%m-%d %H:%M':
                return dt.strftime('%Y-%m-%d %H:%M:00')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    return text


def _is_datetime_column(col: str) -> bool:
    c = col.lower()
    return c.endswith('_at') or c.endswith('_time') or c in ('settlement_time',)


def _is_numeric_column(col: str, column_types: dict[str, str]) -> bool:
    return str(column_types.get(col, '')).upper() in ('REAL', 'INTEGER', 'NUMERIC', 'FLOAT')


def _build_filter_sql(
    filter_conditions: list[dict],
    allowed_fields: set[str],
    column_types: dict[str, str],
) -> tuple[list[str], list[Any]]:
    from datetime import datetime
    parts: list[str] = []
    params: list[Any] = []

    for cond in filter_conditions:
        if not isinstance(cond, dict):
            continue
        field = str(cond.get('field') or '').strip()
        op = str(cond.get('operator') or '').strip().lower()
        logic = 'OR' if str(cond.get('logic') or '').strip().lower() == 'or' else 'AND'
        raw_val = cond.get('value')
        val_text = '' if raw_val is None else str(raw_val).strip()

        if not field or field not in allowed_fields:
            continue
        if op not in {'eq', 'ne', 'contains', 'not_contains', 'gt', 'gte', 'lt', 'lte',
                      'is_empty', 'is_not_empty'}:
            continue

        is_dt = _is_datetime_column(field)
        is_num = _is_numeric_column(field, column_types)
        dt_expr = f"REPLACE(CAST({field} AS TEXT), '/', '-')"
        clause = ''
        p: list[Any] = []

        def _dt(v: str, boundary: str) -> str:
            v = v.replace('/', '-')
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    dt2 = datetime.strptime(v, fmt)
                    if fmt == '%Y-%m-%d':
                        return dt2.strftime('%Y-%m-%d 23:59:59' if boundary == 'end' else '%Y-%m-%d 00:00:00')
                    return dt2.strftime('%Y-%m-%d %H:%M:00' if fmt == '%Y-%m-%d %H:%M' else '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    pass
            return v

        if op == 'eq' and val_text:
            if is_dt:
                clause = f'({dt_expr} >= ? AND {dt_expr} <= ?)'; p = [_dt(val_text, 'start'), _dt(val_text, 'end')]
            elif is_num:
                nv = _clean_numeric_value(val_text)
                clause = f'CAST({field} AS REAL) = ?'; p = [nv if nv is not None else val_text]
            else:
                clause = f'CAST({field} AS TEXT) = ?'; p = [val_text]
        elif op == 'ne' and val_text:
            if is_dt:
                clause = f'({dt_expr} < ? OR {dt_expr} > ?)'; p = [_dt(val_text, 'start'), _dt(val_text, 'end')]
            else:
                clause = f'CAST({field} AS TEXT) <> ?'; p = [val_text]
        elif op == 'contains' and val_text:
            clause = f'CAST({field} AS TEXT) LIKE ?'; p = [f'%{val_text}%']
        elif op == 'not_contains' and val_text:
            clause = f'CAST({field} AS TEXT) NOT LIKE ?'; p = [f'%{val_text}%']
        elif op == 'gt' and val_text:
            if is_dt:
                clause = f'{dt_expr} > ?'; p = [_dt(val_text, 'end')]
            elif is_num:
                nv = _clean_numeric_value(val_text)
                clause = f'CAST({field} AS REAL) > ?'; p = [nv if nv is not None else val_text]
            else:
                clause = f'CAST({field} AS TEXT) > ?'; p = [val_text]
        elif op == 'gte' and val_text:
            if is_dt:
                clause = f'{dt_expr} >= ?'; p = [_dt(val_text, 'start')]
            elif is_num:
                nv = _clean_numeric_value(val_text)
                clause = f'CAST({field} AS REAL) >= ?'; p = [nv if nv is not None else val_text]
            else:
                clause = f'CAST({field} AS TEXT) >= ?'; p = [val_text]
        elif op == 'lt' and val_text:
            if is_dt:
                clause = f'{dt_expr} < ?'; p = [_dt(val_text, 'start')]
            elif is_num:
                nv = _clean_numeric_value(val_text)
                clause = f'CAST({field} AS REAL) < ?'; p = [nv if nv is not None else val_text]
            else:
                clause = f'CAST({field} AS TEXT) < ?'; p = [val_text]
        elif op == 'lte' and val_text:
            if is_dt:
                clause = f'{dt_expr} <= ?'; p = [_dt(val_text, 'end')]
            elif is_num:
                nv = _clean_numeric_value(val_text)
                clause = f'CAST({field} AS REAL) <= ?'; p = [nv if nv is not None else val_text]
            else:
                clause = f'CAST({field} AS TEXT) <= ?'; p = [val_text]
        elif op == 'is_empty':
            clause = f"({field} IS NULL OR TRIM(CAST({field} AS TEXT)) = '')"
        elif op == 'is_not_empty':
            clause = f"({field} IS NOT NULL AND TRIM(CAST({field} AS TEXT)) <> '')"

        if not clause:
            continue
        parts.append(clause if not parts else f'{logic} {clause}')
        params.extend(p)

    return parts, params


def export_data_to_excel(
    table_key: str,
    start_time: str | None,
    end_time: str | None,
    selected_fields: list[str],
    filter_conditions: list[dict] | None,
    config: ShopConfig,
) -> tuple[BytesIO, str]:
    cfg = EXPORT_TABLE_CONFIG.get(table_key)
    if not cfg:
        raise ValueError('不支持的导出表类型')
    if not selected_fields:
        raise ValueError('请至少选择一个导出字段')

    allowed = set(cfg['column_types'].keys())
    bad = [f for f in selected_fields if f not in allowed]
    if bad:
        raise ValueError(f"无效导出字段：{', '.join(bad)}")

    start_text = _normalize_export_dt(start_time)
    end_text = _normalize_export_dt(end_time)
    if start_text and end_text and start_text > end_text:
        raise ValueError('开始时间不能大于结束时间')

    table_name = {
        'orders': config.orders_table,
        'fund_flow': config.fund_flow_table,
        'commission': config.commission_table,
        'merchant': config.merchant_table,
    }[table_key]

    db_path = _get_database_path()
    fields_sql = ', '.join(selected_fields)
    dt_expr = f"REPLACE(CAST({cfg['date_field']} AS TEXT), '/', '-')"
    where: list[str] = []
    params: list[Any] = []
    if start_text:
        where.append(f'{dt_expr} >= ?'); params.append(start_text)
    if end_text:
        where.append(f'{dt_expr} <= ?'); params.append(end_text)

    if filter_conditions:
        fparts, fparams = _build_filter_sql(filter_conditions, allowed, cfg['column_types'])
        if fparts:
            where.append('(' + ' '.join(fparts) + ')')
            params.extend(fparams)

    sql = f"SELECT {fields_sql} FROM {table_name}"
    if where:
        sql += ' WHERE ' + ' AND '.join(where)
    sql += f" ORDER BY {cfg['date_field']} ASC, id ASC"

    with sqlite3.connect(db_path) as conn:
        exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,)
        ).fetchone()
        if not exists:
            raise ValueError(f'数据表不存在：{table_name}')
        df = pd.read_sql_query(sql, conn, params=params)

    # 中文列名映射
    rev_map = {v: k for k, v in cfg['column_mapping'].items()}
    df.columns = [rev_map.get(c, c) for c in df.columns]

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='导出结果')
        _auto_adjust_excel_columns(writer.sheets['导出结果'])
    output.seek(0)

    safe = re.sub(r'[\\/:*?"<>|\s]+', '_', f'{cfg["label"]}')
    s = re.sub(r'[\\/:*?"<>|\s]+', '_', start_text or '全部时间')
    e = re.sub(r'[\\/:*?"<>|\s]+', '_', end_text or '全部时间')
    return output, f'{safe}_{s}_到_{e}.xlsx'
