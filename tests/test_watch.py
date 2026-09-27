import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import memory
import watch


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class TestTasksDueBetween(unittest.TestCase):
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

    def test_window_filters(self):
        now = time.time()
        memory.add_task("today chore", due_at=now + 3600)
        memory.add_task("tomorrow chore", due_at=now + 90000)
        memory.add_task("undated chore")
        rows = memory.tasks_due_between(now - 60, now + 86400)
        descs = [r[1] for r in rows]
        self.assertIn("today chore", descs)
        self.assertNotIn("tomorrow chore", descs)
        self.assertNotIn("undated chore", descs)


class TestWatch(unittest.TestCase):
    def test_headlines_from_hn_shape(self):
        calls = {"n": 0}

        def fake_get(method, url, **kw):
            calls["n"] += 1
            if url.endswith("topstories.json"):
                return FakeResp([11, 22])
            return FakeResp({"title": f"Story {url[-8:-5]}"})

        watch._cache.update(at=0.0, headlines=[])
        with patch.object(watch, "request_with_retry", side_effect=fake_get):
            heads = watch.get_world_headlines(limit=2)
        self.assertEqual(len(heads), 2)
        self.assertTrue(all(h.startswith("Story") for h in heads))

    def test_agenda_empty(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)
        orig = memory.DB_PATH
        memory.DB_PATH = Path(path)
        try:
            self.assertIn("Nothing scheduled", watch.agenda_text())
        finally:
            memory.DB_PATH = orig
            try:
                os.remove(path)
            except OSError:
                pass

    def test_new_headlines_marks_seen(self):
        import json as _json
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        orig_state = watch.STATE_PATH
        watch.STATE_PATH = Path(path)
        watch._cache.update(at=0.0, headlines=[])
        try:
            with patch.object(watch, "get_world_headlines",
                              return_value=["Alpha story", "Beta story"]):
                fresh = watch.new_headlines(limit=2)
            self.assertEqual(fresh, ["Alpha story", "Beta story"])
            with patch.object(watch, "get_world_headlines",
                              return_value=["Alpha story", "Beta story"]):
                self.assertEqual(watch.new_headlines(limit=2), [])
        finally:
            watch.STATE_PATH = orig_state
            try:
                os.remove(path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
