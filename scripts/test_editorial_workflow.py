#!/usr/bin/env python3
"""Static workflow checks without importing YAML or contacting Actions."""
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent.parent


class WorkflowTests(unittest.TestCase):
    def test_schedule_timezone_safety_and_shell_syntax(self):
        text = (ROOT / "deployment/daily-editorial-workflow.yml").read_text()
        self.assertIn("cron: '0 10 * * *'", text)
        self.assertIn("cron: '30 10 * * *'", text)
        self.assertEqual(text.count("timezone: Europe/Athens"), 2)
        self.assertIn("group: codehouse-server-maintenance", text)
        self.assertIn("cancel-in-progress: false", text)
        self.assertIn("default: inspect", text)
        self.assertIn("SITE_RELEASE_OPERATION=inspect", text)
        self.assertIn("--acknowledge", text)
        self.assertIn("contents: write", text)
        self.assertNotIn("actions: write", text)
        self.assertNotIn("push:", text)
        checkout_refs = re.findall(r"\n          ref: (.+)", text)
        self.assertTrue(all(re.fullmatch("[0-9a-f]{40}", ref) or ref.startswith("${{")
                            for ref in checkout_refs))
        self.assertEqual(text.count("persist-credentials: false"), 3)
        self.assertEqual(text.count("source: upload/*"), 1)
        self.assertIn("target: /var/lib/codehouse-release-incoming", text)
        self.assertIn("rm: false", text)
        blocks = re.findall(r"\n        run: \|\n(.*?)(?=\n      -|\Z)", text, re.S)
        for block in blocks:
            # Treat workflow expressions as inert values when checking Bash syntax.
            shell = "\n".join(line[10:] for line in block.splitlines()) + "\n"
            shell = re.sub(r"\$\{\{.*?\}\}", "verified_value", shell)
            result = subprocess.run(["bash", "-n"], input=shell, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreaterEqual(len(blocks), 5)


if __name__ == "__main__":
    unittest.main()
