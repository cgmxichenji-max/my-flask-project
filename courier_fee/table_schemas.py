"""快递费计算模块 — 底单记录表结构定义。"""

# 底单记录：中文列名 -> 英文字段名
SHIPMENT_COLUMN_MAPPING = {
    '申请快递单号时间': 'apply_tracking_time',
    '所属平台':       'platform',
    '店铺名称':       'shop_name',
    '昵称':           'nickname',
    '订单编号':       'order_no',
    '收件人':         'recipient',
    '联系电话':       'phone',
    '省市':           'region',
    '详细地址':       'address',
    '快递名称':       'courier_name',
    '快递单号':       'tracking_no',
    '发货内容':       'ship_content',
    '数量':           'quantity',
    '重量':           'weight',
    '称重重量':       'weighed_weight',
    '实付金额':       'paid_amount',
    '发件人':         'sender',
    '发货时间':       'ship_time',
    '操作人':         'operator',
    '卖家备注':       'seller_remark',
    '买家留言':       'buyer_note',
    '系统单号':       'system_no',
    '分销商':         'distributor',
    '波次号':         'wave_no',
}

# 导入校验时必须存在的列
SHIPMENT_REQUIRED_COLUMNS = ['订单编号', '快递单号', '发货时间']

# SQLite 字段类型
SHIPMENT_COLUMN_TYPES = {
    'apply_tracking_time': 'TEXT',
    'platform':            'TEXT',
    'shop_name':           'TEXT',
    'nickname':            'TEXT',
    'order_no':            'TEXT',
    'recipient':           'TEXT',
    'phone':               'TEXT',
    'region':              'TEXT',
    'address':             'TEXT',
    'courier_name':        'TEXT',
    'tracking_no':         'TEXT',
    'ship_content':        'TEXT',
    'quantity':            'INTEGER',
    'weight':              'REAL',
    'weighed_weight':      'REAL',
    'paid_amount':         'REAL',
    'sender':              'TEXT',
    'ship_time':           'TEXT',
    'operator':            'TEXT',
    'seller_remark':       'TEXT',
    'buyer_note':          'TEXT',
    'system_no':           'TEXT',
    'distributor':         'TEXT',
    'wave_no':             'TEXT',
}

SHIPMENT_TABLE_NAME = 'courier_fee_shipments'

# ──────────────────────────────────────────────
# 计费规则表
# ──────────────────────────────────────────────

PRICING_RULES_TABLE_NAME = 'courier_fee_pricing_rules'

# 超出条件选项
BASE_WEIGHT_OP_OPTIONS = {
    'gt':  '大于(>)',
    'gte': '大于等于(>=)',
}

# 首次建表时写入的3条默认规则（匹配 VBA OPT 模块的硬编码常量）
PRICING_RULES_DEFAULTS = [
    {
        'carrier_name':        '中通',
        'base_weight':         1.2,
        'base_weight_op':      'gt',   # 超过 1.2kg 才计续重
        'base_fee':            5.0,
        'rate_jzshw':          1.0,    # 江浙沪皖续重费率 元/kg
        'rate_other':          2.0,    # 其他省份续重费率 元/kg
        'weight_tolerance_pct': 0.20,  # 重量允差百分比（默认20%）
        'effective_date':      '2024-01-01',
        'is_active':           1,
        'note':                '默认规则（参照 VBA 原始设置）',
    },
    {
        'carrier_name':        '韵达',
        'base_weight':         1.2,
        'base_weight_op':      'gt',
        'base_fee':            4.5,
        'rate_jzshw':          1.0,
        'rate_other':          2.0,
        'weight_tolerance_pct': 0.20,
        'effective_date':      '2024-01-01',
        'is_active':           1,
        'note':                '默认规则（参照 VBA 原始设置）',
    },
    {
        'carrier_name':        '申通',
        'base_weight':         1.2,
        'base_weight_op':      'gt',
        'base_fee':            4.5,
        'rate_jzshw':          1.0,
        'rate_other':          2.0,
        'weight_tolerance_pct': 0.20,
        'effective_date':      '2024-01-01',
        'is_active':           1,
        'note':                '默认规则（参照 VBA 原始设置）',
    },
]

# 查询页面展示的列（中文标题、字段名）
SHIPMENT_DISPLAY_COLUMNS = [
    ('发货时间',   'ship_time'),
    ('所属平台',   'platform'),
    ('店铺名称',   'shop_name'),
    ('昵称',       'nickname'),
    ('订单编号',   'order_no'),
    ('快递名称',   'courier_name'),
    ('快递单号',   'tracking_no'),
    ('发货内容',   'ship_content'),
    ('数量',       'quantity'),
    ('实付金额',   'paid_amount'),
    ('省市',       'region'),
    ('发件人',     'sender'),
    ('操作人',     'operator'),
]

# ──────────────────────────────────────────────
# 快递费账单（Tab 3）
# ──────────────────────────────────────────────

BILL_FILES_TABLE_NAME = 'courier_fee_bill_files'
BILLS_TABLE_NAME      = 'courier_fee_bills'

CARRIER_NAMES = ('中通', '韵达', '申通')

# 列名别名映射（按优先级，第一个匹配为准）
BILL_COLUMN_ALIASES = {
    'tracking_no':   ['快递单号', '运单号', '单号', '邮件号', '面单号'],
    'bill_date':     ['业务时间', '账单日期', '日期', '揽收时间', '计费时间', '发货时间', '寄件时间'],
    'settle_object': ['结算对象', '客户名称', '寄件客户', '商家', '付款客户'],
    'dest_province': ['目的省份', '目的地省', '目的省', '收件省', '到达省份', '省份', '收方省份'],
    'settle_weight': ['结算重量', '计费重量', '重量', '实际重量', '收费重量'],
    'actual_fee':    ['结算费用', '费用', '运费', '金额', '应收金额', '实收金额', '应收费用'],
    'sender':        ['寄件人', '发件人', '寄件客户', '发件客户', '店铺', '商家', '寄件人姓名'],
}
BILL_REQUIRED_FIELDS = ('tracking_no', 'settle_weight', 'actual_fee')

# 横表展示列 (field_name, 中文标题, 可排序)
BILLS_DISPLAY_COLUMNS = [
    ('carrier_name',     '快递公司',        True),
    ('bill_date',        '账单日期',        True),
    ('tracking_no',      '快递单号',        False),
    ('settle_object',    '结算对象',        True),
    ('dest_province',    '目的省份',        True),
    ('actual_fee',       '实际费用',        True),
    ('std_fee',          '应收费用_标准',   True),
    ('fee_diff',         '差额',            True),
    ('check_result',     '核对结果',        True),
    ('ship_content',     '发货内容',        False),
    ('ship_content_key', '发货内容排序Key', False),
    # 结算重量与预估重量并排，方便直观对比
    ('settle_weight',    '结算重量(kg)',    True),
    ('min_weight',       '预估重量(kg)',    True),
    ('max_weight',       '允差上限(kg)',    True),
    ('weight_in_range',  '重量核查',        True),
    ('est_max_fee',      '预估应收费用',    True),
    ('is_corrected',     '已修正',          True),
    ('sender',           '寄件人',          True),
]

# 导出时所有可导出字段（中文标题、字段名）
SHIPMENT_EXPORT_COLUMNS = [
    ('申请快递单号时间', 'apply_tracking_time'),
    ('所属平台',         'platform'),
    ('店铺名称',         'shop_name'),
    ('昵称',             'nickname'),
    ('订单编号',         'order_no'),
    ('收件人',           'recipient'),
    ('联系电话',         'phone'),
    ('省市',             'region'),
    ('详细地址',         'address'),
    ('快递名称',         'courier_name'),
    ('快递单号',         'tracking_no'),
    ('发货内容',         'ship_content'),
    ('数量',             'quantity'),
    ('重量',             'weight'),
    ('称重重量',         'weighed_weight'),
    ('实付金额',         'paid_amount'),
    ('发件人',           'sender'),
    ('发货时间',         'ship_time'),
    ('操作人',           'operator'),
    ('卖家备注',         'seller_remark'),
    ('买家留言',         'buyer_note'),
    ('系统单号',         'system_no'),
    ('分销商',           'distributor'),
    ('波次号',           'wave_no'),
]
