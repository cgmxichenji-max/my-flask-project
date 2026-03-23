from typing import Any
import unicodedata

ALLOWED_EXTENSIONS = ('.xlsx', '.xls')


def is_excel_filename(filename: str) -> bool:
    """判断文件名是否为支持的 Excel 文件。"""
    return filename.lower().endswith(ALLOWED_EXTENSIONS)


def normalize_header_text(value: Any) -> str:
    """统一表头文本：转字符串、做 Unicode 兼容归一化、去掉首尾空格。"""
    return unicodedata.normalize('NFKC', str(value)).strip()


def normalize_columns(columns: list[Any]) -> list[str]:
    """将列名统一标准化，便于比较结构是否一致。"""
    return [normalize_header_text(col) for col in columns]


def check_columns_match(base_columns: list[str], current_columns: list[str]) -> tuple[bool, list[str], list[str]]:
    """
    比较两个文件的列结构是否一致

    返回：
    - 是否完全一致
    - 缺少的列
    - 多出的列
    """
    base_set = set(base_columns)
    current_set = set(current_columns)

    missing_columns = [col for col in base_columns if col not in current_set]
    extra_columns = [col for col in current_columns if col not in base_set]

    is_same_order = current_columns == base_columns
    is_same_set = not missing_columns and not extra_columns

    return is_same_order and is_same_set, missing_columns, extra_columns