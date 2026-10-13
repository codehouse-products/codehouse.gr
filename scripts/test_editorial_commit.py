#!/usr/bin/env python3
"""Exercise narrow Git writes using a local bare remote and synthetic credentials."""
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from editorial_commit import commit


class CommitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.remote = self.root / "remote.git"
        self.source.mkdir()
        self.run_git(self.source, "init", "-q")
        self.run_git(self.source, "config", "user.name", "Synthetic test")
        self.run_git(self.source, "config", "user.email", "test@example.invalid")
        self.run_git(self.root, "init", "--bare", "-q", str(self.remote))
        self.run_git(self.source, "remote", "add", "origin", str(self.remote))
        for path, text in {
            "blog/index.html": "original blog",
            "sitemap.xml": "original sitemap",
            "editorial/published.json": "[]",
            "admin/index.php": "unchanged existing admin",
        }.items():
            self.write(path, text)
        self.run_git(self.source, "add", ".")
        self.run_git(self.source, "commit", "-qm", "Base")
        self.expected = self.run_git(self.source, "rev-parse", "HEAD")
        self.run_git(self.source, "push", "-q", "origin", "HEAD:refs/heads/releases/reviewed-public")
        self.report = {"slug": "reviewed-test-article", "changed": sorted({
            "blog/index.html", "sitemap.xml", "editorial/published.json",
            "blog/reviewed-test-article/index.html",
        })}

    def tearDown(self):
        self.temp.cleanup()

    def run_git(self, path, *args):
        return subprocess.check_output(["git", "-C", str(path), *args],
                                       text=True, stderr=subprocess.DEVNULL).strip()

    def write(self, path, text):
        target = self.source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def prepare(self):
        self.write("blog/index.html", "new card")
        self.write("sitemap.xml", "new URL")
        self.write("blog/reviewed-test-article/index.html", "new article")
        self.write("editorial/published.json", json.dumps([{
            "slug": self.report["slug"], "status": "pending", "date": "2026-10-14",
            "published_at": "2026-10-14T10:00:00+03:00"
        }]))

    def api(self, *_args, **_kwargs):
        sha = self.run_git(self.remote, "rev-parse", "refs/heads/releases/reviewed-public")
        return io.BytesIO(json.dumps({"object": {"sha": sha}}).encode())

    @contextmanager
    def connection(self):
        with patch.dict(os.environ, {"GH_TOKEN": "synthetic-test-value",
                                      "GITHUB_REPOSITORY": "codehouse-products/codehouse.gr"}):
            with patch("editorial_commit.urllib.request.urlopen", side_effect=self.api):
                yield

    def test_article_commit_changes_only_four_paths(self):
        self.prepare()
        with self.connection():
            sha = commit(self.source, self.report, self.expected)
        self.assertNotEqual(sha, self.expected)
        changed = self.run_git(self.source, "diff", "--name-only", self.expected, sha).splitlines()
        self.assertEqual(changed, self.report["changed"])
        self.assertEqual((self.source / "admin/index.php").read_text(), "unchanged existing admin")

    def test_unexpected_admin_change_refused(self):
        self.prepare()
        self.write("admin/index.php", "unapproved change")
        with self.connection(), self.assertRaises(RuntimeError):
            commit(self.source, self.report, self.expected)
        self.assertEqual(self.run_git(self.remote, "rev-parse", "refs/heads/releases/reviewed-public"),
                         self.expected)

    def test_confirmation_changes_only_nonpublic_history(self):
        self.prepare()
        with self.connection():
            article_sha = commit(self.source, self.report, self.expected)
            confirmed_sha = commit(self.source, self.report, article_sha, acknowledgment=True)
        changed = self.run_git(self.source, "diff", "--name-only", article_sha, confirmed_sha)
        self.assertEqual(changed, "editorial/published.json")
        self.assertEqual(json.loads((self.source / changed).read_text())[-1]["status"], "published")

    def test_incomplete_publication_refused(self):
        self.prepare()
        (self.source / "blog/reviewed-test-article/index.html").unlink()
        with self.connection(), self.assertRaises(RuntimeError):
            commit(self.source, self.report, self.expected)

    def test_stale_reviewed_ref_refused(self):
        self.prepare()
        with self.connection():
            with patch("editorial_commit.urllib.request.urlopen",
                       return_value=io.BytesIO(json.dumps({"object": {"sha": "f" * 40}}).encode())):
                with self.assertRaises(RuntimeError):
                    commit(self.source, self.report, self.expected)
        self.assertEqual(self.run_git(self.source, "rev-parse", "HEAD"), self.expected)


if __name__ == "__main__":
    unittest.main()
