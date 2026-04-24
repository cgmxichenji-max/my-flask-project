from flask import Blueprint, jsonify, render_template_string

from auth.decorators import admin_required

from .services import (
    get_xray_status,
    get_vps_traffic_gb,
    get_monthly_traffic_gb,
    get_memory_usage_text,
    get_cpu_usage_text,
    get_disk_usage_text,
    get_uptime_text,
    get_xray_log,
)

# VPS 监控蓝图（不加 url_prefix，保持原有 URL 不变）
vps_monitor_bp = Blueprint("vps_monitor", __name__)


@vps_monitor_bp.route('/vps-status')
@admin_required
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


@vps_monitor_bp.route('/vps-log')
@admin_required
def vps_log():
    """
    查看最近的 xray 日志
    """
    log = get_xray_log()
    return "<pre>" + log + "</pre>"


@vps_monitor_bp.route('/vps-monitor')
@admin_required
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
