import unittest

import models3d
import persona


class TestModels3D(unittest.TestCase):
    def test_keyword_resolve(self):
        self.assertEqual(models3d.resolve("show me a boombox"), "BoomBox.glb")
        self.assertEqual(models3d.resolve("render a duck"), "Duck.glb")

    def test_category_fallback(self):
        self.assertEqual(models3d.resolve("something electronic", "electronics"), "BoomBox.glb")

    def test_no_match_returns_none(self):
        self.assertIsNone(models3d.resolve("show me a car"))

    def test_allowlist_blocks_traversal(self):
        self.assertIsNone(models3d.model_path("../main.py"))
        self.assertIsNone(models3d.model_path("C:\\Windows\\System32\\x.glb"))
        self.assertIsNone(models3d.model_path("Nope.glb"))


class TestPersona(unittest.TestCase):
    def test_cycle_covers_all_before_repeat(self):
        persona.reset_cycles()
        seen = {persona.greeting() for _ in range(len(persona._GREETINGS))}
        self.assertEqual(len(seen), len(persona._GREETINGS))

    def test_followups_vary(self):
        persona.reset_cycles()
        first = persona.followup()
        rest = {persona.followup() for _ in range(len(persona._FOLLOWUPS) - 1)}
        self.assertEqual(len(rest | {first}), len(persona._FOLLOWUPS))


if __name__ == "__main__":
    unittest.main()
