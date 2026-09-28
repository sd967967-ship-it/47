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


class TestSpeechChunks(unittest.TestCase):
    def test_splits_sentences(self):
        from tts_jarvis import _chunks
        text = ("Hello there, this is a much longer opening sentence for synthesis. "
                "How are you today, is everything working well on your side? "
                "I am fine and ready to help with whatever you need next.")
        parts = _chunks(text)
        self.assertGreaterEqual(len(parts), 2)
        self.assertTrue(all(len(p) <= 140 for p in parts))

    def test_short_text_single_chunk(self):
        from tts_jarvis import _chunks
        self.assertEqual(_chunks("Hi."), ["Hi."])


class TestNoProviderNames(unittest.TestCase):
    def test_prompt_claims_47_identity(self):
        import main
        self.assertIn("Your name is 47", main.SYSTEM_PROMPT)

    def test_greeting_has_no_provider(self):
        import inspect
        import main
        src = inspect.getsource(main.voice_loop)
        greeting_line = [ln for ln in src.split("\n") if "47 online" in ln]
        self.assertTrue(greeting_line)
        self.assertNotIn("brain_label", greeting_line[0])


if __name__ == "__main__":
    unittest.main()
