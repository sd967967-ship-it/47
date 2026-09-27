"""
47 desktop control — mouse, keyboard, screenshot (local only).
Pattern from PyAutoGUI-based assistants: all actions stay on this machine,
clicks/typing require the dashboard token + (for risky keys) a staged
"confirm", mirroring shell.py. Import pyautogui lazily so 47 runs without it.
Optional: pip install pyautogui pillow
"""
import os

RISKY_KEYS = {"delete", "backspace", "enter", "tab", "esc", "win", "alt", "ctrl"}


def _gui():
    import pyautogui  # lazy, optional
    pyautogui.FAILSAFE = True
    return pyautogui


def move_mouse(x: int, y: int) -> str:
    try:
        _gui().moveTo(int(x), int(y), duration=0.2)
        return f"Moved mouse to {x}, {y}."
    except Exception as e:
        return f"Couldn't move mouse: {e}"


def click(button: str = "left") -> str:
    try:
        _gui().click(button=button)
        return f"Clicked {button}."
    except Exception as e:
        return f"Couldn't click: {e}"


def type_text(text: str, confirm_token: str = "") -> str:
    """Type text locally. Refuses risky single keys without confirm_token='confirm'."""
    low = text.strip().lower()
    if low in RISKY_KEYS and confirm_token.strip().lower() != "confirm":
        return f"That key ({text}) needs a 'confirm' before I press it."
    try:
        _gui().typewrite(text, interval=0.02)
        return "Typed it."
    except Exception as e:
        return f"Couldn't type: {e}"


def press_key(key: str, confirm_token: str = "") -> str:
    return type_text(key, confirm_token)


def screenshot_region(path: str = "") -> str:
    """Save a local screenshot for on-demand vision. Never uploads by itself."""
    try:
        from datetime import datetime
        out = path or os.path.join(os.path.expanduser("~"),
                                   f"47_shot_{datetime.now():%Y%m%d_%H%M%S}.png")
        _gui().screenshot(out)
        return out
    except Exception as e:
        return f"Couldn't take a screenshot: {e}"
