import unittest

import visual3d


class TestClassify(unittest.TestCase):
    def test_building(self):
        self.assertEqual(visual3d.classify("what does a skyscraper look like"), "building")

    def test_new_electronics_category(self):
        self.assertEqual(visual3d.classify("what does my laptop look like"), "electronics")

    def test_new_nature_category(self):
        self.assertEqual(visual3d.classify("what does a tree look like"), "nature")

    def test_new_furniture_category(self):
        self.assertEqual(visual3d.classify("show me a chair"), "furniture")

    def test_graph_keywords_win_over_object_keywords(self):
        # "compare" should route to bar/network charts, not a 3D shape,
        # even though "car" would otherwise match the vehicle category.
        self.assertIsNone(visual3d.classify("compare a car and a truck"))

    def test_no_match_returns_none(self):
        self.assertIsNone(visual3d.classify("what's the capital of France"))

    def test_build_payload_shape(self):
        kind, payload = visual3d.build_payload("furniture", "show me a chair")
        self.assertEqual(kind, "object3d")
        self.assertEqual(payload["type"], "furniture")
        self.assertEqual(payload["label"], "Show me a chair")

    def test_build_payload_none_category(self):
        self.assertEqual(visual3d.build_payload(None, "irrelevant"), (None, None))

    def test_tool_vehicle_map_categories(self):
        self.assertEqual(visual3d.classify("show me a wrench"), "tool")
        self.assertEqual(visual3d.classify("show me a drone"), "vehicle")
        self.assertEqual(visual3d.classify("show me a trail map"), "map_path")

    def test_word_boundaries_avoid_false_positives(self):
        self.assertIsNone(visual3d.classify("what is a card"))
        self.assertIsNone(visual3d.classify("sunscreen ingredients"))
        self.assertIsNone(visual3d.classify("implant procedure"))

    def test_generic_fallback_for_ask_questions(self):
        self.assertEqual(visual3d.classify_or_generic("render my idea in 3d"), "generic_object")
        self.assertIsNone(visual3d.classify_or_generic("what's the capital of France"))

    def test_floors_hint_flows_through(self):
        kind, payload = visual3d.build_payload("building", "show a 10-story tower")
        self.assertEqual(kind, "object3d")
        self.assertEqual(payload.get("floors"), 10)


if __name__ == "__main__":
    unittest.main()
