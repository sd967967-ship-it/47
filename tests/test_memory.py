import os
import tempfile
import unittest
from pathlib import Path

import memory


class MemoryTestCase(unittest.TestCase):
    """Points memory.DB_PATH at a fresh temp file per test so tests never
    touch the real memory_47.db and never leak state between each other."""

    def setUp(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.remove(path)  # sqlite3.connect creates it fresh
        self._tmp_path = path
        self._orig_db_path = memory.DB_PATH
        memory.DB_PATH = Path(path)

    def tearDown(self):
        memory.DB_PATH = self._orig_db_path
        try:
            os.remove(self._tmp_path)
        except OSError:
            pass


class TestFactNormalizationAndDedup(MemoryTestCase):
    def test_normalize_key_strips_filler_and_case(self):
        self.assertEqual(memory.normalize_key("My Flight"), "flight")
        self.assertEqual(memory.normalize_key("The Wifi Password"), "wifi password")

    def test_restating_a_fact_overwrites_not_duplicates(self):
        k1, v1 = memory.derive_key_and_value("My flight is at 6pm")
        memory.remember_fact(k1, v1)
        k2, v2 = memory.derive_key_and_value("my flight is at 7pm")
        memory.remember_fact(k2, v2)

        self.assertEqual(k1, k2)  # same normalized key
        facts = memory.all_facts()
        self.assertEqual(len(facts), 1)
        self.assertIn("7pm", facts[k1])

    def test_fact_without_is_falls_back_to_prefix_key(self):
        k, v = memory.derive_key_and_value("I have a dog named Rex")
        self.assertTrue(k)
        memory.remember_fact(k, v)
        self.assertEqual(memory.get_fact(k), v)

    def test_forget_fact(self):
        memory.remember_fact("test_key", "test value")
        self.assertTrue(memory.forget_fact("test_key"))
        self.assertIsNone(memory.get_fact("test_key"))
        self.assertFalse(memory.forget_fact("test_key"))  # already gone


class TestFactContextCap(MemoryTestCase):
    def test_facts_as_context_is_capped(self):
        for i in range(memory.MAX_FACTS_IN_CONTEXT + 20):
            memory.remember_fact(f"fact_{i}", f"value {i}")
        context = memory.facts_as_context()
        # count the "- " bullet lines, not the header
        bullet_lines = [l for l in context.splitlines() if l.startswith("- ")]
        self.assertLessEqual(len(bullet_lines), memory.MAX_FACTS_IN_CONTEXT)
        self.assertEqual(memory.fact_count(), memory.MAX_FACTS_IN_CONTEXT + 20)

    def test_no_facts_returns_empty_string(self):
        self.assertEqual(memory.facts_as_context(), "")


class TestTaskReviewAndCleanup(MemoryTestCase):
    def test_delete_task_matching(self):
        memory.add_task("buy milk", source="auto_detected")
        deleted = memory.delete_task_matching("milk")
        self.assertEqual(deleted, "buy milk")
        self.assertEqual(memory.list_open_tasks(), [])

    def test_delete_task_matching_no_match(self):
        self.assertIsNone(memory.delete_task_matching("nonexistent"))

    def test_clear_auto_detected_tasks_only_clears_those(self):
        memory.add_task("auto task 1", source="auto_detected")
        memory.add_task("auto task 2", source="auto_detected")
        memory.add_task("explicit reminder", source="explicit_reminder")

        removed = memory.clear_auto_detected_tasks()
        self.assertEqual(removed, 2)

        remaining = [t[1] for t in memory.list_open_tasks()]
        self.assertEqual(remaining, ["explicit reminder"])


if __name__ == "__main__":
    unittest.main()
