"""Single-active-brain tests for 47 (Groq live today, Grok seam ready)."""
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
from providers import get_active_provider
from providers import groq as groq_provider
from providers import grok as grok_provider


class FakeProvider:
    """Stand-in with the same seam (send_message/request_tool_plan)."""
    def __init__(self, reply="fake answer", plan=None):
        self._reply = reply
        self._plan = plan or []
        self.sent = []

    def request_tool_plan(self, user_text, tools):
        return self._plan

    def send_message(self, messages):
        self.sent = messages
        return self._reply


class TestProviderSelection(unittest.TestCase):
    def test_no_keys_means_no_provider(self):
        with patch("vault.get", return_value=""):
            provider, name = get_active_provider()
        self.assertIsNone(provider)
        self.assertIsNone(name)

    def test_groq_key_selects_groq(self):
        with patch("vault.get", side_effect=lambda k: "x" if k == "GROQ_API_KEY" else ""):
            provider, name = get_active_provider()
        self.assertIs(provider, groq_provider)
        self.assertEqual(name, "Groq")

    def test_grok_key_selects_grok(self):
        with patch("vault.get", side_effect=lambda k: "x" if k == "XAI_API_KEY" else ""):
            provider, name = get_active_provider()
        self.assertIs(provider, grok_provider)
        self.assertEqual(name, "Grok")


class TestAskBrain(unittest.TestCase):
    def test_degraded_without_provider(self):
        with patch.object(main, "get_active_provider", return_value=(None, None)), \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("hello")
        self.assertIn("temporarily unavailable", reply)

    def test_answer_flows_through(self):
        fake = FakeProvider("hi there")
        with patch.object(main, "get_active_provider", return_value=(fake, "Fake")), \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("hello")
        self.assertEqual(reply, "hi there")
        self.assertEqual(fake.sent[-1], {"role": "user", "content": "hello"})

    def test_tool_plan_executes_locally(self):
        fake = FakeProvider("done", plan=[{"name": "fetch", "args": {"url": "https://example.com"}}])
        tools = [{"type": "function", "function": {"name": "fetch", "parameters": {}}}]
        with patch.object(main, "get_active_provider", return_value=(fake, "Fake")), \
             patch.object(main.mcp_client, "list_all_tools", return_value=tools), \
             patch.object(main.mcp_client, "call_tool", return_value="page text") as mc, \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("fetch https://example.com please")
        self.assertEqual(reply, "done")
        mc.assert_called_once_with("fetch", {"url": "https://example.com"})

    def test_provider_error_degrades(self):
        class Boom(FakeProvider):
            def send_message(self, messages):
                raise groq_provider.GroqUnavailable("down")

        with patch.object(main, "get_active_provider", return_value=(Boom(), "Fake")), \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("hello")
        self.assertIn("temporarily unavailable", reply)


class TestProviderUnits(unittest.TestCase):
    def test_groq_validates_messages(self):
        with self.assertRaises(ValueError):
            groq_provider._validate_messages([])
        with self.assertRaises(ValueError):
            groq_provider._validate_messages([{"role": "assistant", "content": "x"}])

    def test_groq_unavailable_without_key(self):
        with patch("vault.get", return_value=""):
            with self.assertRaises(groq_provider.GroqUnavailable):
                groq_provider.send_message([{"role": "user", "content": "hi"}])
            self.assertIn("missing", groq_provider.health_check())

    def test_grok_unavailable_without_key(self):
        with patch("vault.get", return_value=""):
            with self.assertRaises(grok_provider.GrokUnavailable):
                grok_provider.send_message([{"role": "user", "content": "hi"}])
            self.assertIn("missing", grok_provider.health_check())

    def test_vault_redact(self):
        import vault
        self.assertNotIn("xai-abc123XYZ", vault.redact("key xai-abc123XYZ here"))
        self.assertIn("<REDACTED>", vault.redact("key xai-abc123XYZ here"))
        self.assertEqual(vault.get("DEFINITELY_NOT_SET_47"), "")


if __name__ == "__main__":
    unittest.main()
