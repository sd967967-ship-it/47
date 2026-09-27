"""
Ambient awareness — the thing that makes 47 feel "always on" rather than
purely reactive. Runs in the background, polls system vitals, and streams
them to the dashboard continuously (like a HUD).

Uses psutil (free, offline). pip install psutil
"""

import time
import psutil


def _root_mount() -> str:
    import os
    import platform
    if platform.system() == "Windows":
        return os.environ.get("SystemDrive", "C:") + "\\"
    return "/"


def disk_details() -> list:
    """Per-drive {mount, fstype, total_gb, free_gb, pct}. Local psutil only."""
    out = []
    try:
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
                out.append({
                    "mount": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(u.total / 1e9, 1),
                    "free_gb": round(u.free / 1e9, 1),
                    "pct": u.percent,
                })
            except (PermissionError, OSError):
                continue
    except Exception:
        pass
    return out


def get_system_snapshot() -> dict:
    battery = psutil.sensors_battery()
    net = psutil.net_io_counters()
    try:
        disk_pct = psutil.disk_usage(_root_mount()).percent
    except Exception:
        disk_pct = 0.0
    try:
        per_core = psutil.cpu_percent(interval=None, percpu=True)
    except Exception:
        per_core = []
    try:
        top = sorted(
            (p.info for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"])),
            key=lambda d: (d.get("cpu_percent") or 0), reverse=True,
        )[:8]
    except Exception:
        top = []
    try:
        uptime_s = int(time.time() - psutil.boot_time())
    except Exception:
        uptime_s = None
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.3),
        "cpu_per_core": per_core,
        "ram_percent": psutil.virtual_memory().percent,
        "disk_percent": disk_pct,
        "drives": disk_details(),
        "battery_percent": battery.percent if battery else None,
        "battery_plugged": battery.power_plugged if battery else None,
        "net_sent_mb": round(net.bytes_sent / 1e6, 1),
        "net_recv_mb": round(net.bytes_recv / 1e6, 1),
        "process_count": len(psutil.pids()),
        "top_procs": top,
        "uptime_s": uptime_s,
    }


def ambient_loop(push_fn, interval_seconds: int = 5, alert_fn=None):
    """
    Continuously push system vitals to the dashboard.
    push_fn(kind, payload) -> same signature as main.push_to_dashboard
    alert_fn(message) -> optional callback (e.g. speak()) for threshold alerts
    """
    warned_cpu = False
    warned_battery = False
    last_cpu_alert = 0.0
    last_batt_alert = 0.0
    COOLDOWN_S = 1800  # 30 min between repeat alerts — no more nagging

    while True:
        snap = get_system_snapshot()
        push_fn("vitals", snap)
        now = time.time()

        # Simple proactive alerts (ambient intelligence, not just reactive)
        if alert_fn:
            if snap["cpu_percent"] > 90 and now - last_cpu_alert > COOLDOWN_S:
                alert_fn("Heads up — CPU usage is very high right now.")
                last_cpu_alert = now

            if snap["battery_percent"] is not None and snap["battery_percent"] < 15 \
                    and not snap["battery_plugged"] and now - last_batt_alert > COOLDOWN_S:
                alert_fn("Your battery is below 15 percent and not charging.")
                last_batt_alert = now

        time.sleep(interval_seconds)
