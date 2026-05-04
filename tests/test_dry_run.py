"""End-to-end dry-run test for scripts/orchestrate.py."""
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class TestOrchestrateDryRun(unittest.TestCase):
    def setUp(self):
        self.result = subprocess.run(
            [sys.executable, "scripts/orchestrate.py", "--dry-run", "--duration", "10"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_exit_code_zero(self):
        self.assertEqual(
            self.result.returncode,
            0,
            msg=f"stdout:\n{self.result.stdout}\nstderr:\n{self.result.stderr}",
        )

    def test_all_eight_stages_mentioned(self):
        out = self.result.stdout
        for n in range(1, 9):
            self.assertIn(f"Stage {n}", out, msg=f"missing 'Stage {n}' in stdout:\n{out}")

    def test_at_least_one_model_slug_mentioned(self):
        out = self.result.stdout
        slugs = ("google/nano-banana-pro", "kling-video/v2.1/pro/image-to-video")
        self.assertTrue(
            any(s in out for s in slugs),
            msg=f"no expected model slug found in stdout:\n{out}",
        )


if __name__ == "__main__":
    unittest.main()
