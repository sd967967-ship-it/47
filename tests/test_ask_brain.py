"""Grok-only provider tests for 47 (no Ollama paths may remain active)."""
import os
import sys
import types
import unittest
from unittest.mock import patch

if "flask_socketio" not in sys.modules:
    fake = types.ModuleType("flask_socketio")

    class _FakeSocketIO:
        def __init__(self, app, **kwargs):
            pass

        def on(self, *a, **k):
            def deco(fn):
                return fn
            return deco

        def emit(self, *a, **k):
            pass

        def run(self, *a, **k):
            pass

    fake.SocketIO = _FakeSocketIO
    sys.modules["flask_socketio"] = fake

if "speech_recognition" not in sys.modules:
    fake_sr = types.ModuleType("speech_recognition")
    fake_sr.Recognizer = object
    fake_sr.Microphone = object
    fake_sr.UnknownValueError = type("UnknownValueError", (Exception,), {})
    fake_sr.RequestError = type("RequestError", (Exception,), {})
    sys.modules["speech_recognition"] = fake_sr

if "mcp" not in sys.modules:
    fake_mcp = types.ModuleType("mcp")
    fake_mcp.ClientSession = object
    fake_mcp.StdioServerParameters = object
    sys.modules["mcp"] = fake_mcp
    sys.modules["mcp.client"] = types.ModuleType("mcp.client")
    stdio_mod = types.ModuleType("mcp.client.stdio")
    stdio_mod.stdio_client = lambda *a, **k: None
    sys.modules["mcp.client.stdio"] = stdio_mod

os.environ["DASHBOARD_TOKEN"] = "test-token-for-suite"

import main
from providers import grok as grok_provider


class TestGrokOnlyBrain(unittest.TestCase):
    def test_no_ollama_attributes(self):
        for attr in ("ask_ollama", "ask_groq", "BRAIN", "OLLAMA_URL",
                     "OLLAMA_MODEL", "GROQ_API_KEY", "GROQ_MODEL"):
            self.assertFalse(hasattr(main, attr), f"main.{attr} must not exist")

    def test_no_ollama_source_references(self):
        import pathlib
        src = pathlib.Path(main.__file__).read_text(encoding="utf-8")
        self.assertNotIn("localhost:11434", src)
        self.assertNotIn("api.groq.com", src)

    def test_degraded_without_key(self):
        with patch.object(grok_provider, "_key", return_value=""):
            with patch.object(main.memory, "log_turn"):
                reply = main.ask_brain("hello")
        self.assertIn("temporarily unavailable", reply)

    def test_answer_flows_through(self):
        fake_tools = [{"type": "function",
                       "function": {"name": "fetch", "parameters": {}}}]
        with patch.object(grok_provider, "send_message", return_value="hi there"), \
             patch.object(grok_provider, "request_tool_plan", return_value=[]), \
             patch.object(main.mcp_client, "list_all_tools", return_value=fake_tools), \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("hello")
        self.assertEqual(reply, "hi there")

    def test_tool_plan_executes_locally(self):
        fake_tools = [{"type": "function",
                       "function": {"name": "fetch", "parameters": {}}}]
        plan = [{"name": "fetch", "args": {"url": "https://example.com"}}]
        with patch.object(grok_provider, "send_message", return_value="done"), \
             patch.object(grok_provider, "request_tool_plan", return_value=plan), \
             patch.object(main.mcp_client, "list_all_tools", return_value=fake_tools), \
             patch.object(main.mcp_client, "call_tool", return_value="page text") as mc, \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("fetch https://example.com please")
        self.assertEqual(reply, "done")
        mc.assert_called_once_with("fetch", {"url": "https://example.com"})


class TestVault(unittest.TestCase):
    def test_redact(self):
        import vault
        self.assertNotIn("xai-abc123XYZ", vault.redact("key xai-abc123XYZ here"))
        self.assertIn("<REDACTED>", vault.redact("key xai-abc123XYZ here"))
        self.assertEqual(vault.get("DEFINITELY_NOT_SET_47"), "")


if __name__ == "__main__":
    unittest.main()
