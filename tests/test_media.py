import sys
import types
import unittest
from unittest.mock import patch

import media


class TestMediaUrls(unittest.TestCase):
    def test_google_url_encodes(self):
        url = media.google_search_url("taj mahal history")
        self.assertIn("google.com/search?q=", url)
        self.assertIn("taj+mahal", url)

    def test_youtube_search_url(self):
        url = media.youtube_search_url("arijit singh songs")
        self.assertIn("youtube.com/results", url)

    def test_google_empty(self):
        self.assertIn("Tell me", media.google_search("  "))

    def test_play_empty(self):
        self.assertIn("Tell me", media.play_youtube("  "))

    def test_play_falls_back_to_search_page(self):
        with patch.object(media, "_resolve_youtube_watch", return_value=None), \
             patch.object(media.webbrowser, "open") as mock_open:
            report = media.play_youtube("some song")
        self.assertIn("search opened", report)
        opened = mock_open.call_args[0][0]
        self.assertIn("youtube.com/results", opened)

    def test_play_uses_resolved_watch_url(self):
        with patch.object(media, "_resolve_youtube_watch",
                          return_value="https://www.youtube.com/watch?v=abc&autoplay=1"), \
             patch.object(media.webbrowser, "open") as mock_open:
            report = media.play_youtube("some song")
        self.assertIn("Playing", report)
        mock_open.assert_called_once_with("https://www.youtube.com/watch?v=abc&autoplay=1")


if __name__ == "__main__":
    unittest.main()
