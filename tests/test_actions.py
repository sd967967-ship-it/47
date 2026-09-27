import unittest
from unittest.mock import patch

import actions


class TestFindUrl(unittest.TestCase):
    def test_finds_url_and_strips_trailing_punctuation(self):
        text = "check out https://example.com/page, it's great."
        self.assertEqual(actions.find_url(text), "https://example.com/page")

    def test_no_url_returns_none(self):
        self.assertIsNone(actions.find_url("no links here"))


class TestOpenTerminalHonestFailure(unittest.TestCase):
    @patch("actions.platform.system", return_value="Linux")
    @patch("actions.subprocess.Popen", side_effect=FileNotFoundError)
    def test_reports_failure_when_nothing_is_installed(self, mock_popen, mock_system):
        # BUGFIX regression test: previously this returned "Opening a
        # terminal." even when every candidate binary was missing.
        result = actions._open_terminal()
        self.assertIn("Couldn't open a terminal", result)
        self.assertEqual(mock_popen.call_count, 3)  # tried all three candidates

    @patch("actions.platform.system", return_value="Linux")
    @patch("actions.subprocess.Popen")
    def test_reports_success_when_one_launches(self, mock_popen, mock_system):
        mock_popen.side_effect = [FileNotFoundError, None]  # konsole succeeds
        result = actions._open_terminal()
        self.assertEqual(result, "Opening a terminal.")


if __name__ == "__main__":
    unittest.main()
