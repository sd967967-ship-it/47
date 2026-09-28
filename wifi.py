"""
47 Wi-Fi insight — real local scans, no extra tools.

Windows: `netsh wlan show networks mode=bssid` (visible networks with
signal/channel/auth) and `netsh wlan show interfaces` (current link).
Linux best-effort via nmcli; other platforms report honestly.
Read-only: never connects, never changes anything.
"""
import platform
import re


def _run(cmd: str) -> str:
    import shell
    return shell.run(cmd, timeout=30)


def parse_networks(output: str):
    """Parse `netsh wlan show networks` blocks into dicts. Pure function."""
    networks = []
    current = None
    for line in output.splitlines():
        ssid = re.match(r"^SSID\s+\d+\s+:\s*(.*)$", line)
        if ssid:
            if current:
                networks.append(current)
            current = {"ssid": ssid.group(1).strip() or "(hidden)"}
            continue
        field = re.match(r"^\s+([A-Za-z][A-Za-z /]*?)\s+:\s+(.*)$", line or "")
        if field and current is not None:
            current[field.group(1).strip().lower()] = field.group(2).strip()
    if current:
        networks.append(current)
    return networks


def _signal_pct(net: dict) -> int:
    match = re.search(r"(\d+)", net.get("signal", ""))
    return int(match.group(1)) if match else 0


def scan_networks():
    """Visible Wi-Fi networks now. Returns (report-text, chart-data)."""
    if platform.system() == "Windows":
        out = _run("netsh wlan show networks mode=bssid")
    else:
        try:
            out = _run("nmcli -t -f SSID,SIGNAL,CHAN,SECURITY dev wifi list --rescan yes")
            return _parse_nmcli(out), None
        except Exception as e:
            return [], f"Wi-Fi scan isn't supported on {platform.system()}: {e}"
    if "is not recognized" in out or "not recognized" in out:
        return [], "Wi-Fi scanning isn't available (no wireless interface found)."
    nets = parse_networks(out)
    if not nets:
        return [], "No Wi-Fi networks visible right now."
    nets.sort(key=_signal_pct, reverse=True)
    lines = []
    for net in nets[:12]:
        lines.append(f"- {net['ssid']}: {net.get('signal', '?')} "
                     f"(ch {net.get('channel', '?')}, {net.get('authentication', '?')})")
    report = "Wi-Fi around you, strongest first:\n" + "\n".join(lines)
    chart = {"labels": [n["ssid"][:14] for n in nets[:8]],
             "values": [_signal_pct(n) for n in nets[:8]]}
    return chart, report


def _parse_nmcli(output: str):
    return [], output[:1500]


def current_link() -> str:
    """The connected network and its signal, or an honest negative."""
    if platform.system() != "Windows":
        return "Current-link detail is supported on Windows only right now."
    out = _run("netsh wlan show interfaces")
    ssid = re.search(r"^\s*SSID\s+:\s*(.+)$", out, re.M)
    sig = re.search(r"^\s*Signal\s+:\s*(.+)$", out, re.M)
    state = re.search(r"^\s*State\s+:\s*(.+)$", out, re.M)
    if not ssid:
        return "No Wi-Fi connection active."
    return (f"Connected to {ssid.group(1).strip()} — signal {sig.group(1).strip() if sig else '?'}, "
            f"state {state.group(1).strip() if state else '?'}.")


def coverage_tips() -> str:
    return ("Quick coverage tips: put the main router central and high, add a "
            "mesh node per weak floor, keep routers away from metal and "
            "microwaves, and prefer 5 GHz near the router / 2.4 GHz far away.")
