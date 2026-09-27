import unittest
from unittest.mock import patch, MagicMock

import requests

import net_utils


def _resp(status_code, headers=None):
    r = MagicMock(spec=requests.Response)
    r.status_code = status_code
    r.headers = headers or {}
    return r


class TestRequestWithRetry(unittest.TestCase):
    @patch("net_utils.time.sleep", return_value=None)
    @patch("requests.request")
    def test_success_first_try_no_retry(self, mock_request, mock_sleep):
        mock_request.return_value = _resp(200)
        resp = net_utils.request_with_retry("GET", "http://example.com")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_request.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("net_utils.time.sleep", return_value=None)
    @patch("requests.request")
    def test_retries_on_500_then_succeeds(self, mock_request, mock_sleep):
        mock_request.side_effect = [_resp(500), _resp(500), _resp(200)]
        resp = net_utils.request_with_retry("GET", "http://example.com", max_attempts=3)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("net_utils.time.sleep", return_value=None)
    @patch("requests.request")
    def test_gives_up_after_max_attempts(self, mock_request, mock_sleep):
        mock_request.return_value = _resp(500)
        resp = net_utils.request_with_retry("GET", "http://example.com", max_attempts=3)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(mock_request.call_count, 3)

    @patch("net_utils.time.sleep", return_value=None)
    @patch("requests.request")
    def test_honors_retry_after_header_on_429(self, mock_request, mock_sleep):
        mock_request.side_effect = [_resp(429, {"Retry-After": "2"}), _resp(200)]
        resp = net_utils.request_with_retry("GET", "http://example.com", max_attempts=3)
        self.assertEqual(resp.status_code, 200)
        mock_sleep.assert_called_once_with(2.0)

    @patch("net_utils.time.sleep", return_value=None)
    @patch("requests.request")
    def test_does_not_retry_ordinary_4xx(self, mock_request, mock_sleep):
        mock_request.return_value = _resp(404)
        resp = net_utils.request_with_retry("GET", "http://example.com", max_attempts=3)
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(mock_request.call_count, 1)  # no point retrying a 404
        mock_sleep.assert_not_called()

    @patch("net_utils.time.sleep", return_value=None)
    @patch("requests.request")
    def test_retries_on_timeout_then_raises_if_never_succeeds(self, mock_request, mock_sleep):
        mock_request.side_effect = requests.exceptions.Timeout("boom")
        with self.assertRaises(requests.exceptions.Timeout):
            net_utils.request_with_retry("GET", "http://example.com", max_attempts=2)
        self.assertEqual(mock_request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
