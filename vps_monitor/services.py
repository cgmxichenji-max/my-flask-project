from pathlib import Path
from datetime import datetime
import json
import subprocess

# VPS 月流量记录文件
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

    return round(monthly_gb, 2)


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
                        return f"{round(used, 1)}%"
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

