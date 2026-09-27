"""Golden-case evals for 47 — deterministic quality gate, no network, no LLM.

Idea from bertrandmbanwi/Jarvis evals/golden_cases.yml (MIT): fixed
input->expectation pairs that catch regressions in routing (planner,
3D classify, confirm gates, currency fast-paths). Runs inside the normal
unittest suite, so `python -m unittest discover -s tests` is the harness.
"""
import unittest

import planner
import publicdata
import shell
import visual3d

CASES = [
    # (input, check-name, actual, expected)
    ("search bitcoin price then convert 1 btc to usd", "plan", None, True),
    ("hi there", "plan", None, False),
    ("show me a wrench", "category", None, "tool"),
    ("what is a card", "category", None, None),
    ("render my idea in 3d", "generic", None, "generic_object"),
    ("vssadmin delete shadows", "confirm", None, True),
    ("echo hello", "confirm", None, False),
    ("show a 10-story tower", "floors", None, 10),
]


def evaluate(case):
    text, kind = case[0], case[1]
    if kind == "plan":
        return planner.needs_plan(text)
    if kind == "category":
        return visual3d.classify(text)
    if kind == "generic":
        return visual3d.classify_or_generic(text)
    if kind == "confirm":
        return shell.needs_confirmation(text)
    if kind == "floors":
        _, payload = visual3d.build_payload("building", text)
        return payload.get("floors")
    raise AssertionError(f"unknown check {kind}")


class TestGoldenCases(unittest.TestCase):
    def test_golden_cases(self):
        failures = []
        for text, kind, _, expected in CASES:
            try:
                actual = evaluate((text, kind))
                self.assertEqual(actual, expected, msg=f"[{kind}] {text!r}")
            except AssertionError as e:
                failures.append(str(e))
        self.assertEqual(failures, [])

    def test_currency_same_unit_needs_no_network(self):
        self.assertIn("still", publicdata.convert_currency(5, "usd", "USD"))


if __name__ == "__main__":
    unittest.main()
