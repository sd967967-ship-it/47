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

# BUGFIX: "llama-3.2-90b-vision-preview" was retired by Groq. The current
# (as of writing) multimodal model on Groq's free tier is Llama 4 Scout.
# Check https://console.groq.com/docs/models if this ever 404s again.
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


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


def describe_screen(groq_api_key: str, question: str = "What's on my screen right now?") -> str:
    if not groq_api_key:
        return "Screen understanding needs a free GROQ_API_KEY set (see README)."
    try:
        img_b64 = capture_screenshot_b64()
    except Exception as e:
        return f"Couldn't capture the screen: {e}"
    return _ask_vision_model(groq_api_key, img_b64, question)


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


def describe_camera(groq_api_key: str, question: str = "What do you see?") -> str:
    if not groq_api_key:
        return "Camera understanding needs a free GROQ_API_KEY set (see README)."
    try:
        img_b64 = capture_camera_b64()
    except Exception as e:
        return f"Couldn't access the camera: {e}"
    return _ask_vision_model(groq_api_key, img_b64, question)


def _ask_vision_model(api_key: str, img_b64: str, question: str) -> str:
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_VISION_MODEL,
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url",
                         "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    ],
                }],
                "max_tokens": 300,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Vision model call failed: {e}"
