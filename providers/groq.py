"""
47 Groq provider — free-tier cloud LLM (https://console.groq.com).

Same AIProvider seam as providers/grok.py:
    send_message(messages, options) -> str
    request_tool_plan(user_text, tools) -> [{name, args}] (max 2)
    health_check() -> 'ok' | human-readable problem

Fast defaults (verified snappy on this laptop): openai/gpt-oss-20b,
low reasoning effort, tools only for tool-shaped requests, 2 rounds max.
Key via vault.py only — never logged (see vault.redact).
"""
import json
import os

from net_utils import request_with_retry
import vault

BASE_URL = "https://api.groq.com/openai/v1"
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_TOKENS = int(os.environ.get("GROQ_MAX_TOKENS", "1000"))
TEMPERATURE = float(os.environ.get("GROQ_TEMPERATURE", "0.4"))
REASONING = os.environ.get("GROQ_REASONING_EFFORT", "low")


class GroqUnavailable(Exception):
    """Raised when Groq cannot produce an answer. Message is user-safe."""


def _key() -> str:
    return vault.get("GROQ_API_KEY")


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
    if not _key():
        raise GroqUnavailable("missing API key")
    body = {"model": MODEL, "messages": _validate_messages(messages),
            "max_tokens": MAX_TOKENS, "temperature": TEMPERATURE,
            "reasoning_effort": REASONING, "stream": False}
    try:
        resp = request_with_retry("POST", f"{BASE_URL}/chat/completions",
                                  headers=_headers(), json=body,
                                  timeout=45, max_attempts=2, base_delay=0.4)
    except Exception:
        raise GroqUnavailable("network failure")
    if resp.status_code == 429:
        raise GroqUnavailable("rate limited")
    if resp.status_code == 401:
        raise GroqUnavailable("invalid API key")
    try:
        resp.raise_for_status()
        return (resp.json()["choices"][0]["message"].get("content") or "").strip() \
            or "(empty reply)"
    except Exception:
        raise GroqUnavailable("bad response")


def _needs_tools_hint(user_text: str) -> bool:
    lowered = user_text.lower()
    if "http://" in lowered or "https://" in lowered:
        return True
    hints = ("fetch", "search", "weather", "browse", "open ", "run command",
             "file", "folder", "disk", "screenshot")
    return any(h in lowered for h in hints) or len(user_text) > 160


def request_tool_plan(user_text: str, tools: list) -> list:
    if not tools or not _needs_tools_hint(user_text):
        return []
    if not _key():
        return []
    try:
        body = {"model": MODEL,
                "messages": [{"role": "system",
                              "content": "You route requests to tools. Reply ONLY with a "
                                         "JSON array of at most 2 {name, args} objects, or []."},
                             {"role": "user", "content": user_text[:1500]}],
                "max_tokens": 300, "temperature": 0.0, "stream": False,
                "tools": tools, "tool_choice": "auto"}
        resp = request_with_retry("POST", f"{BASE_URL}/chat/completions",
                                  headers=_headers(), json=body,
                                  timeout=30, max_attempts=1)
        resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        if msg.get("content"):
            try:
                parsed = json.loads(msg["content"])
                if isinstance(parsed, list):
                    return [c for c in parsed
                            if isinstance(c, dict) and c.get("name")][:2]
            except ValueError:
                pass
        calls = []
        for call in msg.get("tool_calls") or []:
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            if not isinstance(args, dict):
                args = {}
            calls.append({"name": call["function"].get("name", ""), "args": args})
            if len(calls) >= 2:
                break
        return calls
    except Exception:
        return []


def send_vision(prompt: str, img_b64: str, mime: str = "image/jpeg") -> str:
    raise GroqUnavailable("no vision model on the Groq free tier right now")


def health_check() -> str:
    if not _key():
        return "missing GROQ_API_KEY"
    try:
        resp = request_with_retry("GET", f"{BASE_URL}/models",
                                  headers=_headers(), timeout=15, max_attempts=1)
        if resp.status_code == 401:
            return "invalid GROQ_API_KEY"
        resp.raise_for_status()
        return "ok"
    except Exception:
        return "cannot reach api.groq.com from here"
