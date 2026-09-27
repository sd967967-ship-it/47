import os
import tempfile
import unittest
from pathlib import Path

import audit
import prompts


class TestAudit(unittest.TestCase):
    def test_record_and_read_roundtrip(self):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        os.close(fd)
        orig = audit.AUDIT_PATH
        audit.AUDIT_PATH = Path(path)
        try:
            audit.record("test.event", detail="x")
            entries = audit.read(limit=10)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["event"], "test.event")
            self.assertIn("ts", entries[0])
        finally:
            audit.AUDIT_PATH = orig
            os.remove(path)

    def test_record_never_raises(self):
        orig = audit.AUDIT_PATH
        audit.AUDIT_PATH = Path("/nonexistent-dir-47/audit.jsonl")
        try:
            audit.record("test.event")  # must not raise
        finally:
            audit.AUDIT_PATH = orig


class TestPrompts(unittest.TestCase):
    def test_research_guide_has_sections(self):
        guide = prompts.research_guide()
        self.assertIn("Research", guide)

    def test_fix_guide_has_sections(self):
        guide = prompts.fix_guide()
        self.assertIn("Bug", guide)


if __name__ == "__main__":
    unittest.main()
