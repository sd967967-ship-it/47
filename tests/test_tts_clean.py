import unittest

from tts_jarvis import clean_for_speech


class TestCleanForSpeech(unittest.TestCase):
    def test_bold_and_headers(self):
        out = clean_for_speech("### Markets\n**S&P 500** up 2%")
        self.assertNotIn("**", out)
        self.assertNotIn("#", out)
        self.assertIn("S&P 500", out)

    def test_table_row(self):
        out = clean_for_speech("| S&P | 7,743 | +0.5% |")
        self.assertNotIn("|", out)
        self.assertIn("S&P", out)

    def test_links_and_ticks(self):
        out = clean_for_speech("see [docs](https://example.com) and `code`")
        self.assertIn("docs", out)
        self.assertNotIn("https://", out)
        self.assertNotIn("`", out)

    def test_slashes(self):
        out = clean_for_speech("open and/or closed w/ friends")
        self.assertNotIn("/", out)

    def test_plain_text_untouched(self):
        self.assertEqual(clean_for_speech("Hello there"), "Hello there")


if __name__ == "__main__":
    unittest.main()
