"""
Voice engine for 47.

About "the real JARVIS voice": that's Paul Bettany's copyrighted voice
performance from the Marvel/Iron Man films, tied to a real actor's likeness.
This project can't clone a real person's voice or reproduce copyrighted
character audio — that's not something any legitimate free (or paid) tool
here can do.

What this module gives you instead, as the closest free and legal option
in spirit: a calm, precise, deep-ish British male neural voice (Microsoft
Edge's free "en-GB-RyanNeural") for the online path, with a fully offline
fallback (your OS's own TTS voices via pyttsx3, tuned toward a lower/slower
male voice if one is installed) when there's no internet or edge-tts isn't
installed. Change the online voice with:
    export JARVIS_VOICE="en-GB-RyanNeural"   # or any edge-tts voice name
Run `edge-tts --list-voices` (after `pip install edge-tts`) to see options —
"en-GB-RyanNeural" and "en-GB-ThomasNeural" are both calm British male voices.
"""

import asyncio
import os
import platform
import subprocess
import tempfile
import threading

_lock = threading.Lock()

EDGE_VOICE = os.environ.get("JARVIS_VOICE", "en-GB-RyanNeural")
EDGE_RATE = os.environ.get("JARVIS_RATE", "+0%")
EDGE_PITCH = os.environ.get("JARVIS_PITCH", "-5Hz")

_pyttsx_engine = None


def _get_pyttsx_engine():
    global _pyttsx_engine
    if _pyttsx_engine is None:
        import pyttsx3
        _pyttsx_engine = pyttsx3.init()
        _pyttsx_engine.setProperty("rate", 170)
        try:
            for voice in _pyttsx_engine.getProperty("voices"):
                name = (voice.name or "").lower()
                if any(tag in name for tag in ("male", "david", "daniel", "george", "ryan")):
                    _pyttsx_engine.setProperty("voice", voice.id)
                    break
        except Exception:
            pass
    return _pyttsx_engine


def _speak_offline(text: str):
    engine = _get_pyttsx_engine()
    engine.say(text)
    engine.runAndWait()


async def _edge_tts_to_file(text: str, path: str):
    import edge_tts  # pip install edge-tts (free, no API key, needs internet)
    communicate = edge_tts.Communicate(text, voice=EDGE_VOICE, rate=EDGE_RATE, pitch=EDGE_PITCH)
    await communicate.save(path)


def _play_audio_file(path: str) -> bool:
    try:
        import playsound
        playsound.playsound(path)
        return True
    except Exception:
        pass
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.run(["afplay", path], check=True)
        elif system == "Windows":
            os.startfile(path)  # noqa
            # Give Windows Media Player time to open the file before we delete it.
            import time as _t
            _t.sleep(min(6, max(2, len(path))))
        else:
            subprocess.run(["mpg123", "-q", path], check=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def speak(text: str):
    """Thread-safe. Speaks text aloud: tries the free online neural voice
    first, falls back to the fully offline voice on any failure (no
    internet, edge-tts not installed, playback error, etc.)."""
    if not text:
        return
    with _lock:
        try:
            print(f"47: {text}", flush=True)
        except UnicodeEncodeError:
            safe = text.encode("ascii", errors="replace").decode()
            print(f"47: {safe}", flush=True)
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            asyncio.run(_edge_tts_to_file(text, path))
            if not _play_audio_file(path):
                raise RuntimeError("no audio player available")
        except Exception:
            _speak_offline(text)
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
