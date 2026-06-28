from douyin_shop_common import create_douyin_blueprint

douyin_mulianman_bp = create_douyin_blueprint(
    shop_name='douyin_mulianman',
    display_name='幕莲蔓（抖音）',
    module_key='douyin_shop_mulianman',
    table_prefix='dy_mulianman',
    enable_detail_source_commission=True,
)
