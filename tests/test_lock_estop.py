import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import estop
import lock
import memory


class TestLock(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".lock")
        os.close(fd)
        os.remove(path)
        self._orig = lock.LOCK_PATH
        lock.LOCK_PATH = Path(path)
        self._tmp = path
        lock.reset_state()

    def tearDown(self):
        lock.LOCK_PATH = self._orig
        lock.reset_state()
        try:
            os.remove(self._tmp)
        except OSError:
            pass

    def test_setup_and_verify(self):
        self.assertFalse(lock.is_configured())
        lock.set_pin("271400")
        self.assertTrue(lock.is_configured())
        ok, _ = lock.verify("271400")
        self.assertTrue(ok)
        self.assertTrue(lock.is_unlocked())

    def test_weak_pin_rejected(self):
        with self.assertRaises(ValueError):
            lock.set_pin("12")
        with self.assertRaises(ValueError):
            lock.set_pin("abcd")

    def test_wrong_pin_no_unlock(self):
        lock.set_pin("271400")
        lock.reset_state()
        ok, msg = lock.verify("0000")
        self.assertFalse(ok)
        self.assertFalse(lock.is_unlocked())
        self.assertIn("tries left", msg)

    def test_lockout_after_five(self):
        lock.set_pin("271400")
        lock.reset_state()
        for _ in range(5):
            lock.verify("0000")
        ok, msg = lock.verify("0000")
        self.assertFalse(ok)
        self.assertIn("locked for", msg)

    def test_no_plaintext_in_file(self):
        lock.set_pin("271400")
        blob = Path(self._tmp).read_text(encoding="utf-8")
        self.assertNotIn("271400", blob)


class TestEstop(unittest.TestCase):
    def setUp(self):
        estop.reset_state()

    def tearDown(self):
        estop.reset_state()

    def test_stop_blocks_shell(self):
        import shell
        estop.stop("test")
        self.assertTrue(estop.is_stopped())
        self.assertIn("stopped", shell.run("echo hi").lower())
        self.assertTrue(estop.resume())
        self.assertFalse(estop.is_stopped())

    def test_stop_is_audited(self):
        rec = estop.stop("voice-test", "kill agent 47")
        self.assertEqual(rec["source"], "voice-test")
        self.assertIn("ts", rec)


class TestErase(unittest.TestCase):
    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        self._orig = memory.DB_PATH
        memory.DB_PATH = Path(path)
        self._tmp = path

    def tearDown(self):
        memory.DB_PATH = self._orig
        try:
            os.remove(self._tmp)
        except OSError:
            pass

    def test_erase_all_keeps_tasks(self):
        memory.remember_fact("nickname", "tester")
        memory.log_turn("user", "hi")
        memory.add_task("keep me", source="explicit")
        counts = memory.erase_all_memory()
        self.assertEqual(counts["facts"], 1)
        self.assertEqual(counts["turns"], 1)
        self.assertEqual(memory.fact_count(), 0)
        self.assertEqual(len(memory.list_open_tasks()), 1)

    def test_find_candidates(self):
        memory.remember_fact("nickname", "tester")
        rows = memory.find_fact_candidates("nick")
        self.assertEqual(len(rows), 1)


class TestSafetyEndpoints(unittest.TestCase):
    def test_permissions_and_health_gated(self):
        import main
        orig = main.DASHBOARD_TOKEN
        main.DASHBOARD_TOKEN = "test-token-safe"
        try:
            client = main.app.test_client()
            self.assertEqual(client.get("/api/permissions").status_code, 403)
            resp = client.get("/api/permissions?token=test-token-safe")
            self.assertEqual(resp.status_code, 200)
            ids = [p["id"] for p in resp.get_json()["permissions"]]
            self.assertIn("microphone", ids)
            self.assertIn("files", ids)
            body = resp.get_data(as_text=True)
            self.assertNotIn("gsk_", body)
            h = client.get("/api/health?token=test-token-safe")
            self.assertEqual(h.status_code, 200)
            data = h.get_json()
            self.assertIn("agent", data)
            self.assertIn("issues", data)
        finally:
            main.DASHBOARD_TOKEN = orig


if __name__ == "__main__":
    unittest.main()
