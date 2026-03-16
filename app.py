# app.py
# =====================================================
# 包材管理系统主程序
# 功能：
# 1. 提供总入口页面（Dashboard）展示各模块按钮
# 2. 注册库存盘点模块（inventory）
# 3. 注册采购入库模块（purchase）
# =====================================================

from flask import Flask, render_template, jsonify, render_template_string

import subprocess

# ===== 导入模块蓝图 =====
from inventory.routes import inventory_bp   # 库存盘点模块
from purchase.routes import purchase_bp     # 采购模块
from stocking.routes import stocking_bp     #操作入库

# ===== 创建 Flask 应用 =====
app = Flask(__name__)

# ===== 注册蓝图模块 =====
# /inventory -> 库存盘点
app.register_blueprint(inventory_bp, url_prefix='/inventory')
# /purchase -> 采购入库
app.register_blueprint(purchase_bp, url_prefix='/purchase')
# /stockin -> 操作入库
app.register_blueprint(stocking_bp, url_prefix='/stockin')

# ===== VPS 监控辅助函数 =====
def get_xray_status():
    """
    获取 xray 服务状态。
    本地开发环境大概率没有 xray，因此异常时返回 unknown。
    """
    try:
        result = subprocess.run(
            ["systemctl", "is-active", "xray"],
            capture_output=True,
            text=True,
            timeout=3
        )
        status = result.stdout.strip()
        return status if status else "unknown"
    except Exception:
        return "unknown"


def get_vps_traffic_gb():
    """
    从 /proc/net/dev 读取服务器累计网络流量。
    优先识别常见公网网卡名；如果没有命中，则自动选取第一个非 lo 网卡。
    在 macOS 本地开发环境下通常没有该文件，因此返回 None。
    """
    try:
        with open("/proc/net/dev", "r", encoding="utf-8") as f:
            lines = f.readlines()

        selected_data = None
        preferred_names = ("eth0", "ens3", "enp1s0")

        # 先按常见公网网卡名查找
        for line in lines:
            stripped = line.strip()
            if not stripped or ":" not in stripped:
                continue

            iface = stripped.split(":", 1)[0].strip()
            if iface in preferred_names:
                selected_data = stripped.split(":", 1)[1].split()
                break

        # 如果没找到，再退而求其次：取第一个非 lo 的网卡
        if selected_data is None:
            for line in lines:
                stripped = line.strip()
                if not stripped or ":" not in stripped:
                    continue

                iface = stripped.split(":", 1)[0].strip()
                if iface != "lo":
                    selected_data = stripped.split(":", 1)[1].split()
                    break

        if selected_data is None:
            return None

        rx = int(selected_data[0])
        tx = int(selected_data[8])

        total_gb = (rx + tx) / 1024 / 1024 / 1024
        return round(total_gb, 2)
    except Exception:
        return None

def get_xray_log():
    """
    读取最近的 xray 日志（最多 30 行）。
    本地环境没有 journalctl 时返回提示。
    """
    try:
        result = subprocess.run(
            ["journalctl", "-u", "xray", "-n", "30", "--no-pager"],
            capture_output=True,
            text=True,
            timeout=3
        )
        return result.stdout
    except Exception:
        return "本地环境无法读取 xray 日志"

# ===== 总入口页面 =====
@app.route('/')
def index():
    """
    总入口页面（Dashboard）
    显示各模块的按钮，点击跳转到各模块页面
    """
    return render_template('index.html')

@app.route('/vps-status')
def vps_status():
    """
    返回最小版 VPS 状态信息。
    先提供 xray 状态和累计流量，便于后续再逐步扩展。
    """
    return jsonify({
        'xray_status': get_xray_status(),
        'traffic_gb': get_vps_traffic_gb()
    })

@app.route('/vps-log')
def vps_log():
    """
    查看最近的 xray 日志
    """
    log = get_xray_log()
    return "<pre>" + log + "</pre>"

@app.route('/vps-monitor')
def vps_monitor():
    """
    简易隐藏监控页。
    第一版只读，不提供重启和修改配置功能。
    """
    xray_status = get_xray_status()
    traffic_gb = get_vps_traffic_gb()

    html = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VPS 状态</title>
        <style>
            body {
                font-family: "Microsoft YaHei", Arial, sans-serif;
                margin: 30px;
                line-height: 1.8;
            }
            .card {
                max-width: 520px;
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
            }
            h2 {
                margin-top: 0;
            }
            .row {
                margin: 10px 0;
            }
            .label {
                font-weight: bold;
                display: inline-block;
                width: 110px;
            }
            .hint {
                margin-top: 16px;
                color: #666;
                font-size: 14px;
            }
            a {
                color: #0b57d0;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>VPS 简易状态页</h2>
            <div class="row"><span class="label">xray 状态：</span>{{ xray_status }}</div>
            <div class="row"><span class="label">累计流量：</span>{{ traffic_text }}</div>
            <div class="row"><span class="label">JSON 接口：</span><a href="/vps-status">/vps-status</a></div>
            <div class="row"><span class="label">xray 日志：</span><a href="/vps-log">查看日志</a></div>
            <div class="hint">说明：本页第一版只做查看，不做重启和修改配置。</div>
        </div>
    </body>
    </html>
    """

    traffic_text = f"{traffic_gb} GB" if traffic_gb is not None else "本地环境不可用"

    return render_template_string(
        html,
        xray_status=xray_status,
        traffic_text=traffic_text
    )

# ===== 主程序入口 =====
if __name__ == '__main__':
    # 开发模式运行，监听所有 IP 地址，端口 5001


    print(">>> 包材管理系统启动")
    print(">>> 数据库路径: data/packaging.db")
    app.run(host="0.0.0.0", port=5001, debug=True)
