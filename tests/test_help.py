import os
import unittest

import help_catalog


class TestHelpCatalog(unittest.TestCase):
    def test_groups_nonempty(self):
        self.assertGreaterEqual(len(help_catalog.GROUPS), 5)
        for group in help_catalog.GROUPS:
            self.assertTrue(group["title"])
            self.assertTrue(group["items"])
            for item in group["items"]:
                self.assertTrue(item["triggers"])
                self.assertTrue(item["example"])

    def test_text_render(self):
        text = help_catalog.as_text()
        for word in ("play <song>", "confirm", "quiz me on", "brain status"):
            self.assertIn(word, text)

    def test_api_route_gated(self):
        import main
        orig = main.DASHBOARD_TOKEN
        main.DASHBOARD_TOKEN = "test-token-help"
        try:
            client = main.app.test_client()
            self.assertEqual(client.get("/api/commands").status_code, 403)
            resp = client.get("/api/commands?token=test-token-help")
            self.assertEqual(resp.status_code, 200)
            groups = resp.get_json()["groups"]
            self.assertGreaterEqual(len(groups), 5)
        finally:
            main.DASHBOARD_TOKEN = orig

    def test_api_chat_validation_and_flow(self):
        import main
        orig = main.DASHBOARD_TOKEN
        main.DASHBOARD_TOKEN = "test-token-chat"
        try:
            client = main.app.test_client()
            self.assertEqual(client.post("/api/chat").status_code, 403)
            self.assertEqual(client.post("/api/chat?token=test-token-chat",
                                         json={}).status_code, 400)
            from unittest.mock import patch
            hist = [[("user", "hello")], [("user", "hello"), ("assistant", "stubbed reply")]]
            with patch.object(main, "handle_command") as hc, \
                 patch.object(main.memory, "recent_history", side_effect=hist):
                resp = client.post("/api/chat?token=test-token-chat",
                                   json={"text": "hello"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()["reply"], "stubbed reply")
            hc.assert_called_once_with("hello", context_id="web")
        finally:
            main.DASHBOARD_TOKEN = orig


if __name__ == "__main__":
    unittest.main()
