#!/usr/bin/env python3
"""Exercise the release gate without GitHub credentials or server access."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = Path(os.environ.get(
    "RELEASE_WORKFLOW_PATH", ROOT / ".github/workflows/deploy.yml",
))
BASH = shutil.which("bash")
SHA = "f1f5360b483ca9e76ef16b04495c5843c9206426"


def shell_blocks(text):
    blocks = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line == "        run: |":
            block = []
            for following in lines[index + 1:]:
                if following.startswith("          "):
                    block.append(following[10:])
                elif not following:
                    block.append("")
                else:
                    break
            blocks.append("\n".join(block))
    return blocks


class ReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text()
        cls.blocks = shell_blocks(cls.text)
        cls.gate = cls.blocks[0]

    def gate_result(self, requested="", approved=SHA, operation="apply", api_exit=0):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            gh = path / "gh"
            gh.write_text(
                f"#!{BASH}\n"
                'printf "%s\\n" "$*" >> "$STUB_LOG"\n'
                'if [[ "$STUB_EXIT" != 0 ]]; then exit "$STUB_EXIT"; fi\n'
                'printf "%s\\n" "$STUB_SHA"\n'
            )
            gh.chmod(0o700)
            output = path / "output"
            log = path / "api-log"
            # No inherited credentials, networking, or SSH access in these tests.
            environment = {
                "PATH": temporary,
                "GITHUB_REPOSITORY": "codehouse-products/codehouse.gr",
                "GITHUB_OUTPUT": str(output),
                "SITE_COMMIT": requested,
                "SITE_OPERATION": operation,
                "STUB_SHA": approved,
                "STUB_EXIT": str(api_exit),
                "STUB_LOG": str(log),
            }
            result = subprocess.run(
                [BASH, "-c", self.gate], env=environment,
                capture_output=True, text=True, timeout=5,
            )
            return (
                result.returncode,
                output.read_text() if output.exists() else "",
                log.read_text() if log.exists() else "",
            )

    def test_blank_input_resolves_latest_reviewed_version(self):
        for operation in ("inspect", "apply"):
            code, output, log = self.gate_result(operation=operation)
            self.assertEqual(code, 0)
            self.assertEqual(output, f"commit={SHA}\n")
            self.assertIn(
                "api --method GET repos/codehouse-products/codehouse.gr/"
                "git/ref/heads/releases/reviewed-public --jq .object.sha", log,
            )

    def test_explicit_reviewed_commit_is_accepted(self):
        code, output, _ = self.gate_result(requested=SHA)
        self.assertEqual(code, 0)
        self.assertEqual(output, f"commit={SHA}\n")

    def test_future_release_needs_no_workflow_edit(self):
        newer = "a" * 40
        code, output, _ = self.gate_result(requested=newer, approved=newer)
        self.assertEqual(code, 0)
        self.assertEqual(output, f"commit={newer}\n")
        self.assertNotIn(SHA, self.text)

    def test_unreviewed_or_stale_commit_is_rejected(self):
        code, output, _ = self.gate_result(requested="b" * 40)
        self.assertNotEqual(code, 0)
        self.assertEqual(output, "")

    def test_malformed_and_injected_inputs_never_call_api(self):
        for requested in (
            "main", "releases/reviewed-public", SHA.upper(), "a" * 39,
            "a" * 41, "$(exit 0)", SHA + "\ncommit=bad", SHA + "; exit 0",
        ):
            with self.subTest(requested=requested):
                code, output, log = self.gate_result(requested=requested)
                self.assertNotEqual(code, 0)
                self.assertEqual(output, "")
                self.assertEqual(log, "")

    def test_invalid_operation_never_calls_api(self):
        code, output, log = self.gate_result(operation="delete")
        self.assertNotEqual(code, 0)
        self.assertEqual(output, "")
        self.assertEqual(log, "")

    def test_missing_or_malformed_reference_fails_closed(self):
        for approved in ("", "main", "a" * 39, SHA + "\ncommit=bad"):
            code, output, _ = self.gate_result(approved=approved)
            self.assertNotEqual(code, 0)
            self.assertEqual(output, "")
        code, output, _ = self.gate_result(api_exit=1)
        self.assertNotEqual(code, 0)
        self.assertEqual(output, "")

    def test_workflow_keeps_existing_release_safeguards(self):
        self.assertIn(
            "ref: decbc1d46f76f56463f6c101b919edc04177c72e\n"
            "          path: ops", self.text,
        )
        self.assertIn(
            "ref: ${{ steps.review.outputs.commit }}\n"
            "          path: site", self.text,
        )
        self.assertIn(
            "SITE_RELEASE_COMMIT: ${{ steps.review.outputs.commit }}", self.text,
        )
        self.assertIn('--commit "$SITE_RELEASE_COMMIT"', self.text)
        self.assertIn("default: inspect", self.text)
        self.assertIn("cancel-in-progress: false", self.text)
        self.assertIn("contents: read", self.text)
        self.assertIn("rm: false", self.text)
        self.assertIn("python3 scripts/test_contact_intro.py", self.text)
        self.assertEqual(self.text.count("persist-credentials: false"), 2)
        triggers = self.text.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
        self.assertNotRegex(triggers, r"(?m)^  (push|pull_request):")
        self.assertNotRegex(self.text, r"git reset|rsync.*--delete")
        # User inputs belong in environment values, never executable shell text.
        self.assertFalse(any("${{ inputs." in block for block in self.blocks))

    def test_all_shell_blocks_parse(self):
        self.assertEqual(len(self.blocks), 3)
        for block in self.blocks:
            result = subprocess.run(
                [BASH, "-n", "-c", block], capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()