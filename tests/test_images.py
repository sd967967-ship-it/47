import base64
import unittest
from unittest.mock import patch

import actions


COMMONS_FIXTURE = {
    "query": {"pages": {"1": {
        "title": "File:Red Fort Delhi.jpg",
        "imageinfo": [{
            "thumburl": "https://upload.wikimedia.org/thumb/x.jpg",
            "descriptionurl": "https://commons.wikimedia.org/wiki/File:X",
            "extmetadata": {"ImageDescription": {"value": "<p>Mughal <b>fort</b> in Delhi</p>"}},
        }],
    }}}
}

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


class FakeResp:
    def __init__(self, payload=None, content=b"", ctype="image/png"):
        self._payload = payload
        self.content = content
        self.headers = {"Content-Type": ctype}

    def json(self):
        return self._payload


class TestEnquiryImages(unittest.TestCase):
    def test_parse_strips_html(self):
        items = actions._parse_commons_pages(COMMONS_FIXTURE)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Red Fort Delhi")
        self.assertIn("Mughal fort in Delhi", items[0]["desc"])
        self.assertNotIn("<p>", items[0]["desc"])

    def test_fetch_returns_data_urls(self):
        def fake_get(method, url, **kw):
            if "commons.wikimedia.org" in url:
                return FakeResp(payload=COMMONS_FIXTURE)
            return FakeResp(content=TINY_PNG)

        with patch.object(actions, "request_with_retry", side_effect=fake_get):
            images, note = actions.fetch_enquiry_images("red fort", count=1)
        self.assertEqual(note, "")
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0]["data_url"].startswith("data:image/png;base64,"))

    def test_rejects_non_images(self):
        def fake_get(method, url, **kw):
            if "commons.wikimedia.org" in url:
                return FakeResp(payload=COMMONS_FIXTURE)
            return FakeResp(content=b"<html>nope</html>", ctype="text/html")

        with patch.object(actions, "request_with_retry", side_effect=fake_get):
            images, note = actions.fetch_enquiry_images("red fort", count=1)
        self.assertEqual(images, [])
        self.assertIn("No usable photos", note)


if __name__ == "__main__":
    unittest.main()
