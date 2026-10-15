"""Packaging tests that never read historical data or call a production server."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_site_release import build
from server_release import ReleaseError


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "site"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        for name, content in {"index.html": "new homepage", "lead.php": "<?php",
                              "assets/studio/test.css": "css", "admin/index.php": "private",
                              "leads/test.jsonl": "never package", ".env": "never package"}.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)
        subprocess.run(["git", "-C", str(self.root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.root), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid", "commit", "-qm", "fixture"],
                       check=True)
        self.commit = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True).strip()

    def tearDown(self):
        self.temp.cleanup()

    def test_public_only_and_reproducible(self):
        one = Path(self.temp.name) / "one.gz"
        two = Path(self.temp.name) / "two.gz"
        report = build(self.root, one, self.commit)
        build(self.root, two, self.commit)
        self.assertEqual(one.read_bytes(), two.read_bytes())
        self.assertEqual(report["files"], 3)
        self.assertEqual(report["archive_sha256"], hashlib.sha256(one.read_bytes()).hexdigest())
        with tarfile.open(one) as archive:
            manifest = json.load(archive.extractfile("release-manifest.json"))
            names = {entry["path"] for entry in manifest["entries"]}
        self.assertEqual(names, {"index.html", "lead.php", "assets/studio/test.css"})

    def test_modified_worktree_is_rejected(self):
        (self.root / "index.html").write_text("unreviewed")
        with self.assertRaises(ReleaseError):
            build(self.root, Path(self.temp.name) / "bad.gz", self.commit)

    def test_wrong_commit_is_rejected(self):
        with self.assertRaises(ReleaseError):
            build(self.root, Path(self.temp.name) / "bad.gz", "0" * 40)

    def test_symlink_is_rejected(self):
        target = self.root / "index.html"
        target.unlink()
        target.symlink_to(self.root / "leads/test.jsonl")
        with self.assertRaises(ReleaseError):
            build(self.root, Path(self.temp.name) / "bad.gz", self.commit)


if __name__ == "__main__":
    unittest.main()