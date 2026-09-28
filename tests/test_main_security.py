"""
main.py pulls in flask_socketio, speech_recognition, and (via mcp_client)
the `mcp` package for its voice/socket/tool-calling features. None of
those are needed to exercise the two pieces of main.py this file actually
tests (the dashboard token check, and the passive-scan noise-reduction
regex), so they're stubbed here with minimal fakes rather than skipping
the test — this is a real import and real execution of main.py, not a
mock of main.py itself.
"""

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# ---- Stub optional heavy dependencies before importing main ----
if "flask_socketio" not in sys.modules:
    fake_flask_socketio = types.ModuleType("flask_socketio")

    class _FakeSocketIO:
        def __init__(self, app, **kwargs):
            self.app = app

        def on(self, event_name):
            def decorator(fn):
                return fn
            return decorator

        def emit(self, *a, **kw):
            pass

        def run(self, *a, **kw):
            pass

    fake_flask_socketio.SocketIO = _FakeSocketIO
    sys.modules["flask_socketio"] = fake_flask_socketio

if "speech_recognition" not in sys.modules:
    fake_sr = types.ModuleType("speech_recognition")

    class _FakeRecognizer:
        def adjust_for_ambient_noise(self, source, duration=0.5):
            pass

        def listen(self, source):
            return None

        def recognize_google(self, audio):
            return ""

    class _FakeMicrophone:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    fake_sr.Recognizer = _FakeRecognizer
    fake_sr.Microphone = _FakeMicrophone
    fake_sr.UnknownValueError = type("UnknownValueError", (Exception,), {})
    fake_sr.RequestError = type("RequestError", (Exception,), {})
    sys.modules["speech_recognition"] = fake_sr

if "mcp" not in sys.modules:
    fake_mcp = types.ModuleType("mcp")
    fake_mcp.ClientSession = object
    fake_mcp.StdioServerParameters = object
    fake_mcp_client_pkg = types.ModuleType("mcp.client")
    fake_mcp_client_stdio = types.ModuleType("mcp.client.stdio")
    fake_mcp_client_stdio.stdio_client = lambda *a, **kw: None
    sys.modules["mcp"] = fake_mcp
    sys.modules["mcp.client"] = fake_mcp_client_pkg
    sys.modules["mcp.client.stdio"] = fake_mcp_client_stdio

# Pin the dashboard token so main.py doesn't write a token file to disk
# as a side effect of being imported by the test suite.
os.environ["DASHBOARD_TOKEN"] = "test-token-for-suite"

import main  # noqa: E402  (must come after the stubbing above)
import memory  # noqa: E402


class TestDashboardTokenGate(unittest.TestCase):
    """Regression tests for the 'dashboard has zero authentication' fix."""

    def setUp(self):
        self.client = main.app.test_client()

    def test_check_token_accepts_correct_token(self):
        self.assertTrue(main._check_token("test-token-for-suite"))

    def test_check_token_rejects_wrong_token(self):
        self.assertFalse(main._check_token("something-else"))

    def test_check_token_rejects_empty(self):
        self.assertFalse(main._check_token(""))

    def test_dashboard_route_403s_without_token(self):
        resp = self.client.get("/classic")
        self.assertEqual(resp.status_code, 403)

    def test_dashboard_route_403s_with_wrong_token(self):
        resp = self.client.get("/classic?token=nope")
        self.assertEqual(resp.status_code, 403)

    def test_dashboard_route_200s_with_correct_token(self):
        resp = self.client.get("/classic?token=test-token-for-suite")
        self.assertEqual(resp.status_code, 200)

    def test_root_proxies_node_and_403s_without_token(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 403)

    def test_on_connect_rejects_bad_token(self):
        fake_request = MagicMock()
        fake_request.args.get.return_value = "wrong"
        fake_request.remote_addr = "127.0.0.1"
        with unittest.mock.patch("main.request", fake_request):
            self.assertFalse(main.on_connect())

    def test_on_connect_accepts_good_token(self):
        fake_request = MagicMock()
        fake_request.args.get.return_value = "test-token-for-suite"
        fake_request.sid = "sid-123"
        with unittest.mock.patch("main.request", fake_request):
            self.assertTrue(main.on_connect())
            self.assertIn("sid-123", main._authed_sids)
        main._authed_sids.discard("sid-123")


class TestPassiveScanNoiseReduction(unittest.TestCase):
    """Regression tests for the fix: task triggers only fire at an actual
    clause/sentence boundary, not anywhere as a bare substring."""

    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        self._orig_db_path = memory.DB_PATH
        memory.DB_PATH = Path(path)
        self._tmp_path = path

    def tearDown(self):
        memory.DB_PATH = self._orig_db_path
        try:
            os.remove(self._tmp_path)
        except OSError:
            pass

    def test_first_person_intent_at_start_is_logged(self):
        main.passive_scan("i need to call the dentist tomorrow")
        tasks = [t[1] for t in memory.list_open_tasks()]
        self.assertEqual(tasks, ["call the dentist tomorrow"])

    def test_first_person_intent_after_sentence_boundary_is_logged(self):
        main.passive_scan("that meeting ran long. i have to leave now")
        tasks = [t[1] for t in memory.list_open_tasks()]
        self.assertEqual(tasks, ["leave now"])

    def test_quoted_third_party_speech_is_not_logged(self):
        # "she said i need to leave early" — the trigger is present, but not
        # at a clause boundary that represents the *speaker's own* intent.
        main.passive_scan("she said i need to leave early")
        self.assertEqual(memory.list_open_tasks(), [])


if __name__ == "__main__":
    unittest.main()
