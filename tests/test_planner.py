import unittest

import planner


class TestPlanner(unittest.TestCase):
    def test_compound_request_needs_plan(self):
        self.assertTrue(planner.needs_plan("search bitcoin price then convert 1 btc to usd"))

    def test_single_request_no_plan(self):
        self.assertFalse(planner.needs_plan("what is the bitcoin price"))

    def test_casual_chat_no_plan(self):
        self.assertFalse(planner.needs_plan("hi 47 how are you today"))

    def test_split_steps(self):
        steps = planner.split_steps("search leeds weather then open bbc and finally summarize it")
        self.assertGreaterEqual(len(steps), 2)
        self.assertTrue(all(steps))

    def test_split_caps_at_max(self):
        steps = planner.split_steps("a then b then c then d then e then f")
        self.assertLessEqual(len(steps), planner.MAX_STEPS)

    def test_and_plus_verb_splits(self):
        steps = planner.split_steps("open youtube and play tera zikr")
        self.assertEqual(len(steps), 2)
        self.assertTrue(planner.needs_plan("open youtube and play tera zikr"))

    def test_plain_and_does_not_split(self):
        self.assertFalse(planner.needs_plan("bread and butter"))


if __name__ == "__main__":
    unittest.main()
