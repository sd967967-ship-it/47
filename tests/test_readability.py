import unittest

from readability import style_reply


class TestReadability(unittest.TestCase):
    def test_table_becomes_sentence(self):
        out = style_reply("| S&P | 7,743 | +0.5% |")
        self.assertNotIn("|", out)
        self.assertNotIn("*", out)
        self.assertIn("S&P", out)

    def test_bold_headers_ticks(self):
        out = style_reply("### Markets\n**Sensex** up, see `code`")
        self.assertNotIn("**", out)
        self.assertNotIn("#", out)
        self.assertNotIn("`", out)
        self.assertIn("Sensex", out)

    def test_paragraphs_kept(self):
        out = style_reply("First idea here.\n\nSecond idea here.")
        self.assertIn("\n\n", out)

    def test_plain_untouched(self):
        self.assertEqual(style_reply("Just talking."), "Just talking.")

    def test_links_readable(self):
        out = style_reply("read [the guide](https://example.com/x) now")
        self.assertIn("the guide", out)
        self.assertNotIn("https://", out)


if __name__ == "__main__":
    unittest.main()
