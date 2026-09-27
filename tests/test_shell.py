import sys
import unittest

import shell


class TestDestructivePatterns(unittest.TestCase):
    def test_catches_classic_patterns(self):
        for cmd in ["rm -rf /", "format c:", "shutdown now", "diskpart",
                    "dd if=/dev/zero of=/dev/sda", "reboot"]:
            self.assertTrue(shell.needs_confirmation(cmd), msg=cmd)

    def test_catches_widened_patterns(self):
        for cmd in ["python -c \"import shutil; shutil.rmtree('/home')\"",
                    "Remove-Item -Recurse -Force C:\\Users\\me\\Documents",
                    "rm -r --force /var/log"]:
            self.assertTrue(shell.needs_confirmation(cmd), msg=cmd)

    def test_leaves_ordinary_commands_alone(self):
        for cmd in ["ipconfig /all", "git status", "ls -la", "echo hello",
                    "npm install", "dir"]:
            self.assertFalse(shell.needs_confirmation(cmd), msg=cmd)


class TestPendingIsolation(unittest.TestCase):
    """Regression test for the fix: pending confirmations must be scoped
    per-context so one browser tab/session can't clobber or confirm
    another's staged destructive command."""

    def setUp(self):
        shell._pending.clear()

    def test_separate_contexts_dont_collide(self):
        shell.stage_for_confirmation("tab-a", "rm -rf /tmp/a", False)
        shell.stage_for_confirmation("tab-b", "shutdown now", True)

        self.assertTrue(shell.has_pending("tab-a"))
        self.assertTrue(shell.has_pending("tab-b"))

        cmd_a, elevate_a = shell.pop_pending("tab-a")
        self.assertEqual(cmd_a, "rm -rf /tmp/a")
        self.assertFalse(elevate_a)

        # popping tab-a must not have touched tab-b
        self.assertFalse(shell.has_pending("tab-a"))
        self.assertTrue(shell.has_pending("tab-b"))

        cmd_b, elevate_b = shell.pop_pending("tab-b")
        self.assertEqual(cmd_b, "shutdown now")
        self.assertTrue(elevate_b)

    def test_pop_on_empty_context_is_safe(self):
        cmd, elevate = shell.pop_pending("nonexistent")
        self.assertIsNone(cmd)
        self.assertFalse(elevate)


class TestRunHarmless(unittest.TestCase):
    """Actually executes shell.run() (not just syntax-checks it) with a
    harmless, cross-platform-safe command."""

    def test_run_echo(self):
        output = shell.run("echo hello-from-47-tests")
        self.assertIn("hello-from-47-tests", output)

    def test_run_timeout(self):
        import tempfile
        import os as _os
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write("import time; time.sleep(5)")
            script = f.name
        try:
            output = shell.run(f"{sys.executable} {script}", timeout=1)
            self.assertIn("timed out", output.lower())
        finally:
            try:
                _os.remove(script)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
