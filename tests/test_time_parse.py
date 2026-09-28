import time
import unittest

import time_parse


class TestTimeParse(unittest.TestCase):
    def test_strip_reminder_prefix_with_due_phrase(self):
        out = time_parse.strip_reminder_prefix("remind me in 10 minutes to call the bank")
        self.assertEqual(out, "call the bank in 10 minutes")

    def test_strip_reminder_prefix_no_due_phrase(self):
        out = time_parse.strip_reminder_prefix("remind me to water the plants")
        self.assertEqual(out, "water the plants")

    def test_strip_reminder_prefix_no_to(self):
        out = time_parse.strip_reminder_prefix("remind me in 2 hours")
        self.assertEqual(out, "in 2 hours")

    def test_parse_due_minutes(self):
        before = time.time()
        due = time_parse.parse_due("call the bank in 10 minutes")
        self.assertIsNotNone(due)
        self.assertAlmostEqual(due - before, 600, delta=2)

    def test_parse_due_no_match(self):
        self.assertIsNone(time_parse.parse_due("call the bank"))

    def test_longer_unit_matches_before_shorter(self):
        # regression test for the documented alternation-ordering bugfix
        due = time_parse.parse_due("ping me in 10 minutes")
        stripped = time_parse.strip_due_phrase("ping me in 10 minutes")
        self.assertIsNotNone(due)
        self.assertNotIn("s ", stripped + " ")  # no stray trailing "s" left over

    def test_strip_due_phrase(self):
        out = time_parse.strip_due_phrase("call the bank in 10 minutes")
        self.assertEqual(out, "call the bank")

    def test_parse_due_at_time_is_future(self):
        import time
        due = time_parse.parse_due("wake me up at 15 26")
        self.assertIsNotNone(due)
        self.assertGreater(due, time.time())
        self.assertLess(due - time.time(), 86400 + 60)

    def test_wake_prefix_strips_to_time_only(self):
        raw = time_parse.strip_reminder_prefix("wake me up at 15 26")
        self.assertEqual(time_parse.strip_due_phrase(raw), "")


if __name__ == "__main__":
    unittest.main()
