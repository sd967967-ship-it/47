"""Dashboard static guards — the whole inline script dies on one syntax
slip (a stray brace once killed typed input AND all 3D), so lock the
structure: balanced braces, every getElementById target exists, key
handlers and renderers present."""
import re
import unittest
from pathlib import Path

HTML = Path(__file__).parent.parent / "templates" / "dashboard.html"


def _inline_script():
    text = HTML.read_text(encoding="utf-8")
    scripts = re.findall(r"<script>(.*?)</script>", text, re.DOTALL)
    assert scripts, "no inline script found"
    return scripts[0]


def _stripped(script: str) -> str:
    script = re.sub(r"`(?:[^`\\]|\\.)*`", "``", script)
    script = re.sub(r"'(?:[^'\\\n]|\\.)*'", "''", script)
    script = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', script)
    return re.sub(r"//[^\n]*", "", script)


class TestDashboardScript(unittest.TestCase):
    def test_braces_balanced(self):
        bal = 0
        for line in _stripped(_inline_script()).split("\n"):
            bal += line.count("{") - line.count("}")
            self.assertGreaterEqual(bal, 0, "brace depth went negative")
        self.assertEqual(bal, 0, "unbalanced braces in dashboard script")

    def test_no_double_close_after_emblem(self):
        script = _inline_script()
        self.assertIsNone(
            re.search(r"emblemRings\.push\(ring\);\s*\n\s*\}\);\n\}\n\}", script),
            "stray extra brace after renderEmblem",
        )

    def test_all_dom_ids_exist(self):
        text = HTML.read_text(encoding="utf-8")
        script = _inline_script()
        wanted = set(re.findall(r"getElementById\('([^']+)'\)", script))
        have = set(re.findall(r'id="([^"]+)"', text))
        self.assertEqual(wanted - have, set(),
                         f"JS references missing DOM ids: {wanted - have}")

    def test_key_handlers_present(self):
        script = _inline_script()
        for token in ("function sendTyped", "user_text_command",
                      "function renderEmblem", "enterResponseMode",
                      "emblemRings", "textClose"):
            self.assertIn(token, script, f"missing {token}")

    def test_single_centered_response(self):
        # Exactly one response surface: no mirror of the reply text into
        # the right rail (railBody removed), panel centered via transform.
        text = HTML.read_text(encoding="utf-8")
        self.assertNotIn("railBody", text)
        self.assertIn("translate(-50%,-50%)", text)

    def test_robotic_type_stack(self):
        text = HTML.read_text(encoding="utf-8")
        self.assertIn("Share Tech Mono", text)
        self.assertIn("--font-display", text)


if __name__ == "__main__":
    unittest.main()
