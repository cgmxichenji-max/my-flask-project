from douyin_shop_common import create_douyin_blueprint

douyin_overseas_bp = create_douyin_blueprint(
    shop_name='douyin_overseas',
    display_name='海外旗舰（抖音）',
    module_key='douyin_shop_overseas',
    table_prefix='dy_overseas',
    fund_flow_format='overseas',
    order_format='overseas',
)
