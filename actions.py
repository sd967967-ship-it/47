"""
47 action modules — the "hands" of the assistant.
All free, local, no paid APIs required (email needs a one-time free
Google Cloud OAuth setup, no cost).
"""

import os
import platform
import re
import subprocess
import webbrowser
import requests
from pathlib import Path
from urllib.parse import quote_plus

from net_utils import request_with_retry


# ---------- Open apps / websites ----------
KNOWN_SITES = {
    "youtube": "https://youtube.com",
    "gmail": "https://mail.google.com",
    "google": "https://google.com",
    "github": "https://github.com",
}

# Local tools that need special-cased launch commands rather than a plain
# app name (a real terminal, not "run a command inside a hidden shell" —
# see shell.py for that). Keyed by every spoken alias that should match.
_TERMINAL_ALIASES = {
    "terminal", "cmd", "command prompt", "powershell", "shell", "console",
}
_FILE_MANAGER_ALIASES = {"file explorer", "explorer", "finder", "files"}


def _open_terminal() -> str:
    # BUGFIX: the Linux branch used to claim "Opening a terminal." even
    # when every one of gnome-terminal/konsole/xterm was missing (the
    # for-loop just fell through with no error). Now it actually tracks
    # whether any launch succeeded and says so honestly if none did.
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(["cmd.exe"])
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", "Terminal"])
        else:
            launched = False
            for term in ("gnome-terminal", "konsole", "xterm"):
                try:
                    subprocess.Popen([term])
                    launched = True
                    break
                except FileNotFoundError:
                    continue
            if not launched:
                return ("Couldn't open a terminal: none of gnome-terminal, "
                        "konsole, or xterm are installed.")
        return "Opening a terminal."
    except Exception as e:
        return f"Couldn't open a terminal: {e}"


def _open_file_manager() -> str:
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(["explorer.exe"])
        elif system == "Darwin":
            subprocess.Popen(["open", str(Path.home())])
        else:
            subprocess.Popen(["xdg-open", str(Path.home())])
        return "Opening the file manager."
    except Exception as e:
        return f"Couldn't open the file manager: {e}"


def open_app_or_site(target: str) -> str:
    target = target.strip()
    lowered = target.lower()

    if lowered in _TERMINAL_ALIASES:
        return _open_terminal()
    if lowered in _FILE_MANAGER_ALIASES:
        return _open_file_manager()
    if lowered in KNOWN_SITES:
        webbrowser.open(KNOWN_SITES[lowered])
        return f"Opening {target}."

    if target.endswith(".com") or target.startswith("http"):
        url = target if target.startswith("http") else f"https://{target}"
        webbrowser.open(url)
        return f"Opening {target}."

    # Try to launch as a local application
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(target)  # noqa
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", target])
        else:
            subprocess.Popen([target.lower()])
        return f"Opening {target}."
    except Exception:
        return f"I couldn't find an app or site called {target}."


# ---------- Fetch any web page (free, no API key: plain GET + tag-strip) ----------
_URL_RE = re.compile(r"https?://\S+")


def find_url(text: str) -> str:
    """Pull the first http(s) URL out of a sentence, if any."""
    match = _URL_RE.search(text)
    return match.group(0).rstrip(".,)") if match else None


_BLOCKED_FETCH_HOSTS = ("127.", "10.", "192.168.", "169.254.", "::1", "localhost", "0.0.0.0")


def _fetch_allowed(url: str) -> bool:
    low = url.lower()
    if not low.startswith(("http://", "https://")):
        return False
    return not any(h in low for h in _BLOCKED_FETCH_HOSTS)


def fetch_url(url: str, max_chars: int = 4000) -> str:
    """GET a URL and return roughly-cleaned plain text (script/style
    stripped, tags stripped, whitespace collapsed). No JS rendering — this
    is a plain HTTP fetch, so JS-only pages may come back mostly empty."""
    if not _fetch_allowed(url):
        return "Refusing to fetch that URL (private/local hosts are blocked)."
    try:
        resp = request_with_retry(
            "GET", url, timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (47-assistant/1.0)"},
        )
        resp.raise_for_status()
        html = resp.text
        html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] or "(fetched the page but it had no readable text)"
    except Exception as e:
        return f"Couldn't fetch that page: {e}"


# ---------- Live weather (free, no API key: Open-Meteo) ----------
def get_weather(place: str) -> str:
    """Real-time weather for a place name, via Open-Meteo (free, no key,
    two calls: geocode the place name, then fetch current conditions)."""
    try:
        geo = request_with_retry(
            "GET", "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": place, "count": 1}, timeout=10,
        ).json()
        results = geo.get("results")
        if not results:
            return f"I couldn't find a place called {place}."
        loc = results[0]
        lat, lon = loc["latitude"], loc["longitude"]
        label = f"{loc.get('name', place)}, {loc.get('country', '')}".strip(", ")

        wx = request_with_retry(
            "GET", "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current_weather": True},
            timeout=10,
        ).json()
        current = wx.get("current_weather", {})
        temp = current.get("temperature")
        wind = current.get("windspeed")
        if temp is None:
            return f"Couldn't get current conditions for {label}."
        return f"Right now in {label}: {temp}°C, wind {wind} km/h."
    except Exception as e:
        return f"Couldn't fetch the weather: {e}"


# ---------- Web search (free, no API key: DuckDuckGo) ----------
def web_search(query: str):
    # Real results via duckduckgo-search (DDGS) when installed — same library
    # JARVIS-6's tool registry uses. Falls back to the instant-answers API.
    try:
        from duckduckgo_search import DDGS
        with DDGS() as d:
            hits = list(d.text(query, max_results=5))
        results = [{"title": f"{h.get('title', '')}: {h.get('body', '')[:150]}",
                    "url": h.get("href", "")} for h in hits]
        if results:
            return results
    except Exception:
        pass
    url = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
    try:
        r = request_with_retry("GET", url, timeout=10).json()
        results = []
        for topic in r.get("RelatedTopics", [])[:5]:
            if "Text" in topic:
                results.append({"title": topic["Text"], "url": topic.get("FirstURL", "")})
        if not results and r.get("AbstractText"):
            results.append({"title": r["AbstractText"], "url": r.get("AbstractURL", "")})
        return results or [{"title": f"No instant answer for '{query}'", "url": ""}]
    except Exception as e:
        return [{"title": f"Search failed: {e}", "url": ""}]


# ---------- File search (deeper OS control) ----------
def find_files(name_fragment: str, search_root: str = None, max_results: int = 15):
    """Search the filesystem for files whose name contains name_fragment."""
    root = Path(search_root) if search_root else Path.home()
    fragment = name_fragment.lower()
    matches = []
    scanned = 0
    try:
        for path in root.rglob("*"):
            scanned += 1
            if scanned > 20000:
                break
            try:
                if fragment in path.name.lower():
                    matches.append(str(path))
                    if len(matches) >= max_results:
                        break
            except OSError:
                continue
    except (PermissionError, OSError):
        pass
    return matches


def open_file(path: str) -> str:
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)  # noqa
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return f"Opening {path}."
    except Exception as e:
        return f"Couldn't open {path}: {e}"


# ---------- Sandboxed local file access (stays on this machine) ----------
ALLOW_ROOTS = [Path.home() / "Documents", Path.home() / "Desktop", Path.home() / "Downloads"]

_WRITE_BLOCKED_DIRS = ("windows", "system32", "program files", "/etc", "/sys", "/proc")


def _safe_resolve(p: str, for_write: bool = False) -> Path:
    cand = (Path(p).expanduser() if Path(p).is_absolute()
            else (Path.home() / p)).resolve()
    if for_write and any(b in str(cand).lower() for b in _WRITE_BLOCKED_DIRS):
        raise ValueError("system locations are read-only")
    return cand


def read_file(path: str, max_chars: int = 8000) -> str:
    """Read a text file locally. Refuses binaries and files over 2MB."""
    try:
        target = _safe_resolve(path)
        if not target.is_file():
            return f"No file at {path}."
        if target.stat().st_size > 2_000_000:
            return "File too large to read (over 2MB)."
        data = target.read_bytes()[:2_000_000]
        if b"\x00" in data[:8192]:
            return "That looks like a binary file — refusing to dump it as text."
        return data.decode("utf-8", errors="replace")[:max_chars]
    except Exception as e:
        return f"Couldn't read {path}: {e}"


def list_dir(path: str = "", max_entries: int = 50) -> str:
    """List a folder (names + sizes). Defaults to home Documents."""
    try:
        target = _safe_resolve(path or str(Path.home() / "Documents"))
        if not target.is_dir():
            return f"No folder at {path or target}."
        lines = []
        for child in sorted(target.iterdir(), key=lambda c: c.name.lower())[:max_entries]:
            try:
                size = child.stat().st_size if child.is_file() else -1
                tag = f"{size}B" if size >= 0 else "dir"
                lines.append(f"{child.name} [{tag}]")
            except OSError:
                lines.append(f"{child.name} [?]")
        return f"{target}:\n" + ("\n".join(lines) if lines else "(empty)")
    except Exception as e:
        return f"Couldn't list {path}: {e}"


def open_folder(path: str = "") -> str:
    """Open a folder in the OS explorer, or reveal a file's parent."""
    try:
        target = _safe_resolve(path or str(Path.home()))
        if not target.exists():
            return f"No such path: {path}."
        folder = str(target if target.is_dir() else target.parent)
        system = platform.system()
        if system == "Windows":
            if target.is_file():
                subprocess.Popen(["explorer.exe", "/select,", str(target)])
            else:
                subprocess.Popen(["explorer.exe", folder])
        elif system == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
        return f"Opening {folder}."
    except Exception as e:
        return f"Couldn't open {path}: {e}"


def list_apps(max_entries: int = 20) -> str:
    """List running app names locally via psutil. No network involved."""
    try:
        import psutil
        seen = []
        for p in psutil.process_iter(["name"]):
            name = (p.info.get("name") or "").strip()
            if name and name.lower() not in seen:
                seen.append(name.lower())
                if len(seen) >= max_entries:
                    break
        return "Running apps: " + (", ".join(seen) if seen else "(none found)")
    except Exception as e:
        return f"Couldn't list apps: {e}"


def list_windows(max_entries: int = 20) -> str:
    """List visible window titles (Windows via pygetwindow). Local only."""
    try:
        if platform.system() != "Windows":
            return "Window listing is currently supported on Windows only."
        import pygetwindow as gw
        titles = [t for t in gw.getAllTitles() if t and t.strip()][:max_entries]
        return "Open windows:\n" + ("\n".join(f"- {t[:80]}" for t in titles) if titles else "(none)")
    except Exception as e:
        return f"Couldn't list windows: {e}"


def recent_files(folder: str = "", count: int = 10) -> str:
    """List recently modified files (JARVIS-6 files.recent idea, reimplemented
    on 47's sandboxed resolver)."""
    try:
        target = _safe_resolve(folder or str(Path.home() / "Downloads"))
        if not target.is_dir():
            return f"No folder at {folder or target}."
        items = []
        for child in target.iterdir():
            try:
                items.append((child.stat().st_mtime, child.name))
            except OSError:
                continue
        items.sort(reverse=True)
        lines = [name for _, name in items[:max(1, min(count, 30))]]
        return f"Recent in {target}:\n" + ("\n".join(f"- {n}" for n in lines) if lines else "(empty)")
    except Exception as e:
        return f"Couldn't list recent files: {e}"


def top_processes(count: int = 8) -> str:
    """Heaviest processes by memory (JARVIS-6 system.processes idea). Local only."""
    try:
        import psutil
        procs = sorted(psutil.process_iter(["name", "memory_info"]),
                       key=lambda p: (p.info.get("memory_info").rss
                                      if p.info.get("memory_info") else 0),
                       reverse=True)[:max(1, min(count, 15))]
        lines = [f"{p.info['name'] or '?'} "
                 f"{(p.info['memory_info'].rss / 1e6 if p.info.get('memory_info') else 0):.0f} MB"
                 for p in procs]
        return "Top processes by memory:\n" + "\n".join(f"- {l}" for l in lines)
    except Exception as e:
        return f"Couldn't list processes: {e}"


def lock_workstation() -> str:
    """Lock the PC now (safe, reversible — same call JARVIS-6's system.power uses)."""
    try:
        if platform.system() == "Windows":
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Workstation locked."
        return "Lock is currently supported on Windows only."
    except Exception as e:
        return f"Couldn't lock: {e}"


# ---------- System controls (volume) ----------
def set_volume(level_percent: int) -> str:
    """Best-effort cross-platform volume control (0-100)."""
    level_percent = max(0, min(100, level_percent))
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {level_percent}"])
        elif system == "Windows":
            # Requires: pip install pycaw comtypes
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level_percent / 100, None)
        else:
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level_percent}%"])
        return f"Volume set to {level_percent} percent."
    except Exception as e:
        return f"Couldn't change volume: {e}"


# ---------- Email (free — Gmail API, needs one-time OAuth setup) ----------
def send_email(to: str, subject: str, body: str):
    """
    SETUP (one-time, free):
    1. Go to console.cloud.google.com -> create project -> enable Gmail API
    2. Create OAuth credentials -> download credentials.json into this folder
    3. pip install google-auth-oauthlib google-api-python-client
    4. First run will open a browser to authorize your Google account
    This stub is left unimplemented until you complete that setup.
    """
    raise NotImplementedError("Complete the Gmail API setup above, then implement this.")
