#!/usr/bin/env python3
"""Isolated stdlib-only tests for the public-site release installer."""

import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest import mock

from scripts import server_release as release


def make_archive(path, files=None, *, entries=None, source_sha=None, extra_members=()):
    files = files or {"index.html": b"<html>release</html>", "assets/site.css": b"body{}"}
    if entries is None:
        entries = [
            {"path": name, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
            for name, data in files.items()
        ]
    if source_sha is None:
        canonical = [
            {"path": entry["path"], "sha256": entry["sha256"].lower(), "size": entry["size"]}
            for entry in sorted(entries, key=lambda item: item["path"])
        ]
        source_sha = hashlib.sha256(json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
        ).encode()).hexdigest()
    manifest = json.dumps({"source_sha256": source_sha, "entries": entries}).encode()
    with tarfile.open(path, "w:gz") as archive:
        members = [("release-manifest.json", manifest)]
        members.extend((f"payload/{name}", data) for name, data in files.items())
        members.extend(extra_members)
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ReleaseManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / "site"
        self.root.mkdir()
        self.archive = self.base / "incoming.tar.gz"
        self.backups = self.base / "backups"
        self.digest = make_archive(self.archive)

    def tearDown(self):
        self.temp.cleanup()

    def manager(self, health_checker=None, uid=0):
        return release.ReleaseManager(
            root=self.root, archive_path=self.archive, backup_dir=self.backups,
            uid_getter=lambda: uid,
            health_checker=health_checker or (
                lambda root, payload: all(
                    root.joinpath(*name.split("/")).read_bytes() == data
                    for name, data in payload.items()
                )
            ),
        )

    def test_inspect_and_apply_are_allowlisted_and_preserve_private_data(self):
        private = self.root / "leads"
        private.mkdir()
        sentinel = private / "historical.jsonl"
        sentinel.write_bytes(b"DO NOT READ OR CHANGE")
        admin = self.root / "admin"
        admin.mkdir()
        (admin / "config.php").write_bytes(b"private config")
        index = self.root / "index.html"
        index.write_bytes(b"old homepage")
        os.chmod(index, 0o640)
        original_read_bytes = Path.read_bytes

        def deny_private_read(path):
            if path == private or path.is_relative_to(private) or path == admin or path.is_relative_to(admin):
                raise AssertionError("installer attempted to read private server data")
            return original_read_bytes(path)

        with mock.patch.object(Path, "read_bytes", deny_private_read):
            report = self.manager().inspect(self.digest)
            result = self.manager().apply(self.digest)
        self.assertEqual(report["files"], 2)
        self.assertEqual(result["operation"], "apply")
        self.assertEqual(index.read_bytes(), b"<html>release</html>")
        self.assertEqual(index.stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.root / "assets" / "site.css").read_bytes(), b"body{}")
        self.assertEqual(sentinel.read_bytes(), b"DO NOT READ OR CHANGE")
        self.assertEqual((admin / "config.php").read_bytes(), b"private config")
        run_dirs = list(self.backups.glob("run-*"))
        self.assertEqual(len(run_dirs), 1)
        self.assertEqual((run_dirs[0] / "files").stat().st_mode & 0o777, 0o700)
        backups = list((run_dirs[0] / "files").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.manager().apply(self.digest)["files"], 2)
        self.assertEqual(len(list(self.backups.glob("run-*/files/*"))), 1)
        self.assertEqual(sentinel.read_bytes(), b"DO NOT READ OR CHANGE")

    def test_digest_must_be_strict_and_match_archive(self):
        for invalid in ("", "1" * 63, "g" * 64):
            with self.subTest(invalid=invalid), self.assertRaises(release.ReleaseError):
                self.manager().inspect(invalid)
        with self.assertRaisesRegex(release.ReleaseError, "does not match"):
            self.manager().inspect("0" * 64)
        self.assertFalse((self.root / "index.html").exists())

    def test_manifest_and_archive_members_must_match_exactly(self):
        files = {"index.html": b"ok"}
        bad_entries = [{"path": "index.html", "sha256": "0" * 64, "size": 2}]
        self.digest = make_archive(self.archive, files, entries=bad_entries)
        with self.assertRaises(release.ReleaseError):
            self.manager().inspect(self.digest)

        self.digest = make_archive(
            self.archive, files,
            extra_members=[("payload/index.html", b"duplicate")],
        )
        with self.assertRaisesRegex(release.ReleaseError, "duplicate"):
            self.manager().inspect(self.digest)

    def test_rejects_traversal_private_and_dot_paths_before_writes(self):
        for unsafe in ("../leads/x", "admin/config.php", ".env", "assets/../index.html",
                       "assets/.secret", "/index.html", "assets\\file.css"):
            with self.subTest(unsafe=unsafe):
                self.digest = make_archive(
                    self.archive,
                    {"index.html": b"ok", unsafe: b"bad"},
                )
                with self.assertRaises(release.ReleaseError):
                    self.manager().apply(self.digest)
                self.assertFalse((self.root / "index.html").exists())

    def test_rejects_tar_links_and_unexpected_member_types(self):
        with tarfile.open(self.archive, "w:gz") as archive:
            link = tarfile.TarInfo("payload/assets/link")
            link.type = tarfile.SYMTYPE
            link.linkname = "/etc/passwd"
            archive.addfile(link)
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        with self.assertRaises(release.ReleaseError):
            self.manager().inspect(self.digest)

    def test_existing_target_symlink_and_hardlink_are_rejected(self):
        outside = self.base / "outside"
        outside.write_bytes(b"untouched")
        (self.root / "index.html").symlink_to(outside)
        with self.assertRaises(release.ReleaseError):
            self.manager().apply(self.digest)
        (self.root / "index.html").unlink()
        (self.root / "index.html").hardlink_to(outside)
        with self.assertRaisesRegex(release.ReleaseError, "single-link"):
            self.manager().apply(self.digest)
        self.assertEqual(outside.read_bytes(), b"untouched")

    def test_symlinked_root_ancestor_is_rejected(self):
        real = self.base / "real"
        real.mkdir()
        link = self.base / "root-link"
        link.symlink_to(real, target_is_directory=True)
        manager = release.ReleaseManager(link, self.archive, self.backups, uid_getter=lambda: 0)
        with self.assertRaisesRegex(release.ReleaseError, "ancestor"):
            manager.inspect(self.digest)

    def test_health_failure_rolls_back_overwrites_and_removes_new_files(self):
        (self.root / "index.html").write_bytes(b"old")

        def unhealthy(root, payload):
            return False

        with self.assertRaisesRegex(release.ReleaseError, "health check"):
            self.manager(unhealthy).apply(self.digest)
        self.assertEqual((self.root / "index.html").read_bytes(), b"old")
        self.assertFalse((self.root / "assets" / "site.css").exists())
        self.assertTrue((self.root / "assets").is_dir())

    def test_prewrite_concurrent_edit_is_not_overwritten(self):
        target = self.root / "index.html"
        target.write_bytes(b"original")
        original_fsync = os.fsync
        calls = []

        def edit_during_backup(fd):
            if not calls:
                calls.append(True)
                target.write_bytes(b"administrator edit")
            return original_fsync(fd)

        with mock.patch.object(release.os, "fsync", side_effect=edit_during_backup):
            with self.assertRaisesRegex(release.ReleaseError, "changed during release preparation"):
                self.manager().apply(self.digest)
        self.assertEqual(target.read_bytes(), b"administrator edit")
        self.assertFalse((self.root / "assets" / "site.css").exists())

    def test_non_root_cannot_apply_but_can_inspect(self):
        manager = self.manager(uid=1234)
        self.assertEqual(manager.inspect(self.digest)["operation"], "inspect")
        with self.assertRaisesRegex(release.ReleaseError, "requires root"):
            manager.apply(self.digest)

    def test_manifest_source_hash_is_canonical_entries_fingerprint(self):
        data = b"homepage"
        files = {"index.html": data}
        entries = [{
            "path": "index.html", "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
        }]
        self.digest = make_archive(self.archive, files, entries=entries, source_sha="f" * 64)
        with self.assertRaisesRegex(release.ReleaseError, "canonical entries"):
            self.manager().inspect(self.digest)


class PublicHealthTests(unittest.TestCase):
    def test_real_urllib_http_errors_keep_status_and_headers(self):
        class ErrorOpener:
            def open(_, request, timeout):
                raise release.urllib.error.HTTPError(
                    request.full_url, 302, "redirect",
                    {"Location": "/prosfora/"}, io.BytesIO(b""),
                )
        checker = release.PublicHealthChecker(opener=ErrorOpener())
        status, headers, body = checker._request("HEAD", "/lead.php")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], "/prosfora/")
        self.assertEqual(body, b"")

    class Response:
        def __init__(self, status, headers=None, body=b""):
            self.status = status
            self.headers = headers or {}
            self.body = body

        def getcode(self):
            return self.status

        def read(self, size=-1):
            return self.body[:size]

        def close(self):
            pass

    def test_health_gate_uses_only_required_public_get_and_head_routes(self):
        calls = []

        class FakeOpener:
            def open(_, request, timeout):
                method = request.get_method()
                path = request.full_url.removeprefix("https://codehouse.gr")
                calls.append((method, path, timeout))
                if path.startswith("/?"):
                    return PublicHealthTests.Response(
                        200, body=b'<img src="assets/studio/logo-user-white.png">'
                    )
                if path == "/lead.php":
                    return PublicHealthTests.Response(302, {"Location": "/prosfora/"})
                redirects = {
                    "/dimiourgia-site/": "https://codehouse.gr/dimioyrgia-site/",
                    "/blog/checklist-dorean-istoselida/":
                        "https://codehouse.gr/blog/checklist-dorean-istoselida-epixeirisi/",
                }
                if path in redirects:
                    return PublicHealthTests.Response(301, {"Location": redirects[path]})
                if path in ("/.git/HEAD", "/replit.md"):
                    return PublicHealthTests.Response(404)
                return PublicHealthTests.Response(200)

        checker = release.PublicHealthChecker(
            opener=FakeOpener(), sleep=lambda _: self.fail("unexpected retry"),
            nonce_factory=lambda: "cache-buster",
        )
        self.assertTrue(checker(Path("/unused"), {}))
        self.assertEqual([method for method, _, _ in calls],
                     ["GET"] + ["HEAD"] * 8)
        self.assertTrue(calls[0][1].startswith("/?release_check=cache-buster"))
        self.assertEqual([path for _, path, _ in calls[1:]],
                         ["/assets/studio/studio.css", "/contact/", "/blog/",
                          "/lead.php", "/dimiourgia-site/",
                          "/blog/checklist-dorean-istoselida/", "/.git/HEAD", "/replit.md"])


if __name__ == "__main__":
    unittest.main()