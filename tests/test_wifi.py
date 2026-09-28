import unittest

import wifi


SAMPLE_NETSH = """Interface name : Wi-Fi

There are 2 networks currently visible.

SSID 1 : HomeNet
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    Signal                  : 85%
    Radio type              : 802.11n
    Channel                 : 6

SSID 2 : CafeFree
    Network type            : Infrastructure
    Authentication          : Open
    Signal                  : 42%
    Radio type              : 802.11g
    Channel                 : 11
"""


class TestWifiParse(unittest.TestCase):
    def test_parse_two_networks(self):
        nets = wifi.parse_networks(SAMPLE_NETSH)
        self.assertEqual(len(nets), 2)
        self.assertEqual(nets[0]["ssid"], "HomeNet")
        self.assertEqual(nets[1]["channel"], "11")

    def test_signal_sort(self):
        nets = wifi.parse_networks(SAMPLE_NETSH)
        self.assertGreater(wifi._signal_pct(nets[0]), wifi._signal_pct(nets[1]))

    def test_empty_output(self):
        self.assertEqual(wifi.parse_networks("No networks found."), [])

    def test_hidden_ssid(self):
        nets = wifi.parse_networks("SSID 1 : \n    Signal                  : 60%\n")
        self.assertEqual(nets[0]["ssid"], "(hidden)")


if __name__ == "__main__":
    unittest.main()
