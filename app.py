# app.py
# =====================================================
# 包材管理系统主程序
# 功能：
# 1. 提供总入口页面（Dashboard）展示各模块按钮
# 2. 注册库存盘点模块（inventory）
# 3. 注册采购入库模块（purchase）
# =====================================================

from flask import Flask, render_template, jsonify, render_template_string
from pathlib import Path
from datetime import datetime
import json
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
MONTHLY_TRAFFIC_FILE = Path("data/vps_monthly_traffic.json")


def ensure_data_dir():
    """确保 data 目录存在。"""
    MONTHLY_TRAFFIC_FILE.parent.mkdir(parents=True, exist_ok=True)


def get_current_month_key():
    """返回当前月份键，如 2026-03。"""
    return datetime.now().strftime("%Y-%m")

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

def get_monthly_traffic_gb():
    """
    计算“本月累计流量”。
    逻辑：
    1. 读取当前开机累计流量（get_vps_traffic_gb）
    2. 若本月第一次访问，则把当前值记为 baseline_gb
    3. 同月内返回 current_gb - baseline_gb
    4. 跨月后自动重置 baseline_gb
    """
    current_gb = get_vps_traffic_gb()
    if current_gb is None:
        return None

    ensure_data_dir()
    month_key = get_current_month_key()

    if MONTHLY_TRAFFIC_FILE.exists():
        try:
            with open(MONTHLY_TRAFFIC_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
        except Exception:
            saved = {}
    else:
        saved = {}
    
    # 如果文件不存在，说明是第一次上线
    # 直接把 baseline 设为 0，这样页面会显示当前总流量而不是 0
    if not MONTHLY_TRAFFIC_FILE.exists():
        saved = {
            "month": month_key,
            "baseline_gb": 0
        }
        with open(MONTHLY_TRAFFIC_FILE, "w", encoding="utf-8") as f:
            json.dump(saved, f, ensure_ascii=False, indent=2)
        return round(current_gb, 2)

    saved_month = saved.get("month")
    baseline_gb = saved.get("baseline_gb")

    # 新月份或首次使用时，重置基线
    if saved_month != month_key or baseline_gb is None:
        baseline_gb = current_gb
        saved = {
            "month": month_key,
            "baseline_gb": baseline_gb
        }
        with open(MONTHLY_TRAFFIC_FILE, "w", encoding="utf-8") as f:
            json.dump(saved, f, ensure_ascii=False, indent=2)
        return round(current_gb, 2)

    monthly_gb = current_gb - float(baseline_gb)
    if monthly_gb < 0:
        monthly_gb = 0.0

    return 0.0


def get_memory_usage_text():
    """读取内存使用情况，返回类似 412MB / 1972MB。"""
    try:
        result = subprocess.run(
            ["free", "-m"],
            capture_output=True,
            text=True,
            timeout=3
        )
        lines = result.stdout.splitlines()
        for line in lines:
            if line.startswith("Mem:"):
                parts = line.split()
                used = parts[2]
                total = parts[1]
                return f"{used}MB / {total}MB"
        return "unknown"
    except Exception:
        return "unknown"


def get_uptime_text():
    """读取服务器运行时间。"""
    try:
        result = subprocess.run(
            ["uptime", "-p"],
            capture_output=True,
            text=True,
            timeout=3
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"
    
def get_cpu_usage_text():
    """读取 CPU 使用率（1秒平均）。"""
    try:
        result = subprocess.run(
            ["top", "-bn1"],
            capture_output=True,
            text=True,
            timeout=3
        )
        for line in result.stdout.splitlines():
            if "Cpu(s)" in line or "CPU:" in line:
                parts = line.split(",")
                for p in parts:
                    if "id" in p:
                        idle = float(p.strip().split()[0])
                        used = 100 - idle
                        return f"{round(used,1)}%"
        return "unknown"
    except Exception:
        return "unknown"

def get_disk_usage_text():
    """读取根分区磁盘使用情况。"""
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=3
        )
        lines = result.stdout.splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            used = parts[2]
            total = parts[1]
            percent = parts[4]
            return f"{used} / {total} ({percent})"
        return "unknown"
    except Exception:
        return "unknown"

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
    提供 xray 状态、开机累计流量、本月累计流量、内存和运行时间。
    """
    return jsonify({
        'xray_status': get_xray_status(),
        'traffic_gb': get_vps_traffic_gb(),
        'monthly_traffic_gb': get_monthly_traffic_gb(),
        'memory_usage': get_memory_usage_text(),
        'cpu_usage': get_cpu_usage_text(),
        'disk_usage': get_disk_usage_text(),
        'uptime': get_uptime_text()
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
    monthly_traffic_gb = get_monthly_traffic_gb()
    memory_usage = get_memory_usage_text()
    cpu_usage = get_cpu_usage_text()
    disk_usage = get_disk_usage_text()
    uptime_text = get_uptime_text()

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
            <div class="row"><span class="label">开机累计流量：</span>{{ traffic_text }}</div>
            <div class="row"><span class="label">本月累计流量：</span>{{ monthly_traffic_text }}</div>
            <div class="row"><span class="label">CPU 使用：</span>{{ cpu_usage }}</div>
            <div class="row"><span class="label">内存使用：</span>{{ memory_usage }}</div>
            <div class="row"><span class="label">磁盘使用：</span>{{ disk_usage }}</div>
            <div class="row"><span class="label">运行时间：</span>{{ uptime_text }}</div>
            <div class="row"><span class="label">JSON 接口：</span><a href="/vps-status">/vps-status</a></div>
            <div class="row"><span class="label">xray 日志：</span><a href="/vps-log">查看日志</a></div>
            <div class="hint">说明：本页第一版只做查看，不做重启和修改配置。</div>
        </div>
    </body>
    </html>
    """

    traffic_text = f"{traffic_gb} GB" if traffic_gb is not None else "本地环境不可用"
    monthly_traffic_text = f"{monthly_traffic_gb} GB" if monthly_traffic_gb is not None else "本地环境不可用"

    return render_template_string(
        html,
        xray_status=xray_status,
        traffic_text=traffic_text,
        monthly_traffic_text=monthly_traffic_text,
        memory_usage=memory_usage,
        cpu_usage=cpu_usage,
        disk_usage=disk_usage,
        uptime_text=uptime_text
    )

# ===== 主程序入口 =====
if __name__ == '__main__':
    # 开发模式运行，监听所有 IP 地址，端口 5001


    print(">>> 包材管理系统启动")
    print(">>> 数据库路径: data/packaging.db")
    app.run(host="0.0.0.0", port=5001, debug=True)
