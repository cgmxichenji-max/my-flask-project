"""
包装推荐 + 预估重量 —— 全系统唯一算法源（单一真相）。

页头打印（label_print）前端、快递费核对（courier_fee）批量计算，均调用本模块，
不再各自维护一份实现。

流程：
  1. 货物行 [{code, qty}]
  2. 箱型推荐：预设优先 -> 单品精确计算 / 多品体积估算 -> 整数箱偏好 / 单件下限约束
  3. 气泡袋推荐：信封型适配，1袋优先，再多袋
  4. 预估重量 = 货物重量 + 箱型重量 + 气泡袋重量

库存过滤：有快照记录且 qty<=0 的包材不参与推荐（与页头打印一致）。

数据来源：
  label_sizes            货物尺寸 (code, length, width, height, is_irregular)
  label_weights          货物单件重量 (code, weight)
  label_packing_sizes    箱型/气泡袋尺寸 (pack_name, size="290×170×190" 或 "180×200")
  label_packing_weights  包材重量 (pack_name, weight)
  label_pack_settings    算法参数 (key, value)
  label_pack_presets     预设组合 (combo_key, box_name, bag_name, bag_qty)
"""

import math
import re

# 与 label_print.html 中的硬编码常量保持一致
WAREHOUSE_BOX_SAMPLES = {
    "140×1+702×2": "8",
    "702×2": "7.5",
    "155×1": "11",
    "155×2": "10",
    "155×3": "8",
    "139×1": "11",
    "139×2": "11",
    "140×3": "7.5",
    "A113×6": "11",
    "A160×1": "10.5",
    "140×1+184×1": "7.5",
    "139×1+140×1": "11",
    "164×2+165×1": "6",
    "163×1": "11",
    "164×1+184×1": "6.5",
    "112×1": "6.5",
    "A113×2": "11.5",
}
INTEGER_BOX_PREFERENCE = ["11", "10"]
INTEGER_BOX_VOLUME_LIMIT = 1.4


def _parse_dims(s):
    out = []
    for part in str(s or '').split('×'):
        try:
            n = float(part)
        except (ValueError, TypeError):
            continue
        if n > 0:
            out.append(n)
    return out


class PackRecommender:
    """加载一次数据，可复用对多条发货内容做箱型/气泡袋推荐与重量预估。"""

    def __init__(self, conn):
        self.goods_sizes = {}    # code -> {'d':[l,w,h], 'ir':bool}
        self.goods_weights = {}  # code -> weight(kg)
        self.pack_weights = {}   # pack_name -> weight(kg)
        self.boxes = []          # [{'n':name,'dims':[l,w,h]}], 按体积升序
        self.bags = []           # [{'n':name,'dims':[BW,BL]}], 按面积升序
        self.settings = {}
        self.presets = {}        # combo_key -> {'box','bag','bagQty'}

        # 包材库存快照：{spec: qty}（与 label_print 一致；qty<=0 的包材不参与推荐）
        pack_stock = {}
        try:
            for r in conn.execute('''
                SELECT spec, qty FROM pack_stock_snapshot
                WHERE (spec, stocktake_ts) IN (
                    SELECT spec, MAX(stocktake_ts) FROM pack_stock_snapshot GROUP BY spec
                )
            ''').fetchall():
                pack_stock[str(r['spec'])] = (r['qty'] if r['qty'] is not None else 0)
        except Exception:
            pack_stock = {}

        # 货物尺寸
        for r in conn.execute(
            'SELECT code,length,width,height,is_irregular FROM label_sizes'
        ).fetchall():
            code = str(r['code'] or '').strip()
            if not code:
                continue
            self.goods_sizes[code] = {
                'd': [float(r['length'] or 0), float(r['width'] or 0), float(r['height'] or 0)],
                'ir': bool(r['is_irregular']),
            }
        # 货物重量
        for r in conn.execute('SELECT code,weight FROM label_weights').fetchall():
            code = str(r['code'] or '').strip()
            if code:
                self.goods_weights[code] = float(r['weight'] or 0)
        # 包材重量
        for r in conn.execute(
            'SELECT pack_name,weight FROM label_packing_weights'
        ).fetchall():
            name = str(r['pack_name'] or '').strip()
            if name:
                self.pack_weights[name] = float(r['weight'] or 0)
        # 箱型 / 气泡袋尺寸
        for r in conn.execute(
            'SELECT pack_name,size FROM label_packing_sizes'
        ).fetchall():
            name = str(r['pack_name'] or '').strip()
            dims = _parse_dims(r['size'])
            if not name:
                continue
            # 库存过滤（与 label_print 一致）：有快照记录且 qty<=0 的包材跳过；
            # 无快照记录视为有货，不影响。
            if name in pack_stock and pack_stock[name] <= 0:
                continue
            if len(dims) == 3:
                self.boxes.append({'n': name, 'dims': dims})
            elif len(dims) == 2:
                self.bags.append({'n': name, 'dims': dims})
        self.boxes.sort(key=lambda b: b['dims'][0] * b['dims'][1] * b['dims'][2])
        self.bags.sort(key=lambda b: b['dims'][0] * b['dims'][1])
        # 参数
        for r in conn.execute('SELECT key,value FROM label_pack_settings').fetchall():
            self.settings[r['key']] = r['value']
        # 预设
        try:
            for r in conn.execute(
                'SELECT combo_key,box_name,bag_name,bag_qty FROM label_pack_presets'
            ).fetchall():
                ck = str(r['combo_key'] or '').strip()
                if ck:
                    self.presets[ck] = {
                        'box': r['box_name'] or None,
                        'bag': r['bag_name'] or None,
                        'bagQty': r['bag_qty'] or 0,
                    }
        except Exception:
            pass

    # ── 参数读取 ──────────────────────────────────────────
    def _f(self, key, default):
        try:
            return float(self.settings.get(key, default))
        except (ValueError, TypeError):
            return default

    def _i(self, key, default):
        try:
            return int(float(self.settings.get(key, default)))
        except (ValueError, TypeError):
            return default

    # ── 货物尺寸/重量查找（大小写兼容）────────────────────
    def _goods_size(self, code):
        if code in self.goods_sizes:
            return self.goods_sizes[code]
        for k in self.goods_sizes:
            if k.lower() == code.lower():
                return self.goods_sizes[k]
        return None

    def _goods_weight(self, code):
        if code in self.goods_weights:
            return self.goods_weights[code]
        for k in self.goods_weights:
            if k.lower() == code.lower():
                return self.goods_weights[k]
        return None

    def _pack_weight(self, name):
        if not name:
            return None
        if name in self.pack_weights:
            return self.pack_weights[name]
        for k in self.pack_weights:
            if k.lower() == name.lower():
                return self.pack_weights[k]
        return None

    # ── 箱型几何 ──────────────────────────────────────────
    @staticmethod
    def _rots(d):
        l, w, h = d
        return [[l, w, h], [l, h, w], [w, l, h], [w, h, l], [h, l, w], [h, w, l]]

    def _box_cap(self, box, item, buf):
        BL, BW, BH = box
        best = 0
        for l, w, h in self._rots(item):
            if l <= 0 or w <= 0 or h <= 0:
                continue
            c = math.floor(BL / l) * math.floor(BW / w) * math.floor(BH / h)
            if c > best:
                best = c
        return best

    def _fits_box(self, box, item, buf):
        BL, BW, BH = box
        for l, w, h in self._rots(item):
            if l + buf <= BL and w + buf <= BW and h + buf <= BH:
                return True
        return False

    def _box_index_by_name(self, name):
        for i, b in enumerate(self.boxes):
            if b['n'] == name:
                return i
        return -1

    def _box_by_name(self, name):
        for b in self.boxes:
            if b['n'] == name:
                return b
        return None

    @staticmethod
    def _box_volume(box):
        if not box:
            return math.inf
        return box['dims'][0] * box['dims'][1] * box['dims'][2]

    def _effective_box_item(self, item, irr_fac):
        """异形多件压缩体积，返回 {'dims','qty','volume'}。"""
        dims = item['dims']
        if not item['ir'] or item['qty'] <= 1:
            return {'dims': dims, 'qty': item['qty'],
                    'volume': dims[0] * dims[1] * dims[2] * item['qty']}
        sorted_d = sorted(dims, reverse=True)
        long_, mid, high = sorted_d[0], sorted_d[1], sorted_d[2]
        step = max(5, math.ceil(high * (irr_fac - 1)))
        stacked_high = high + step * (item['qty'] - 1)
        compact_dims = [long_, mid, stacked_high]
        raw_vol = dims[0] * dims[1] * dims[2] * item['qty']
        compact_vol = long_ * mid * stacked_high
        return {'dims': compact_dims, 'qty': 1,
                'volume': max(raw_vol * 0.55, compact_vol)}

    def _single_item_box_index(self, item, buf, irr_fac):
        eff = self._effective_box_item(item, irr_fac)
        for i, box in enumerate(self.boxes):
            if self._box_cap(box['dims'], eff['dims'], buf) >= eff['qty']:
                return i
        return -1

    def _single_unit_box_index(self, item, buf, irr_fac):
        single_key = f"{item['code']}×1"
        preset = self.presets.get(single_key)
        known_box = (preset and preset.get('box')) or WAREHOUSE_BOX_SAMPLES.get(single_key)
        if known_box:
            ki = self._box_index_by_name(known_box)
            if ki >= 0:
                return ki
        one = dict(item)
        one['qty'] = 1
        return self._single_item_box_index(one, buf, irr_fac)

    def _can_use_box_for_items(self, box, items, buf, fill_rate, irr_fac):
        if not box or not items:
            return False
        total_vol = 0
        for item in items:
            eff = self._effective_box_item(item, irr_fac)
            if self._box_cap(box['dims'], eff['dims'], buf) < eff['qty']:
                return False
            total_vol += eff['volume']
        return len(items) == 1 or total_vol <= self._box_volume(box) * fill_rate

    def _prefer_integer_box(self, rec_box, items, buf, fill_rate, irr_fac):
        if not rec_box or rec_box == '无匹配' or '.' not in str(rec_box):
            return rec_box
        current = self._box_by_name(rec_box)
        if not current:
            return rec_box
        max_volume = self._box_volume(current) * INTEGER_BOX_VOLUME_LIMIT
        for name in INTEGER_BOX_PREFERENCE:
            cand = self._box_by_name(name)
            if cand and self._box_volume(cand) <= max_volume and \
               self._can_use_box_for_items(cand, items, buf, fill_rate, irr_fac):
                return name
        return rec_box

    def _enforce_single_unit_floor(self, rec_box, items, buf, irr_fac):
        rec_index = self._box_index_by_name(rec_box)
        if rec_index < 0:
            return rec_box, False
        idxs = [self._single_unit_box_index(it, buf, irr_fac) if it['qty'] > 1 else -1
                for it in items]
        min_index = max(idxs) if idxs else -1
        if min_index >= 0 and rec_index < min_index:
            return self.boxes[min_index]['n'], True
        return rec_box, False

    # ── 气泡袋几何 ────────────────────────────────────────
    @staticmethod
    def _fits_bag(bag, item, buf, ratio):
        BW, BL = bag
        l, w, h = item
        return ((2 * (w + h) <= BL * ratio and l + buf <= BW) or
                (2 * (l + h) <= BL * ratio and w + buf <= BW) or
                (2 * (l + w) <= BL * ratio and h + buf <= BW))

    @staticmethod
    def _bag_role(bag):
        n = bag.get('n', '') or ''
        if '小' in n:
            return 'small'
        if '中' in n:
            return 'medium'
        if '大' in n:
            return 'large'
        return ''

    def _find_bag_by_role(self, role):
        for b in self.bags:
            if self._bag_role(b) == role:
                return b
        return None

    @staticmethod
    def _bag_pseudo_volume(bag, ratio):
        BW, BL = bag['dims']
        side = (BL * ratio) / 4
        return side * side * BW

    def _bag_cap_pieces(self, bag, dims, ratio, fill_rate):
        item_vol = dims[0] * dims[1] * dims[2]
        if item_vol <= 0:
            return 0
        return max(1, math.floor((self._bag_pseudo_volume(bag, ratio) * fill_rate) / item_vol))

    def _required_bag_count(self, bag, items, ratio, fill_rate, irr_fac):
        count = 1
        for it in items:
            dims, qty, ir = it['dims'], it['qty'], it['ir']
            cap = self._bag_cap_pieces(bag, dims, ratio, fill_rate) / (irr_fac if ir else 1)
            if cap <= 0:
                return math.inf
            count = max(count, math.ceil(qty / cap))
        total_vol = sum(it['dims'][0] * it['dims'][1] * it['dims'][2] * it['qty'] *
                        (irr_fac if it['ir'] else 1) for it in items)
        count = max(count, math.ceil(total_vol / (self._bag_pseudo_volume(bag, ratio) * fill_rate)))
        return count

    def _can_use_bag_count(self, bag, items, buf, ratio, fill_rate, irr_fac, count):
        if not bag or not items:
            return False
        for it in items:
            if not self._fits_bag(bag['dims'], it['dims'], buf, ratio):
                return False
        return self._required_bag_count(bag, items, ratio, fill_rate, irr_fac) <= count

    def _recommend_bags(self, items, buf, ratio, fill_rate, irr_fac):
        bag_items = [i for i in items if str(i['code']).upper() not in ('164', '165')]
        if not bag_items:
            return None, 0
        small = self._find_bag_by_role('small')
        medium = self._find_bag_by_role('medium')
        large = self._find_bag_by_role('large')
        for bag in [b for b in (small, medium, large) if b]:
            if self._can_use_bag_count(bag, bag_items, buf, ratio, fill_rate, irr_fac, 1):
                return bag['n'], 1
        for count in range(2, 21):
            for bag in [b for b in (medium, large) if b]:
                if self._can_use_bag_count(bag, bag_items, buf, ratio, fill_rate, irr_fac, count):
                    return bag['n'], count
        return None, 0

    # ── 组合编号 ──────────────────────────────────────────
    @staticmethod
    def _build_combo_key(rows):
        valid = [r for r in rows if r['code'] and r['qty'] > 0]
        valid.sort(key=lambda r: r['code'])
        return '+'.join(f"{r['code']}×{r['qty']}" for r in valid)

    # ── 主推荐 ────────────────────────────────────────────
    def recommend(self, rows):
        """返回 {'box','bag','bagQty','comboKey'} 或 None。供页头打印前端直接调用。"""
        if not rows:
            return None
        combo_key = self._build_combo_key(rows)

        preset = self.presets.get(combo_key)
        if preset:
            return {'box': preset.get('box') or None,
                    'bag': preset.get('bag') or None,
                    'bagQty': preset.get('bagQty') or 0,
                    'comboKey': combo_key}
        warehouse_box = WAREHOUSE_BOX_SAMPLES.get(combo_key)

        buf = self._f('buffer_mm', 0)
        fill_m = self._f('fill_rate_multi', 0.75)
        irr_fac = self._f('irregular_factor', 1.15)
        cplx_thr = self._i('complex_threshold', 10)
        bag_ratio = self._f('bag_girth_ratio', 1.05)

        items = []
        for r in rows:
            g = self._goods_size(r['code'])
            if g:
                items.append({'code': r['code'], 'qty': r['qty'], 'dims': g['d'], 'ir': g['ir']})
        if not items:
            return {'box': None, 'bag': None, 'bagQty': 0, 'comboKey': combo_key}

        if len(items) > cplx_thr:
            return {'box': None, 'bag': None, 'bagQty': 0, 'comboKey': combo_key}

        largest_item = None
        largest_vol = 0
        for it in items:
            d = it['dims']
            v = d[0] * d[1] * d[2]
            if v > largest_vol:
                largest_vol = v
                largest_item = d

        rec_box = None
        if len(items) == 1:
            eff = self._effective_box_item(items[0], irr_fac)
            for box in self.boxes:
                if self._box_cap(box['dims'], eff['dims'], buf) >= eff['qty']:
                    rec_box = box['n']
                    break
        else:
            total_vol = sum(self._effective_box_item(it, irr_fac)['volume'] for it in items)
            min_box_index = max(
                max(self._single_item_box_index(it, buf, irr_fac),
                    self._single_unit_box_index(it, buf, irr_fac) if it['qty'] > 1 else -1)
                for it in items
            )
            for box in self.boxes:
                bi = self._box_index_by_name(box['n'])
                if min_box_index >= 0 and bi < min_box_index:
                    continue
                vol = box['dims'][0] * box['dims'][1] * box['dims'][2]
                caps_ok = all(
                    self._box_cap(box['dims'], self._effective_box_item(it, irr_fac)['dims'], buf)
                    >= self._effective_box_item(it, irr_fac)['qty']
                    for it in items
                )
                if caps_ok and self._fits_box(box['dims'], largest_item, buf) and \
                   total_vol <= vol * fill_m:
                    rec_box = box['n']
                    break

        if not rec_box:
            rec_box = '无匹配'
        if warehouse_box:
            rec_box = warehouse_box
        else:
            rec_box, changed = self._enforce_single_unit_floor(rec_box, items, buf, irr_fac)
            if not changed:
                rec_box = self._prefer_integer_box(rec_box, items, buf, fill_m, irr_fac)

        bag_name, bag_qty = self._recommend_bags(items, buf, bag_ratio, fill_m, irr_fac)
        return {'box': rec_box, 'bag': bag_name, 'bagQty': bag_qty, 'comboKey': combo_key}

    # ── 预估重量 ──────────────────────────────────────────
    def estimate(self, rows):
        """
        输入 rows=[{code, qty}]，返回:
          (ok: bool, total_weight: float, detail: dict)
        ok=False 表示有货物缺重量数据（无法预估）→ 调用方应假设对方正确。
        detail 含 goods/box/bag 重量与推荐结果，便于展示与排错。
        """
        if not rows:
            return False, 0.0, {'reason': '空发货内容'}

        rec = self.recommend(rows)

        missing = []
        goods_w = 0.0
        for r in rows:
            wt = self._goods_weight(r['code'])
            if wt is None:
                missing.append(f"货物{r['code']}")
            else:
                goods_w += wt * r['qty']

        box_w = 0.0
        box_name = rec.get('box') if rec else None
        if box_name and box_name != '无匹配' and not str(box_name).startswith('不预览'):
            wt = self._pack_weight(box_name)
            if wt is None:
                missing.append(f"箱型{box_name}")
            else:
                box_w = wt

        bag_w = 0.0
        bag_name = rec.get('bag') if rec else None
        bag_qty = rec.get('bagQty') if rec else 0
        if bag_name:
            wt = self._pack_weight(bag_name)
            if wt is None:
                missing.append(f"气泡袋{bag_name}")
            else:
                bag_w = wt * (bag_qty or 1)

        detail = {
            'goods_w': round(goods_w, 4),
            'box_w': round(box_w, 4),
            'bag_w': round(bag_w, 4),
            'box': box_name,
            'bag': bag_name,
            'bag_qty': bag_qty,
            'combo_key': rec.get('comboKey') if rec else '',
            'missing': missing,
        }

        # 货物重量缺失 → 无法预估（假设对方正确）
        if missing or goods_w <= 0:
            return False, 0.0, detail

        total = round(goods_w + box_w + bag_w, 3)
        return True, total, detail
