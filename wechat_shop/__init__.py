

from flask import Blueprint

# 创建微信小店模块蓝图
wechat_shop_bp = Blueprint(
    'wechat_shop',
    __name__,
    template_folder='../templates'
)

# 注册路由
from . import routes