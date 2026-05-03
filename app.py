import os
import secrets

from flask import Flask, g, render_template, session

# ===== 导入模块蓝图 =====
from auth import register_auth
from auth.decorators import login_required
from auth.schema import ensure_default_admin, ensure_tables
from auth.services import get_user_by_id, has_module_permission
from inventory.routes import inventory_bp    # 库存盘点模块
from purchase.routes import purchase_bp      # 采购模块
from stocking.routes import stocking_bp      # 操作入库
from logs.routes import logs_bp             # 操作日志模块
from vps_monitor import vps_monitor_bp       # VPS 监控模块
from wechat_shop import wechat_shop_bp       # 微信小店模块
from invoicing.routes import invoicing_bp     # 发票核对模块

# ===== 创建 Flask 应用 =====
app = Flask(__name__)
# ===== 数据库统一配置 =====
app.config['DATABASE_PATH'] = 'data/main.db'
app.config['MAX_CONTENT_LENGTH'] = 512 * 1024 * 1024


def get_secret_key():
    secret_path = os.path.join('data', '.app_secret_key')
    env_secret = os.environ.get('APP_SECRET_KEY')
    if env_secret:
        return env_secret
    if os.path.exists(secret_path):
        with open(secret_path, 'r', encoding='utf-8') as secret_file:
            return secret_file.read().strip()

    secret_key = secrets.token_urlsafe(48)
    os.makedirs(os.path.dirname(secret_path), exist_ok=True)
    with open(secret_path, 'w', encoding='utf-8') as secret_file:
        secret_file.write(secret_key)
    return secret_key


app.secret_key = get_secret_key()

with app.app_context():
    ensure_tables()
    ensure_default_admin()


@app.before_request
def load_current_user():
    g.current_user = None
    user_id = session.get('user_id')
    if not user_id:
        return
    user = get_user_by_id(user_id)
    if not user or not user.get('is_active'):
        session.clear()
        return
    g.current_user = user

# ===== 注册蓝图模块 =====
register_auth(app)
# /inventory -> 库存盘点
app.register_blueprint(inventory_bp, url_prefix='/inventory')
# /purchase -> 采购入库
app.register_blueprint(purchase_bp, url_prefix='/purchase')
# /stockin -> 操作入库
app.register_blueprint(stocking_bp, url_prefix='/stockin')
# /logs -> 操作日志
app.register_blueprint(logs_bp)
# VPS 监控相关接口与页面
app.register_blueprint(vps_monitor_bp)
# /wechat-shop -> 微信小店
app.register_blueprint(wechat_shop_bp, url_prefix='/wechat_shop')
# /invoicing -> 发票核对
app.register_blueprint(invoicing_bp, url_prefix='/invoicing')

# ===== 总入口页面 =====
@app.route('/')
@login_required
def index():
    """
    总入口页面（Dashboard）
    显示各模块的按钮，点击跳转到各模块页面
    """
    return render_template('index.html', can_module=has_module_permission)

# ===== 主程序入口 =====
if __name__ == '__main__':
    # 开发模式运行，监听所有 IP 地址，端口 5001


    print(">>> 包材管理系统启动")
    print(">>> 数据库路径: data/main.db")
    app.run(host="0.0.0.0", port=5001, debug=True)
