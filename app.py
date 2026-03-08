# app.py
# =====================================================
# 包材管理系统主程序
# 功能：
# 1. 提供总入口页面（Dashboard）展示各模块按钮
# 2. 注册库存盘点模块（inventory）
# 3. 注册采购入库模块（purchase）
# =====================================================

from flask import Flask, render_template

# ===== 导入模块蓝图 =====
from inventory.routes import inventory_bp   # 库存盘点模块
from purchase.routes import purchase_bp     # 采购模块

# ===== 创建 Flask 应用 =====
app = Flask(__name__)

# ===== 注册蓝图模块 =====
# /inventory -> 库存盘点
app.register_blueprint(inventory_bp, url_prefix='/inventory')
# /purchase -> 采购入库
app.register_blueprint(purchase_bp, url_prefix='/purchase')


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
1    # 开发模式运行，监听所有 IP 地址，端口 5001


    print(">>> 包材管理系统启动")
    print(">>> 数据库路径: data/packaging.db")
    app.run(host="0.0.0.0", port=5001, debug=True)