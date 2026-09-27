"""Dual-brain fallback tests for 47 (Groq <-> Ollama)."""
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


class TestAskBrainFallback(unittest.TestCase):
    def test_groq_success_no_fallback(self):
        with patch.object(main, "BRAIN", "groq"), \
             patch.object(main, "GROQ_API_KEY", "fake"), \
             patch.object(main, "ask_groq", return_value="groq answer") as mg, \
             patch.object(main, "ask_ollama") as mo, \
             patch.object(main.memory, "log_turn"):
            self.assertEqual(main.ask_brain("hi"), "groq answer")
            mg.assert_called_once()
            mo.assert_not_called()

    def test_groq_fail_falls_back_to_ollama(self):
        with patch.object(main, "BRAIN", "groq"), \
             patch.object(main, "GROQ_API_KEY", "fake"), \
             patch.object(main, "ask_groq",
                          return_value="I couldn't reach Groq. Error: down"), \
             patch.object(main, "ask_ollama", return_value="local answer"), \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("hi")
            self.assertIn("local answer", reply)
            self.assertIn("Groq unavailable", reply)

    def test_both_fail_keeps_primary_error(self):
        with patch.object(main, "BRAIN", "groq"), \
             patch.object(main, "GROQ_API_KEY", "fake"), \
             patch.object(main, "ask_groq",
                          return_value="I couldn't reach Groq. Error: down"), \
             patch.object(main, "ask_ollama",
                          return_value="I couldn't reach my local brain (Ollama). Error: down"), \
             patch.object(main.memory, "log_turn"):
            reply = main.ask_brain("hi")
            self.assertTrue(reply.startswith("I couldn't reach Groq"))

    def test_ollama_fail_falls_back_to_groq(self):
        with patch.object(main, "BRAIN", "ollama"), \
             patch.object(main, "GROQ_API_KEY", "fake"), \
             patch.object(main, "ask_ollama",
                          return_value="I couldn't reach my local brain (Ollama). Error: down"), \
             patch.object(main, "ask_groq", return_value="groq answer"), \
             patch.object(main.memory, "log_turn"):
            self.assertEqual(main.ask_brain("hi"), "groq answer")


if __name__ == "__main__":
    unittest.main()
