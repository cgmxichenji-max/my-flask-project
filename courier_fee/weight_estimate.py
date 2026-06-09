"""
快递费重量预估 —— 薄封装。

包装推荐 + 预估重量算法的唯一实现已收敛到 label_print/pack_recommend.py，
本文件仅：
  1. 复用 PackRecommender（以 WeightEstimator 名兼容既有调用）；
  2. 提供 courier_fee 专用的发货内容 Key 解析 parse_ship_key_to_rows。
"""

import re

from label_print.pack_recommend import PackRecommender as WeightEstimator  # noqa: F401


def parse_ship_key_to_rows(ship_key):
    """把 '113B*2;140*1' 解析为 [{'code','qty'}]。"""
    rows = []
    if not ship_key:
        return rows
    for part in str(ship_key).split(';'):
        part = part.strip()
        if not part:
            continue
        arr = part.split('*')
        code = re.sub(r'[^A-Za-z0-9]', '', arr[0]).upper()
        if not code:
            continue
        try:
            qty = int(float(arr[1])) if len(arr) > 1 else 1
        except (ValueError, IndexError):
            qty = 1
        if qty <= 0:
            qty = 1
        rows.append({'code': code, 'qty': qty})
    return rows
