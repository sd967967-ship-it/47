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
import queue
import subprocess
import tempfile
import threading
import time

_lock = threading.Lock()

EDGE_VOICE = os.environ.get("JARVIS_VOICE", "en-GB-RyanNeural")
EDGE_RATE = os.environ.get("JARVIS_RATE", "+0%")
EDGE_PITCH = os.environ.get("JARVIS_PITCH", "-5Hz")

_pyttsx_engine = None


def clean_for_speech(text: str) -> str:
    """Strip markdown/formatting noise so TTS speaks words, not symbols.
    Dashboard display is untouched — this only feeds the voice engine."""
    import re as _re
    if not text:
        return text
    t = text
    t = _re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", t)   # images -> alt text
    t = _re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)    # links -> text
    t = _re.sub(r"^#{1,6}\s*", "", t, flags=_re.M)     # headers
    t = _re.sub(r"\*\*(.+?)\*\*", r"\1", t)            # bold
    t = _re.sub(r"__(.+?)__", r"\1", t)
    t = _re.sub(r"(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)", r"\1", t)  # italic
    t = t.replace("`", "")                             # code ticks
    t = _re.sub(r"^\s*[-*_]{3,}\s*$", "", t, flags=_re.M)  # rules
    t = _re.sub(r"^\s*\|?[\s:\-|]+\|?\s*$", "", t, flags=_re.M)  # table separators
    t = t.replace("|", ", ")                           # table cells -> pauses
    t = _re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", t, flags=_re.M)  # bullets
    t = _re.sub(r"^\s*>\s?", "", t, flags=_re.M)        # quotes
    t = t.replace("and/or", "and or").replace("w/o", "without").replace("w/", "with")
    t = _re.sub(r"(?<!\S)/(?!\S)", ", ", t)             # lone slashes
    t = t.replace("*", "").replace("_", " ")           # leftover emphasis
    t = _re.sub(r"[ \t]+", " ", t)
    t = _re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


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
    """Non-blocking: prints immediately and queues audio on a single worker,
    so command handling (and the dashboard) never waits on TTS synthesis or
    playback. Items are spoken in order, one at a time."""
    if not text:
        return
    try:
        print(f"47: {text}", flush=True)
    except UnicodeEncodeError:
        safe = text.encode("ascii", errors="replace").decode()
        print(f"47: {safe}", flush=True)
    _ensure_worker()
    try:
        _speak_queue.put_nowait(text[:600])
    except queue.Full:
        pass


_speak_queue: queue.Queue = queue.Queue(maxsize=8)
_worker_started = False
_worker_lock = threading.Lock()


def clear_queue():
    """Drop pending utterances (emergency stop). Never raises."""
    try:
        while True:
            _speak_queue.get_nowait()
            _speak_queue.task_done()
    except queue.Empty:
        pass


def _ensure_worker():
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
    thread = threading.Thread(target=_speak_worker, daemon=True, name="tts-47")
    thread.start()


def _speak_worker():
    while True:
        text = _speak_queue.get()
        try:
            _speak_one(text)
        except Exception:
            pass
        finally:
            _speak_queue.task_done()
        time.sleep(0.4)  # breath between utterances


def _chunks(text: str, limit: int = 140) -> list:
    """Split speech into sentence-ish chunks so the first audio starts
    after ~1 sentence of synthesis instead of the whole reply."""
    import re as _re
    parts = [p.strip() for p in _re.split(r"(?<=[.!?\n])\s+", text.strip()) if p.strip()]
    out, buf = [], ""
    for p in parts:
        if len(buf) + len(p) + 1 <= limit:
            buf = (buf + " " + p).strip()
        else:
            if buf:
                out.append(buf)
            buf = p
    if buf:
        out.append(buf)
    return out or [text]


def _speak_one(text: str):
    """Tries the free online neural voice first, falls back to the fully
    offline voice on any failure (no internet, edge-tts missing, etc.).
    Speaks the cleaned (symbol-free) version; logs show the original.
    Chunked: first sentence plays as soon as it's synthesized."""
    say = clean_for_speech(text)
    if not say:
        return
    try:
        import playsound  # noqa  (blocking playback -> serial chunks)
        chunked = True
    except Exception:
        chunked = False
    with _lock:
        if chunked:
            try:
                for piece in _chunks(say):
                    fd, path = tempfile.mkstemp(suffix=".mp3")
                    os.close(fd)
                    try:
                        asyncio.run(_edge_tts_to_file(piece, path))
                        playsound.playsound(path)
                    finally:
                        try:
                            os.remove(path)
                        except OSError:
                            pass
                return
            except Exception:
                pass
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            asyncio.run(_edge_tts_to_file(say, path))
            if not _play_audio_file(path):
                raise RuntimeError("no audio player available")
        except Exception:
            _speak_offline(say)
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
