"""
Vision & environmental awareness for 47.

Three layers, each opt-in except the lightest one:
1. Active window/app tracking (always on, lightweight, no images) —
   knows *what you're doing* without ever capturing pixels.
2. Screen understanding (on-demand: "what's on my screen") — takes one
   screenshot, sends it to a free vision model, describes it.
3. Camera snapshot (on-demand only: "what do you see") — takes one photo
   from the webcam, describes it. Never runs continuously.

PRIVACY: nothing here runs a hidden background camera or continuous
screen recording. Screen/camera capture only happens the moment you ask.
requirements: mss, opencv-python, pygetwindow (Windows), pyobjc (Mac, optional)
"""

import base64
import os
import platform
import subprocess

import requests

# FIX for "active-window tracking needs xdotool, which doesn't work under
# Wayland (most modern Linux desktops) and isn't even in requirements.txt":
# xdotool is an X11 tool with no Wayland equivalent that works the same
# way — there's no portable one-liner fix, since Wayland deliberately
# restricts cross-app window introspection for security reasons. Rather
# than silently retrying a doomed xdotool call every 3 seconds forever
# (see main.py's start_window_tracking), detect Wayland up front and warn
# once with an honest explanation instead of a bare "unknown" nobody can
# act on. xdotool also isn't a pip package — it's a system package
# (apt/dnf/pacman), so it was correctly left out of requirements.txt; noted
# here instead since that's where someone hits the actual failure.
_warned_wayland = False
_warned_no_xdotool = False

# BUGFIX: "llama-3.2-90b-vision-preview" was retired by Groq. Vision now
# routes through the Grok provider (providers/grok.py send_vision) — see
# describe_screen/describe_camera below. Without a Grok key or a
# vision-capable model they return an honest unavailable message.


# ---------- Layer 1: active window tracking (always on, no images) ----------
def get_active_window_title() -> str:
    system = platform.system()
    try:
        if system == "Windows":
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "unknown"
        elif system == "Darwin":
            script = (
                'tell application "System Events" to get name of first '
                'application process whose frontmost is true'
            )
            result = subprocess.run(["osascript", "-e", script],
                                     capture_output=True, text=True, timeout=3)
            return result.stdout.strip() or "unknown"
        else:  # Linux
            global _warned_wayland, _warned_no_xdotool
            if os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland":
                if not _warned_wayland:
                    print("[vision] Active-window tracking needs xdotool, which "
                          "doesn't work under Wayland. Skipping (this only "
                          "warns once). Switch to an X11 session for this "
                          "feature, or ignore it — nothing else depends on it.")
                    _warned_wayland = True
                return "unknown (Wayland session — active-window tracking unavailable)"
            try:
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True, text=True, timeout=3,
                )
                return result.stdout.strip() or "unknown"
            except FileNotFoundError:
                if not _warned_no_xdotool:
                    print("[vision] xdotool isn't installed (it's a system "
                          "package, e.g. `sudo apt install xdotool`, not a pip "
                          "package). Active-window tracking disabled until "
                          "it's installed. This only warns once.")
                    _warned_no_xdotool = True
                return "unknown (xdotool not installed)"
    except Exception:
        return "unknown"


# ---------- Layer 2: screen understanding (on-demand) ----------
def capture_screenshot_b64() -> str:
    import mss
    import mss.tools
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        img_bytes = mss.tools.to_png(shot.rgb, shot.size)
        return base64.b64encode(img_bytes).decode("utf-8")


def describe_screen(question: str = "What's on my screen right now?") -> str:
    try:
        img_b64 = capture_screenshot_b64()
    except Exception as e:
        return f"Couldn't capture the screen: {e}"
    try:
        from providers import get_active_provider
        provider, _name = get_active_provider()
        send_vision = getattr(provider, "send_vision", None) if provider else None
        if send_vision is None:
            raise RuntimeError("no vision provider")
        return send_vision(question, img_b64, "image/png")
    except Exception:
        return ("Screen understanding needs a vision-capable brain — "
                "47's vision is unavailable right now.")


# ---------- Layer 3: camera snapshot (on-demand only, never continuous) ----------
def capture_camera_b64() -> str:
    import cv2
    cam = cv2.VideoCapture(0)
    try:
        ok, frame = cam.read()
        if not ok:
            raise RuntimeError("Could not read from webcam.")
        ok, buf = cv2.imencode(".jpg", frame)
        return base64.b64encode(buf).decode("utf-8")
    finally:
        cam.release()


def describe_camera(question: str = "What do you see?") -> str:
    try:
        img_b64 = capture_camera_b64()
    except Exception as e:
        return f"Couldn't access the camera: {e}"
    try:
        from providers import get_active_provider
        provider, _name = get_active_provider()
        send_vision = getattr(provider, "send_vision", None) if provider else None
        if send_vision is None:
            raise RuntimeError("no vision provider")
        return send_vision(question, img_b64, "image/jpeg")
    except Exception:
        return ("Camera understanding needs a vision-capable brain — "
                "47's vision is unavailable right now.")
