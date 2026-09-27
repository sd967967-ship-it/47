"""
47 - Personal AI Assistant (free/local by default, upgradeable)
--------------------------------------------------------------------
Pipeline: Mic OR typed text -> Brain (local LLM or Groq) -> Voice + 3D dashboard.
Persistent memory across restarts. Ambient system-monitoring HUD.
Data it generates is pushed to a live 3D dashboard.

SETUP (free path):
1. Install Ollama: https://ollama.com  then:  ollama pull llama3
2. pip install -r requirements.txt
3. python main.py
   -> prints a dashboard URL that already includes your access token,
      and opens it in a browser automatically. Use THAT printed URL —
      http://localhost:5000 with no token will be refused. See the
      "Dashboard access control" section below for why.

OPTIONAL — close the intelligence gap, still 100% free:
    export GROQ_API_KEY=gsk_...
    export ASSISTANT_BRAIN=groq
Groq hosts open-source models (Llama 3.3 70B) for free — no credit card,
no cost, and it's dramatically sharper than a small local model, with
very low latency. Get a free key at https://console.groq.com
Everything else (memory, actions, dashboard) stays exactly the same.

VOICE: see tts_jarvis.py for what "JARVIS voice" means here — a free,
legal, British neural voice styled in that direction; not a clone of the
actual copyrighted movie character voice, which isn't something any
legitimate tool can reproduce. See also the voice-privacy note in
listen() below and in README.md — the free recognizer streams audio to
Google, not just after the wake word.

SECURITY — dashboard access control:
This app's dashboard can, on request, run arbitrary shell commands
(shell.py) — including elevated ones. Earlier versions bound the web
server to 0.0.0.0 (every network interface) with no login of any kind,
which meant anyone on the same Wi-Fi/LAN, or anyone who could reach this
machine's port over the internet (port-forwarding, a misconfigured
firewall, a cloud VM with a public IP), could open the dashboard and
issue shell commands with zero authentication. That's fixed two ways:
  1. Binds to 127.0.0.1 (this machine only) by default. Override with
     DASHBOARD_HOST=0.0.0.0 only if you specifically want LAN access —
     doing so prints a loud warning, because you are then relying
     entirely on fix #2.
  2. A random access token, generated on first run and cached in
     .47_dashboard_token next to this file (override with
     DASHBOARD_TOKEN=... to pin it yourself). Both the page load (GET /)
     and every socket connection must present it as ?token=... or they're
     rejected. The printed startup URL already includes it.
This is a shared-secret, not a real multi-user auth system — treat the
token file the way you'd treat a password, and regenerate it (delete the
file) if you think it leaked. It's sized for "keep strangers on the LAN
out of my personal assistant," not for "safe to expose to the internet."
"""

import os
import re
import secrets
import signal
import sys
import time
import json
import threading
import webbrowser

import requests
import speech_recognition as sr
from flask import Flask, render_template, request, abort
from flask_socketio import SocketIO

import actions
import memory
import ambient
import vision
import mcp_client
import time_parse
import visual3d
import tts_jarvis
import shell
from net_utils import request_with_retry

# ---------- Setup ----------
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins=["http://127.0.0.1:5000",
                                               "http://localhost:5000"])

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")  # fast default; was 120b (retired llama replacement) — 120b reasoned slowly and burned free-tier rate limits. Set GROQ_MODEL=openai/gpt-oss-120b for max smarts.

# ---------- Dashboard access token ----------
_TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".47_dashboard_token")


def _load_or_create_token() -> str:
    env_token = os.environ.get("DASHBOARD_TOKEN")
    if env_token:
        return env_token
    try:
        if os.path.exists(_TOKEN_PATH):
            with open(_TOKEN_PATH, "r") as f:
                existing = f.read().strip()
                if existing:
                    return existing
        token = secrets.token_urlsafe(24)
        with open(_TOKEN_PATH, "w") as f:
            f.write(token)
        try:
            os.chmod(_TOKEN_PATH, 0o600)  # best-effort; no-op on some platforms
        except OSError:
            pass
        return token
    except OSError:
        # Filesystem is read-only or unwritable — fall back to an
        # in-memory-only token rather than crashing. It won't survive a
        # restart, which is annoying but far safer than no auth at all.
        return secrets.token_urlsafe(24)


DASHBOARD_TOKEN = _load_or_create_token()
DASHBOARD_HOST = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
DASHBOARD_PORT = int(os.environ.get("DASHBOARD_PORT", "5000"))
_authed_sids = set()
_authed_lock = threading.Lock()

# HARDWARE NOTE (i5 11th gen + Iris Xe, no discrete GPU/VRAM): Iris Xe gets
# no benefit at all from an LLM — it has no CUDA/ROCm inference path, so a
# "local" model runs purely on the 4 CPU cores. An 8B model (the old default,
# "llama3") is genuinely rough on that CPU: multi-second replies, fans at
# full tilt, everything else on the laptop sluggish while it thinks. So:
#   - default to Groq automatically whenever a free API key is present
#     (inference happens in Groq's cloud — zero load on your CPU/iGPU, and
#     it's also just a smarter model). This is the "don't compromise" path.
#   - if you explicitly want fully offline, this now defaults to a small
#     quantized model (llama3.2:3b) that a 4-core CPU can actually run at a
#     readable pace, instead of 8B. Force one or the other with:
#       export ASSISTANT_BRAIN=groq     # or "ollama"
#       export OLLAMA_MODEL=phi3.5      # any other small local model
BRAIN = os.environ.get("ASSISTANT_BRAIN") or ("groq" if GROQ_API_KEY else "ollama")

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
# Tell Ollama how many of the CPU's threads it's allowed to use. A typical
# 11th-gen i5 (e.g. 1135G7) is 4 cores / 8 threads — leave one or two free
# so the voice loop, Flask, and the rest of 47 don't stutter while it thinks.
OLLAMA_NUM_THREAD = int(os.environ.get("OLLAMA_NUM_THREAD", max(2, (os.cpu_count() or 4) - 2)))

SYSTEM_PROMPT = (
    "You are 47, a capable personal AI assistant. "
    "Default to a 1-3 sentence spoken reply AND a thorough dashboard answer "
    "when the user asks for detail, explanations, comparisons, or how-to — "
    "never truncate to fit brevity; be complete and specific with numbers, "
    "steps, and names. "
    "You have persistent memory of past conversations, known facts about the "
    "user, and their open tasks — use them naturally when relevant. When the "
    "user mentions a task (past or present), proactively suggest a faster or "
    "smarter way to get it done if you can think of one, without being asked. "
    "If the user's request involves data that could be shown visually "
    "(comparisons, timelines, structures, numbers), say so briefly and note "
    "that you're sending it to the dashboard. "
    "If an MCP tool is available and would make the answer fresher or more "
    f"accurate, call it. Today's date is {time.strftime('%Y-%m-%d')}."
)

GROQ_MAX_TOKENS = int(os.environ.get("GROQ_MAX_TOKENS", "1000"))
GROQ_TEMPERATURE = float(os.environ.get("GROQ_TEMPERATURE", "0.4"))


def _needs_tools(user_text: str) -> bool:
    """Fast-path gate (JARVIS-6 'first-partial routing' idea, cheap version):
    casual chat ('hi', 'thanks', small talk) never needs MCP tools, so skip
    them entirely — one fast round instead of up to 3 reasoning + tool rounds.
    Tools only attach for fetch/search/run/open/browse/weather-type requests."""
    lowered = user_text.lower()
    if actions.find_url(user_text):
        return True
    hints = ("fetch", "search", "weather", "browse", "automate", "open ",
             "run command", "execute", "terminal", "file", "folder", "disk",
             "browse", "click", "screenshot", "turn on", "turn off", "toggle")
    if any(h in lowered for h in hints):
        return True
    return len(user_text) > 160  # long/complex prompts may benefit from tools

# Context id used for the always-on voice loop's pending-confirmation state
# (see shell.py) — there's only ever one microphone, so a fixed key is fine.
VOICE_CONTEXT = "voice"


# ---------- Core brain ----------
def ask_ollama(user_text: str, context: str, history=None) -> str:
    hist = ""
    if history:
        hist = "\n".join(
            f"{'User' if r == 'user' else '47'}: {c[:800]}"
            for r, c in history[-6:]
        )
    prompt = f"{SYSTEM_PROMPT}\n\n{context}\n\n{hist}\nUser: {user_text}\n47:"
    try:
        resp = request_with_retry(
            "POST", OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                # Cap context and pin thread count — keeps RAM/CPU use
                # predictable on a 4-core laptop instead of Ollama grabbing
                # everything it can.
                "options": {"num_thread": OLLAMA_NUM_THREAD, "num_ctx": 4096,
                            "keep_alive": "30m"},
            },
            timeout=90,
            max_attempts=2,
            base_delay=0.3,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        return f"I couldn't reach my local brain (Ollama). Is it running? Error: {e}"


def ask_groq(user_text: str, context: str, history) -> str:
    """Agentic loop: the model can call MCP tools (e.g. fetch a URL) mid-answer,
    see the result, and keep reasoning — up to a few rounds — before replying."""
    try:
        messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{context}"}]
        for role, content in history:
            messages.append({"role": "user" if role == "user" else "assistant",
                             "content": content[:1200]})
        messages.append({"role": "user", "content": user_text})

        tools = mcp_client.list_all_tools() if _needs_tools(user_text) else []

        for _ in range(2):  # cap tool-call rounds so a bad loop can't run forever
            body = {"model": GROQ_MODEL, "messages": messages,
                    "max_tokens": GROQ_MAX_TOKENS if tools else 400,
                    "temperature": GROQ_TEMPERATURE,
                    "reasoning_effort": os.environ.get("GROQ_REASONING_EFFORT", "low")}
            if tools:
                body["tools"] = tools
                body["tool_choice"] = "auto"

            resp = request_with_retry(
                "POST", "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=45,
                max_attempts=2,
                base_delay=0.4,
            )
            if resp.status_code == 429:
                return ("Groq's free tier is rate-limiting me right now — "
                        "falling back to the local brain.")
            resp.raise_for_status()
            data = resp.json()
            msg = data["choices"][0]["message"]

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                return (msg.get("content") or "").strip()

            messages.append(msg)
            for call in tool_calls:
                name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                print(f"[MCP] calling {name} with {args}")
                result = mcp_client.call_tool(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result[:4000],  # keep context manageable
                })

        return "I tried a few tool calls but couldn't finish — try rephrasing that."
    except Exception as e:
        return f"I couldn't reach Groq. Check GROQ_API_KEY and your connection. Error: {e}"


def _is_groq_failure(reply: str) -> bool:
    return reply.startswith("I couldn't reach Groq") or "rate-limit" in reply[:80]


def _is_ollama_failure(reply: str) -> bool:
    return reply.startswith("I couldn't reach my local brain")


def ask_brain(user_text: str) -> str:
    context = memory.facts_as_context() + "\n\n" + memory.tasks_as_context()
    # Cap an unbounded task list so one long-lived install can't bloat every turn.
    if len(context) > 6000:
        context = context[:6000]
    history = [(r, c[:1200]) for r, c in memory.recent_history(limit=20)]

    # Dual-brain: try preferred first, auto-fallback to the other.
    # Set ASSISTANT_BRAIN=groq (default when GROQ_API_KEY is set) or
    # ASSISTANT_BRAIN=ollama to choose the primary.
    primary = BRAIN if BRAIN in ("groq", "ollama") else ("groq" if GROQ_API_KEY else "ollama")
    reply = ""
    if primary == "groq" and GROQ_API_KEY:
        reply = ask_groq(user_text, context, history)
        if _is_groq_failure(reply):
            print(f"[brain] Groq failed ({reply[:80]}...), falling back to Ollama.")
            ollama_reply = ask_ollama(user_text, context, history)
            if not _is_ollama_failure(ollama_reply):
                reply = f"(Groq unavailable, answered locally) {ollama_reply}"
    else:
        reply = ask_ollama(user_text, context, history)
        if _is_ollama_failure(reply) and GROQ_API_KEY:
            print(f"[brain] Ollama failed, falling back to Groq.")
            groq_reply = ask_groq(user_text, context, history)
            if not _is_groq_failure(groq_reply):
                reply = groq_reply

    memory.log_turn("user", user_text)
    memory.log_turn("assistant", reply)
    return reply


def speak(text: str):
    tts_jarvis.speak(text)


# ---------- Voice input ----------
# PRIVACY NOTE (was previously undocumented outside this comment — see
# README.md's Privacy section for the user-facing version): sr.recognize_
# google() is a free *cloud* API. Every listen() call below streams that
# chunk of ambient audio to Google for transcription — not just audio after
# the wake word, because the wake word itself is only detected by
# inspecting the transcription that comes back. There is no on-device
# wake-word gate in the free path. If that's not acceptable for your
# situation, set VOICE_RECOGNIZER=sphinx below for a fully offline
# (lower-accuracy) alternative, or don't run the voice loop at all and use
# the dashboard's typed-input box instead.
VOICE_RECOGNIZER = os.environ.get("VOICE_RECOGNIZER", "google").lower()
_sphinx_warned = False


def listen() -> str:
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source)
    global _sphinx_warned
    try:
        if VOICE_RECOGNIZER == "sphinx":
            try:
                text = r.recognize_sphinx(audio)
            except Exception as e:
                if not _sphinx_warned:
                    print(f"[voice] pocketsphinx unavailable ({e}); install "
                          f"pocketsphinx for offline recognition, or unset "
                          f"VOICE_RECOGNIZER to use the free Google API.")
                    _sphinx_warned = True
                return ""
        elif VOICE_RECOGNIZER == "whisper":
            # Local Whisper via faster-whisper when installed (offline,
            # low-hallucination like the JARVIS-6/Moonshine pattern).
            try:
                from faster_whisper import WhisperModel
                import numpy as np
                raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                pcm = (np.frombuffer(raw, dtype=np.int16).astype("float32") / 32768.0)
                model = listen._whisper_model if hasattr(listen, "_whisper_model") else None
                if model is None:
                    model = WhisperModel(os.environ.get("WHISPER_MODEL", "tiny"),
                                         device="cpu", compute_type="int8")
                    listen._whisper_model = model
                segments, _ = model.transcribe(pcm, beam_size=1)
                text = " ".join(s.text for s in segments).strip()
            except Exception as e:
                if not _sphinx_warned:
                    print(f"[voice] whisper unavailable ({e}); pip install "
                          f"faster-whisper or use VOICE_RECOGNIZER=sphinx/google.")
                    _sphinx_warned = True
                return ""
        else:
            text = r.recognize_google(audio)
        print(f"You: {text}")
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("Speech recognition service is unavailable right now.")
        return ""


# ---------- Dashboard push ----------
def push_to_dashboard(kind: str, payload: dict):
    socketio.emit("data_47", {"kind": kind, "payload": payload})


def maybe_show_3d(text: str):
    """Always-3D policy for 47: named categories render their parametric
    scene; ask/show/model/render questions fall back to a labeled generic
    object so the dashboard never stays flat when asked to *see* something.
    Text answers always go to the 2D panel alongside — never 3D-only."""
    category = visual3d.classify_or_generic(text)
    kind, payload = visual3d.build_payload(category, text)
    if kind:
        push_to_dashboard(kind, payload)


# ---------- Command router ----------
# BUGFIX (noisy passive detection): the old version matched a trigger like
# "i need to " *anywhere* in the utterance as a plain substring, so e.g.
# "she said i need to leave early" (someone else's sentence, overheard,
# quoted) logged a task, and any trigger that happened to appear mid-word
# or mid-clause got picked up too. Triggers now only fire at the start of
# the utterance or right after sentence punctuation (. , ; ! ? or a
# clause-connecting "and"/"but"), which is a much better proxy for "the
# user is actually stating a first-person intention right now" than a bare
# substring search. Still heuristic, still not perfect — just meaningfully
# less noisy.
_SENTENCE_BOUNDARY_RE = re.compile(r"(?:^|[.!?;]\s*|\band\s+|\bbut\s+)", re.IGNORECASE)
TASK_TRIGGERS = ["i need to ", "i have to ", "i should ", "i plan to ", "i'm going to ", "i am going to "]


def passive_scan(text: str):
    """Runs on everything 47 overhears, even without the wake word — but never
    speaks. Only does quiet background logging (task auto-detection)."""
    lowered = text.lower()
    boundaries = {m.end() for m in _SENTENCE_BOUNDARY_RE.finditer(lowered)}
    for trigger in TASK_TRIGGERS:
        idx = lowered.find(trigger)
        if idx != -1 and idx in boundaries:
            fragment = text[idx + len(trigger):].strip(" .,")
            if fragment:
                memory.add_task(fragment, source="auto_detected")
            break


_ELEVATE_PHRASES_RE = re.compile(
    r"\bas\s+(?:an?\s+)?administrator\b|\bas\s+admin\b|\bwith\s+admin(?:istrator)?\s+"
    r"(?:rights|permissions|privileges)\b|\belevated\b|\busing\s+admin\s+rights\b",
    re.IGNORECASE,
)

RUN_TRIGGERS = [
    "run command ", "run this command ", "execute command ", "execute ",
    "run in the terminal ", "run in terminal ", "in the terminal run ",
    "type in the terminal ", "terminal command ",
]

FETCH_TRIGGERS = ["fetch ", "pull up ", "get me the data from ", "read this page "]


def _extract_after_trigger(text: str, lowered: str, trigger: str) -> str:
    """Same slice on both, so casing/paths in the original text survive."""
    return text[len(trigger):].strip() if lowered.startswith(trigger) else text.strip()


def handle_command(text: str, context_id: str = VOICE_CONTEXT):
    lowered = text.lower()
    if not text:
        return
    # ---- Confirmation gate for anything shell.py flagged as destructive.
    # Must be checked before anything else so "confirm" isn't swallowed by
    # a different branch, and so a pending destructive command can't be
    # silently replaced by whatever's said next. Keyed by context_id (see
    # shell.py) so one browser tab's staged command can't be confirmed or
    # clobbered by a different tab or the voice loop.
    if shell.has_pending(context_id):
        if lowered.strip() in ("confirm", "yes confirm", "confirm it", "yes run it", "do it"):
            command, elevate = shell.pop_pending(context_id)
            speak("Confirmed — running it now." if not elevate else "Confirmed — elevating and running it now.")
            output = shell.run(command, elevate=elevate)
            speak(output[:280])
            push_to_dashboard("text", {"content": output})
            return
        else:
            shell.pop_pending(context_id)  # anything else cancels it rather than leaving it live
            speak("Cancelled that command since you didn't confirm it.")
            # fall through — still process whatever they actually said

    # still run passive task detection even on addressed commands
    passive_scan(text)

    # BUGFIX/FEATURE: fire the 3D-object visualizer on every addressed
    # command, not just the generic-chat fallback, so "hi 47, what does a
    # wrench look like" gets a visual even though it doesn't match any of
    # the hardcoded command branches below.
    maybe_show_3d(text)

    # ---- Multi-step planner (bbjarvis planner heuristic, 47's own runner):
    # "search X then open Y" runs as ordered steps through this same router,
    # each keeping its confirm gates. Only fires on explicit sequence words.
    import planner as _planner
    if _planner.needs_plan(text):
        steps = _planner.split_steps(text)
        speak(f"That's {len(steps)} steps. Working through them in order.")
        push_to_dashboard("text", {"content": "Plan:\n" + "\n".join(
            f"{i + 1}. {s}" for i, s in enumerate(steps))})
        for i, step in enumerate(steps):
            push_to_dashboard("text", {"content": f"Step {i + 1}/{len(steps)}: {step}"})
            handle_command(step, context_id=context_id)
            if shell.has_pending(context_id):
                speak("Paused — that step needs a 'confirm' before I continue.")
                return
        speak("All steps done.")
        return

    # ---- Task review/cleanup (fix for "noisy passive detection with no
    # easy way to review/delete except touching the sqlite file directly").
    if lowered.startswith("delete task ") or lowered.startswith("remove task "):
        fragment = text.split(" ", 2)[-1].strip()
        deleted = memory.delete_task_matching(fragment)
        speak(f"Deleted '{deleted}'." if deleted else "I couldn't find a matching task to delete.")
        return

    if "clear auto" in lowered and "task" in lowered:
        removed = memory.clear_auto_detected_tasks()
        speak(f"Cleared {removed} auto-detected task{'s' if removed != 1 else ''}."
              if removed else "There weren't any auto-detected tasks to clear.")
        return

    # ---- Real command-prompt access (see shell.py for the elevation and
    # destructive-command-confirmation design). Handles things like:
    #   "run command ipconfig /all"
    #   "execute git status as administrator"
    if any(lowered.startswith(t) for t in RUN_TRIGGERS):
        trigger = next(t for t in RUN_TRIGGERS if lowered.startswith(t))
        raw_command = _extract_after_trigger(text, lowered, trigger)
        elevate = bool(_ELEVATE_PHRASES_RE.search(raw_command))
        command = _ELEVATE_PHRASES_RE.sub("", raw_command).strip(" .,")
        if not command:
            speak("What command do you want me to run?")
            return
        if shell.needs_confirmation(command):
            shell.stage_for_confirmation(context_id, command, elevate)
            speak(f"That looks like a destructive command: {command}. Say 'confirm' if you want me to run it anyway.")
            return
        speak(("Elevating and running it now." if elevate else "Running it now."))
        output = shell.run(command, elevate=elevate)
        speak(output[:280])
        push_to_dashboard("text", {"content": f"$ {command}\n\n{output}"})
        return

    # ---- Fetch real-time data from any URL (works with either brain,
    # unlike the MCP fetch tool which only runs on the Groq path). Reads
    # the page, then hands the text to the brain to summarize on request.
    url_in_text = actions.find_url(text)
    if url_in_text and (any(lowered.startswith(t) for t in FETCH_TRIGGERS) or "fetch" in lowered):
        speak(f"Fetching that page now.")
        page_text = actions.fetch_url(url_in_text)
        summary_prompt = f"Summarize this page in 2-3 sentences:\n\n{page_text[:3000]}"
        reply = ask_brain(summary_prompt)
        speak(reply)
        push_to_dashboard("text", {"content": reply})
        return

    if lowered.startswith("weather in ") or lowered.startswith("what's the weather in ") or \
       lowered.startswith("whats the weather in ") or lowered.startswith("weather for "):
        place = lowered.split(" in ", 1)[-1].strip() if " in " in lowered else lowered.split("for ", 1)[-1].strip()
        report = actions.get_weather(place)
        speak(report)
        push_to_dashboard("text", {"content": report})
        return

    if "what's on my screen" in lowered or "whats on my screen" in lowered or "look at my screen" in lowered:
        speak("Let me take a look.")
        description = vision.describe_screen(GROQ_API_KEY)
        speak(description)
        push_to_dashboard("text", {"content": description})
        return

    if "what do you see" in lowered or "look at me" in lowered or "camera" in lowered:
        speak("Checking the camera now.")
        description = vision.describe_camera(GROQ_API_KEY)
        speak(description)
        push_to_dashboard("text", {"content": description})
        return

    if lowered.startswith("remind me to ") or lowered.startswith("remind me in") or "remind me to" in lowered:
        # BUGFIX: previously, "remind me in 10 minutes to call the bank" fell
        # through to using the *entire* raw sentence as the task description
        # whenever it didn't literally contain "remind me to". Now the whole
        # "remind me [in ...] [to]" prefix is stripped consistently first.
        raw = time_parse.strip_reminder_prefix(text)
        due_at = time_parse.parse_due(raw)
        description = time_parse.strip_due_phrase(raw)
        memory.add_task(description, due_at=due_at, source="explicit_reminder")
        if due_at:
            speak(f"Got it, I'll remind you to {description}.")
        else:
            speak(f"Added to your tasks: {description}. Just say 'what are my tasks' anytime.")
        return

    if "what are my tasks" in lowered or "what do i have to do" in lowered or "what's on my plate" in lowered:
        tasks = memory.list_open_tasks()
        if not tasks:
            speak("You have no open tasks right now.")
        else:
            names = [t[1] for t in tasks[:6]]
            speak(f"You have {len(tasks)} open tasks: " + "; ".join(names) + ".")
            push_to_dashboard("bars", {
                "labels": [n[:18] for n in names],
                "values": [1] * len(names),
            })
        return

    if lowered.startswith("done with ") or lowered.startswith("finished ") or lowered.startswith("i completed "):
        # BUGFIX: the old code used a bare `lowered.split(" ", 1)[-1]` for the
        # "i completed X" branch, which kept the word "completed" glued onto
        # the fragment (matching "i completed X" against "completed X" instead
        # of "X"). Now every prefix is stripped explicitly.
        for prefix in ("done with ", "finished ", "i completed "):
            if lowered.startswith(prefix):
                fragment = lowered[len(prefix):].strip()
                break
        completed = memory.complete_task_matching(fragment)
        if completed:
            speak(f"Nice — marked '{completed}' as done.")
        else:
            speak("I couldn't find a matching open task.")
        return

    # Passive task detection also runs here via passive_scan() above.

    if lowered.startswith("remember that "):
        fact_sentence = text[len("remember that "):]
        key, value = memory.derive_key_and_value(fact_sentence)
        memory.remember_fact(key, value)
        speak(f"Got it, I'll remember that {value}.")
        return

    if lowered.startswith("open ") or " open " in lowered:
        target = lowered.split("open ", 1)[1]
        speak(actions.open_app_or_site(target))
        return

    if lowered.startswith("find file") or lowered.startswith("search for a file"):
        term = lowered.split("file", 1)[1].strip()
        matches = actions.find_files(term)
        if matches:
            speak(f"I found {len(matches)} matching files. Showing them on the dashboard.")
            push_to_dashboard("bars", {
                "labels": [m.split("/")[-1][:18] for m in matches[:8]],
                "values": [1] * len(matches[:8]),
            })
        else:
            speak(f"No files matching {term} found.")
        return

    if lowered.startswith("read file ") or lowered.startswith("show file "):
        target = text.split(" ", 2)[-1].strip()
        content = actions.read_file(target)
        speak(content[:280])
        push_to_dashboard("text", {"content": content[:4000]})
        return

    if lowered.startswith("list files") or lowered.startswith("list folder"):
        target = text.split(" ", 2)[-1].strip() if len(text.split()) > 2 else ""
        if target.lower() in ("files", "folder", "in"):
            target = ""
        content = actions.list_dir(target)
        speak(content[:280])
        push_to_dashboard("text", {"content": content[:4000]})
        return

    if lowered.startswith("open folder") or lowered.startswith("open explorer"):
        target = text.split(" ", 2)[-1].strip()
        if target.lower() in ("folder", "explorer"):
            target = ""
        speak(actions.open_folder(target))
        return

    if "list apps" in lowered or "running apps" in lowered:
        report = actions.list_apps()
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    if "list windows" in lowered or "open windows" in lowered:
        report = actions.list_windows()
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    if "disk" in lowered and ("space" in lowered or "details" in lowered or "drives" in lowered):
        import ambient as _ambient
        drives = _ambient.disk_details()
        if not drives:
            speak("I couldn't read drive details.")
        else:
            lines = [f"{d['mount']}: {d['free_gb']}GB free of {d['total_gb']}GB ({d['pct']}%)"
                     for d in drives]
            report = "Drives:\n" + "\n".join(lines)
            speak(report[:280])
            push_to_dashboard("text", {"content": report})
        return

    if "system status" in lowered or "pc status" in lowered or "computer status" in lowered:
        import ambient as _ambient
        snap = _ambient.get_system_snapshot()
        cores = len(snap.get("cpu_per_core") or [])
        report = (f"CPU {snap['cpu_percent']}% across {cores} cores, "
                  f"RAM {snap['ram_percent']}%, disk {snap['disk_percent']}%, "
                  f"{snap['process_count']} processes.")
        if snap.get("uptime_s"):
            report += f" Uptime {snap['uptime_s'] // 3600}h."
        speak(report)
        push_to_dashboard("text", {"content": report})
        push_to_dashboard("vitals", snap)
        return

    if "volume" in lowered:
        digits = "".join(ch for ch in lowered if ch.isdigit())
        level = int(digits) if digits else 50
        speak(actions.set_volume(level))
        return

    if lowered.startswith("search") and "for" in lowered:
        query = lowered.split("for", 1)[1].strip()
        results = actions.web_search(query)
        speak(f"Here's what I found on {query}.")
        push_to_dashboard("bars", {
            "labels": [r["title"][:20] for r in results[:5]],
            "values": [1] * len(results[:5]),
        })
        return

    if "send email" in lowered or "write an email" in lowered:
        speak("Email needs the Gmail API setup — see actions.py for steps.")
        return

    conv = re.match(r".*?convert\s+([\d.]+)\s+([a-z$]+)\s+to\s+([a-z$]+)", lowered)
    if conv:
        import publicdata as _pd
        report = _pd.convert_currency(float(conv.group(1)), conv.group(2), conv.group(3))
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    crypto = re.match(r".*?(?:price of|how much is)\s+([a-z ]+?)[?.!]*$", lowered) or \
        re.match(r".*?\b(bitcoin|btc|ethereum|eth|solana|sol|dogecoin|doge|ripple|xrp|bnb)\b.*?(price|worth|rate)", lowered)
    if crypto:
        import publicdata as _pd
        asset = crypto.group(1).strip()
        report = _pd.crypto_price(asset)
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    if "holiday" in lowered:
        import publicdata as _pd
        place = lowered.split(" in ", 1)[-1].strip(" ?.") if " in " in lowered else "US"
        report = _pd.next_holiday(place)
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    if lowered.startswith("country info "):
        import publicdata as _pd
        report = _pd.country_info(text[len("country info "):].strip())
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    if lowered.startswith("research "):
        topic = text[len("research "):].strip() or "general knowledge"
        import prompts as _prompts
        guide = _prompts.research_guide()
        results = actions.web_search(topic)
        brief = "\n".join(f"- {r['title']} ({r['url']})" for r in results[:5])
        summary_prompt = (f"Research this topic and answer with these sections:\n{guide}\n\n"
                          f"Topic: {topic}\n\nWeb results:\n{brief}")
        reply = ask_brain(summary_prompt)
        speak(reply[:280])
        push_to_dashboard("text", {"content": reply})
        return

    if "lock" in lowered and ("pc" in lowered or "computer" in lowered or "workstation" in lowered):
        speak(actions.lock_workstation())
        return

    if "recent files" in lowered or "recent downloads" in lowered:
        report = actions.recent_files()
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    if "top processes" in lowered or "heaviest processes" in lowered:
        report = actions.top_processes()
        speak(report[:280])
        push_to_dashboard("text", {"content": report})
        return

    if "audit log" in lowered or "show audit" in lowered:
        import audit as _audit
        entries = _audit.read(limit=20)
        if not entries:
            speak("The audit log is empty.")
        else:
            import time as _t
            lines = [f"{_t.strftime('%m-%d %H:%M', _t.localtime(e['ts']))} {e['event']}"
                     for e in entries[-10:]]
            report = "Recent audit entries:\n" + "\n".join(lines)
            speak(report[:280])
            push_to_dashboard("text", {"content": report})
        return

    if lowered.startswith("browse ") or lowered.startswith("automate page "):
        url = actions.find_url(text) or text.split(" ", 1)[-1].strip()
        try:
            import browser as _browser
            result = _browser.open_page(url)
        except Exception as e:
            result = f"Browser automation needs 'pip install playwright': {e}"
        speak(result[:280])
        push_to_dashboard("text", {"content": result[:4000]})
        return

    if lowered.startswith("move mouse"):
        import re as _re
        nums = _re.findall(r"-?\d+", text)
        if len(nums) >= 2:
            import desktop as _desktop
            speak(_desktop.move_mouse(nums[0], nums[1]))
        else:
            speak("Tell me X and Y, like 'move mouse to 500 300'.")
        return

    if lowered.startswith("click"):
        import desktop as _desktop
        btn = "right" if "right" in lowered else "left"
        speak(_desktop.click(btn))
        return

    if lowered.startswith("type "):
        import desktop as _desktop
        speak(_desktop.type_text(text[len("type "):]))
        return

    if "screenshot" in lowered and ("take" in lowered or "capture" in lowered):
        import desktop as _desktop
        out = _desktop.screenshot_region()
        speak(f"Saved screenshot to {out}.")
        push_to_dashboard("text", {"content": f"Screenshot: {out}"})
        return

    if lowered.startswith("turn on ") or lowered.startswith("turn off ") or lowered.startswith("toggle "):
        import home as _home
        if lowered.startswith("toggle "):
            res = _home.toggle(text[len("toggle "):].strip())
        elif lowered.startswith("turn on "):
            res = _home.turn_on(text[len("turn on "):].strip())
        else:
            res = _home.turn_off(text[len("turn off "):].strip())
        speak(res)
        return

    push_to_dashboard("text", {"content": "47 is thinking…"})
    reply = ask_brain(text)
    speak(reply[:280])
    push_to_dashboard("text", {"content": reply})


# ---------- Background-thread supervision ----------
# FIX for "no crash supervisor for the daemon threads": previously, any
# unhandled exception inside voice_loop/start_ambient/etc. just silently
# killed that one daemon thread — the process kept running, looking
# healthy, with (say) the ambient HUD frozen forever and no log louder
# than a stack trace scrolling past. supervise() restarts the target on
# any exception, with backoff, and gives up (loudly) only if it's crashing
# in a tight loop, which is a real bug worth surfacing rather than papering
# over.
def supervise(name: str, target, *args, **kwargs):
    def _wrapper():
        attempt = 0
        while True:
            try:
                attempt += 1
                target(*args, **kwargs)
                # A target that returns normally (e.g. voice_loop bailing out
                # because there's no mic) is intentional — don't restart it.
                print(f"[supervisor] '{name}' exited normally; not restarting.")
                return
            except Exception as e:
                delay = min(30, 2 ** min(attempt, 5))
                print(f"[supervisor] '{name}' crashed (attempt {attempt}): {e}. "
                      f"Restarting in {delay}s.")
                time.sleep(delay)
    thread = threading.Thread(target=_wrapper, daemon=True, name=name)
    thread.start()
    return thread


# ---------- Voice loop ----------
WAKE_WORD = os.environ.get("WAKE_WORD", "hi 47").lower()


def voice_loop():
    # BUGFIX: sr.Microphone() raises OSError immediately if no mic is
    # present/PyAudio isn't set up, which used to crash the whole process
    # since this ran in a daemon thread with no guard. Now it degrades
    # gracefully to "typed input only" instead of taking the app down.
    try:
        sr.Microphone()
    except Exception as e:
        print(f"[voice] No usable microphone ({e}). Voice input disabled — "
              f"use the text box on the dashboard instead.")
        return

    brain_label = "Groq (gpt-oss-20b)" if (BRAIN == "groq" and GROQ_API_KEY) else "local model"
    speak(f"47 online, running on {brain_label}. Say '{WAKE_WORD}' to talk to me.")
    while True:
        heard = listen()
        if not heard:
            continue
        lowered_heard = heard.lower()
        if WAKE_WORD in lowered_heard:
            command = lowered_heard.replace(WAKE_WORD, "", 1).strip(" ,.")
            if command:
                handle_command(command, context_id=VOICE_CONTEXT)
            else:
                speak("Yes?")
        else:
            # Not addressed directly — stay quiet, but keep passive task detection running
            passive_scan(heard)


# ---------- Ambient loop ----------
def ambient_alert(message: str):
    speak(message)


def start_ambient():
    ambient.ambient_loop(push_to_dashboard, interval_seconds=5, alert_fn=ambient_alert)


def start_window_tracking():
    """Lightweight always-on awareness of what app/window is active — no images captured."""
    last_title = None
    while True:
        title = vision.get_active_window_title()
        if title != last_title:
            memory.remember_fact("last_active_window", title)
            push_to_dashboard("window", {"title": title})
            last_title = title
        time.sleep(3)


def start_task_reminders():
    """Checks every 15s for tasks whose scheduled time has arrived and speaks them up."""
    while True:
        due = memory.due_unreminded_tasks(time.time())
        for task_id, description in due:
            speak(f"Reminder: {description}")
            memory.mark_reminded(task_id)
        time.sleep(15)


# ---------- Flask routes ----------
def _check_token(supplied: str) -> bool:
    return bool(supplied) and secrets.compare_digest(supplied, DASHBOARD_TOKEN)


@app.route("/")
def dashboard():
    # SECURITY FIX: this used to render unconditionally for anyone who could
    # reach the port. Now it 403s without the correct ?token=... — see the
    # module docstring's "Dashboard access control" section.
    if not _check_token(request.args.get("token", "")):
        abort(403, description="Missing or invalid dashboard token. Use the URL "
                                "printed in the console when 47 started.")
    return render_template("dashboard.html")


# FEATURE: typed data-entry channel. You can type anything the dashboard's
# text box sends here — a command ("open github"), a fact to remember
# ("remember that my flight is at 6pm"), or just a question — and 47 routes
# it through the exact same handle_command() pipeline as a spoken "hi 47"
# command, so it speaks the reply back and can act on it. Runs in a
# background thread so a slow brain/TTS call never blocks the socket.
@socketio.on("connect")
def on_connect():
    # SECURITY FIX: socket connections used to be accepted from anyone,
    # independent of the page-load check above (a raw socket client could
    # connect directly, bypassing GET /). Returning False here rejects the
    # handshake outright — the client's connect_error handler (dashboard.html)
    # is what shows the "connection rejected" message.
    token = request.args.get("token", "")
    if not _check_token(token):
        print(f"[security] Rejected unauthenticated socket connection from {request.remote_addr}.")
        return False
    with _authed_lock:
        _authed_sids.add(request.sid)
    return True


@socketio.on("disconnect")
def on_disconnect():
    with _authed_lock:
        _authed_sids.discard(request.sid)


@socketio.on("user_text_command")
def on_user_text_command(data):
    # Defense in depth: even though on_connect() already gates the socket
    # handshake, double-check the sid is still in the authenticated set
    # before acting on anything it sends.
    with _authed_lock:
        authed = request.sid in _authed_sids
    if not authed:
        return
    text = (data or {}).get("text", "").strip()
    if not text:
        return
    print(f"[typed] {text}")
    push_to_dashboard("text", {"content": f"You typed: {text}"})
    threading.Thread(target=handle_command, args=(text,), kwargs={"context_id": request.sid},
                      daemon=True).start()


# ---------- Graceful shutdown ----------
def _install_shutdown_handlers():
    def _handle_signal(signum, _frame):
        print(f"\n[47] Received signal {signum}; shutting down.")
        try:
            speak("Shutting down now. Goodbye.")
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _handle_signal)
    try:
        signal.signal(signal.SIGTERM, _handle_signal)
    except (AttributeError, ValueError):
        pass  # SIGTERM isn't available on every platform/thread context


if __name__ == "__main__":
    _install_shutdown_handlers()

    supervise("voice_loop", voice_loop)
    supervise("ambient", start_ambient)
    supervise("window_tracking", start_window_tracking)
    supervise("task_reminders", start_task_reminders)

    dashboard_url = f"http://{DASHBOARD_HOST if DASHBOARD_HOST != '0.0.0.0' else 'localhost'}:{DASHBOARD_PORT}/?token={DASHBOARD_TOKEN}"
    if DASHBOARD_HOST == "0.0.0.0":
        print("=" * 70)
        print("WARNING: DASHBOARD_HOST=0.0.0.0 — this dashboard is reachable from")
        print("every network interface on this machine (LAN, and the internet if")
        print("this machine is exposed). Anyone with the token below has full")
        print("shell access through this app. Only do this if you understand and")
        print("accept that.")
        print("=" * 70)
    print(f"[47] Dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    socketio.run(app, host=DASHBOARD_HOST, port=DASHBOARD_PORT)
