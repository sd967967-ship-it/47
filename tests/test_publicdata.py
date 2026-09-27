import time
import unittest
from unittest.mock import patch

import publicdata
import shell


class FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class TestPublicData(unittest.TestCase):
    def test_same_currency_no_network(self):
        self.assertIn("still", publicdata.convert_currency(5, "usd", "USD"))

    def test_zero_amount_no_network(self):
        self.assertIn("greater than zero", publicdata.convert_currency(0, "usd", "eur"))

    def test_convert_parses_frankfurter(self):
        with patch.object(publicdata, "request_with_retry",
                          return_value=FakeResp({"rates": {"EUR": 92.5}, "date": "2026-09-28"})):
            report = publicdata.convert_currency(100, "usd", "eur")
        self.assertIn("92.5", report)
        self.assertIn("EUR", report)

    def test_crypto_alias_and_format(self):
        with patch.object(publicdata, "request_with_retry",
                          return_value=FakeResp({"bitcoin": {"usd": 97500}})):
            report = publicdata.crypto_price("btc")
        self.assertIn("Bitcoin", report)
        self.assertIn("97,500", report)

    def test_country_normalization(self):
        self.assertEqual(publicdata._norm_country("india"), "IN")
        self.assertEqual(publicdata._norm_country("UK"), "GB")


class TestPendingTTL(unittest.TestCase):
    def setUp(self):
        shell._pending.clear()

    def test_fresh_pending_is_live(self):
        shell.stage_for_confirmation("ctx", "rm -rf /tmp/x", False)
        self.assertTrue(shell.has_pending("ctx"))

    def test_stale_pending_expires(self):
        shell.stage_for_confirmation("ctx", "rm -rf /tmp/x", False)
        cmd, elev, ts = shell._pending["ctx"]
        shell._pending["ctx"] = (cmd, elev, ts - 61)
        self.assertFalse(shell.has_pending("ctx"))
        self.assertNotIn("ctx", shell._pending)


if __name__ == "__main__":
    unittest.main()
