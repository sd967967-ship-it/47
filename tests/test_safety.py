import os
import tempfile
import unittest

import shell


class TestSafetyYaml(unittest.TestCase):
    def test_builtin_patterns_still_caught(self):
        self.assertTrue(shell.needs_confirmation("rm -rf /"))

    def test_extra_pattern_from_custom_file(self):
        fd, path = tempfile.mkstemp(suffix=".yaml")
        with os.fdopen(fd, "w") as f:
            f.write("confirm_before:\n  - \"\\bcustomdanger\\b\"\n")
        try:
            self.assertTrue(shell.needs_confirmation("run customdanger now", safety_path=path))
            self.assertFalse(shell.needs_confirmation("run harmless now", safety_path=path))
        finally:
            os.remove(path)

    def test_missing_file_falls_back_to_builtins(self):
        self.assertFalse(shell.needs_confirmation("echo hello", safety_path="/nonexistent-47.yaml"))

    def test_shipped_safety_yaml_catches_vssadmin(self):
        default = os.path.join(os.path.dirname(shell.__file__), "safety.yaml")
        self.assertTrue(shell.needs_confirmation("vssadmin delete shadows", safety_path=default))


if __name__ == "__main__":
    unittest.main()
