from flask import Flask, render_template

# ===== 导入模块蓝图 =====
from inventory.routes import inventory_bp    # 库存盘点模块
from purchase.routes import purchase_bp      # 采购模块
from stocking.routes import stocking_bp      # 操作入库
from logs.routes import logs_bp             # 操作日志模块
from vps_monitor import vps_monitor_bp       # VPS 监控模块
from wechat_shop import wechat_shop_bp       # 微信小店模块

# ===== 创建 Flask 应用 =====
app = Flask(__name__)
# ===== 数据库统一配置 =====
app.config['DATABASE_PATH'] = 'data/main.db'
app.secret_key = "chenxi98_logs_session_key"

# ===== 注册蓝图模块 =====
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

# ===== 总入口页面 =====
@app.route('/')
def index():
    """
    总入口页面（Dashboard）
    显示各模块的按钮，点击跳转到各模块页面
    """
    return render_template('index.html')

# ===== 主程序入口 =====
if __name__ == '__main__':
    # 开发模式运行，监听所有 IP 地址，端口 5001


    print(">>> 包材管理系统启动")
    print(">>> 数据库路径: data/main.db")
    app.run(host="0.0.0.0", port=5001, debug=True)
