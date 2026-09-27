"""
47 AI provider layer — Grok/xAI is the ONLY cloud LLM provider.

Interface (the single seam every caller uses):
    send_message(messages, options)   -> str   (one complete reply)
    stream_message(messages, options) -> yields str deltas (SSE)
    request_tool_plan(context, tools) -> list of {name, args} (max 2)
    health_check()                    -> "ok" | human-readable problem

Rules enforced here (spec):
  - No Ollama paths, endpoints, fallbacks, or UI references (removed).
  - Key comes from vault.py (env/keyring/.47_env) — never logged, never
    sent anywhere except api.x.ai over HTTPS.
  - Payloads validated, history trimmed, sizes capped, timeouts + safe
    retries; user-facing errors never leak raw provider output or keys.
  - When Grok is unreachable/missing: callers show "47 is temporarily
    unavailable" and keep local non-LLM features working.

xAI endpoint is OpenAI-compatible: POST {base}/chat/completions.
Default model grok-3-mini (fast); override with GROK_MODEL.
"""
import json
import os

from net_utils import request_with_retry
import vault

BASE_URL = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1").rstrip("/")
MODEL = os.environ.get("GROK_MODEL", "grok-3-mini")
MAX_TOKENS = int(os.environ.get("GROK_MAX_TOKENS", "1000"))
TEMPERATURE = float(os.environ.get("GROK_TEMPERATURE", "0.4"))

UNAVAILABLE = ("47 is temporarily unavailable right now (no answer from Grok). "
               "Your files, tasks, reminders, system status, and dashboard "
               "still work — try again in a bit.")


class GrokUnavailable(Exception):
    """Raised when the Grok call cannot produce an answer."""


def _key() -> str:
    return vault.get("XAI_API_KEY")


def _headers() -> dict:
    return {"Authorization": f"Bearer {_key()}", "Content-Type": "application/json"}


def _validate_messages(messages) -> list:
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages must be a non-empty list")
    clean = []
    for m in messages[-20:]:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        content = (m.get("content") or "")[:4000]
        if role in ("system", "user", "assistant", "tool") and content:
            clean.append({"role": role, "content": content})
    if not clean or clean[-1]["role"] != "user":
        raise ValueError("messages must end with a user message")
    return clean


def send_message(messages, options=None) -> str:
    """One complete reply. Raises GrokUnavailable (never leaks internals)."""
    if not _key():
        raise GrokUnavailable("missing API key")
    try:
        body = {"model": MODEL, "messages": _validate_messages(messages),
                "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE,
                "stream": False}
        resp = request_with_retry("POST", f"{BASE_URL}/chat/completions",
                                  headers=_headers(), json=body,
                                  timeout=45, max_attempts=2, base_delay=0.4)
    except Exception:
        raise GrokUnavailable("network failure")
    if resp.status_code == 429:
        raise GrokUnavailable("rate limited")
    if resp.status_code == 401:
        raise GrokUnavailable("invalid API key")
    try:
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"].get("content") or ""
        return text.strip() or "(empty reply)"
    except Exception:
        raise GrokUnavailable("bad response")


def stream_message(messages, options=None):
    """Yield reply deltas via SSE. Raises GrokUnavailable on setup failure."""
    import requests
    if not _key():
        raise GrokUnavailable("missing API key")
    body = {"model": MODEL, "messages": _validate_messages(messages),
            "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE, "stream": True}
    try:
        resp = requests.post(f"{BASE_URL}/chat/completions", headers=_headers(),
                             json=body, timeout=60, stream=True)
        resp.raise_for_status()
    except Exception:
        raise GrokUnavailable("network failure")
    for line in resp.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        try:
            delta = json.loads(data)["choices"][0]["delta"].get("content") or ""
            if delta:
                yield delta
        except (ValueError, KeyError, IndexError):
            continue


def request_tool_plan(user_text: str, tools: list) -> list:
    """Ask Grok which tools (if any) serve this request. Max 2 calls.
    Returns [] for casual chat or any failure — never raises."""
    if not tools or not _needs_tools_hint(user_text):
        return []
    try:
        body = {"model": MODEL,
                "messages": [{"role": "system",
                              "content": "You route requests to tools. Reply with a JSON "
                                         "array of at most 2 {name, args} objects, or []."},
                             {"role": "user", "content": user_text[:1500]}],
                "max_tokens": 300, "temperature": 0.0, "stream": False,
                "tools": tools, "tool_choice": "auto"}
        resp = request_with_retry("POST", f"{BASE_URL}/chat/completions",
                                  headers=_headers(), json=body,
                                  timeout=30, max_attempts=1)
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        calls = []
        for call in msg.get("tool_calls") or []:
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            calls.append({"name": call["function"].get("name", ""), "args": args})
            if len(calls) >= 2:
                break
        return calls
    except Exception:
        return []


def _needs_tools_hint(user_text: str) -> bool:
    lowered = user_text.lower()
    if "http://" in lowered or "https://" in lowered:
        return True
    hints = ("fetch", "search", "weather", "browse", "open ", "run command",
             "file", "folder", "disk", "screenshot")
    return any(h in lowered for h in hints) or len(user_text) > 160


def send_vision(prompt: str, img_b64: str, mime: str = "image/jpeg") -> str:
    """Describe an image with a vision-capable Grok model. Raises
    GrokUnavailable when there is no key, no vision model, or any failure —
    callers surface an honest message, never a traceback or key."""
    if not _key():
        raise GrokUnavailable("missing API key")
    body = {"model": os.environ.get("GROQ_VISION_MODEL", "grok-2-vision"),
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt[:1000]},
                {"type": "image_url",
                 "image_url": {"url": f"data:{mime};base64,{img_b64}"}}]}],
            "max_tokens": 300, "temperature": 0.2, "stream": False}
    try:
        resp = request_with_retry("POST", f"{BASE_URL}/chat/completions",
                                  headers=_headers(), json=body,
                                  timeout=45, max_attempts=1)
        resp.raise_for_status()
        return (resp.json()["choices"][0]["message"].get("content") or "").strip()
    except Exception:
        raise GrokUnavailable("vision call failed")


def health_check() -> str:
    """'ok' or a human-readable problem (key-shaped data never included)."""
    if not _key():
        return "missing XAI_API_KEY — add it to use the Grok brain"
    try:
        resp = request_with_retry("GET", f"{BASE_URL}/models",
                                  headers=_headers(), timeout=15, max_attempts=1)
        if resp.status_code == 401:
            return "invalid XAI_API_KEY"
        resp.raise_for_status()
        return "ok"
    except Exception:
        return "cannot reach api.x.ai from here"
