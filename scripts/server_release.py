#!/usr/bin/env python3
"""Verify and safely apply a narrowly allowlisted static-site release."""

import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request


ROOT = "/home/websites/artivoai.com"
ARCHIVE = "/var/lib/codehouse-release-incoming/site-release.tar.gz"
BACKUP_DIR = "/var/backups/codehouse-releases"
PUBLIC_DIRS = frozenset({
    "assets", "blog", "en", "projects", "douleies", "contact", "prosfora",
    "aporrito", "services", "studio", "dimioyrgia-site", "dimiourgia-site",
    "dorean-istoselida", "kataskevi-eshop", "seo", "qr-menu",
})
PUBLIC_FILES = frozenset({"index.html", "lead.php", "robots.txt", "sitemap.xml", "favicon.ico"})
MAX_BYTES = 512 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class ReleaseError(Exception):
    """A release could not be verified or applied safely."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ReleaseError("manifest contains duplicate object keys")
        result[key] = value
    return result


def _sha256(value, label):
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise ReleaseError(f"{label} must be exactly 64 hexadecimal characters")
    return value.lower()


def _entries_fingerprint(entries):
    canonical = [
        {
            "path": entry["path"],
            "sha256": _sha256(entry["sha256"], "manifest entry sha256"),
            "size": entry["size"],
        }
        for entry in sorted(entries, key=lambda item: item["path"])
    ]
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


class PublicHealthChecker:
    """Check the public deployment endpoints without following redirects."""

    BASE_URL = "https://codehouse.gr"
    TIMEOUT = 4
    ATTEMPTS = 3
    MAX_HOMEPAGE_BYTES = 2 * 1024 * 1024

    def __init__(self, opener=None, sleep=time.sleep, nonce_factory=None):
        self.opener = opener or urllib.request.build_opener(_NoRedirect())
        self.sleep = sleep
        self.nonce_factory = nonce_factory or (lambda: f"{time.time_ns()}-{os.getpid()}")

    def _request(self, method, path, read_body=False):
        request = urllib.request.Request(self.BASE_URL + path, method=method)
        try:
            response = self.opener.open(request, timeout=self.TIMEOUT)
        except urllib.error.HTTPError as error:
            # Exception-target variables are cleared after the except block.
            response = error
        except (urllib.error.URLError, OSError) as exc:
            raise ReleaseError("public site health request failed") from exc
        try:
            status = getattr(response, "status", response.getcode())
            headers = response.headers
            body = response.read(self.MAX_HOMEPAGE_BYTES + 1) if read_body else b""
            return status, headers, body
        finally:
            response.close()

    def _check_once(self):
        query = urllib.parse.urlencode({"release_check": self.nonce_factory()})
        status, _, body = self._request("GET", f"/?{query}", read_body=True)
        marker = b"assets/studio/logo-user-white.png"
        if status != 200 or len(body) > self.MAX_HOMEPAGE_BYTES or marker not in body:
            raise ReleaseError("public homepage health check failed")
        for path in ("/assets/studio/studio.css", "/contact/", "/blog/"):
            status, _, _ = self._request("HEAD", path)
            if status != 200:
                raise ReleaseError("public page health check failed")
        status, headers, _ = self._request("HEAD", "/lead.php")
        location = headers.get("Location", "") if headers else ""
        if status not in (302, 303) or urllib.parse.urlsplit(location).path != "/prosfora/":
            raise ReleaseError("public lead endpoint health check failed")
        for path, destination in (
                ("/dimiourgia-site/", "https://codehouse.gr/dimioyrgia-site/"),
                ("/blog/checklist-dorean-istoselida/",
                 "https://codehouse.gr/blog/checklist-dorean-istoselida-epixeirisi/")):
            status, headers, _ = self._request("HEAD", path)
            location = headers.get("Location", "") if headers else ""
            if status != 301 or urllib.parse.urljoin(self.BASE_URL, location) != destination:
                raise ReleaseError("public canonical redirect health check failed")
        for path in ("/.git/HEAD", "/replit.md"):
            status, _, _ = self._request("HEAD", path)
            if status != 404:
                raise ReleaseError("public privacy health check failed")

    def __call__(self, root, payload):
        for name, data in payload.items():
            path = root.joinpath(*PurePosixPath(name).parts)
            try:
                if path.read_bytes() != data:
                    raise ReleaseError("release health check failed")
            except OSError as exc:
                raise ReleaseError("release health check failed") from exc
        last_error = None
        for attempt in range(self.ATTEMPTS):
            try:
                self._check_once()
                return True
            except ReleaseError as exc:
                last_error = exc
                if attempt + 1 < self.ATTEMPTS:
                    self.sleep(1)
        raise ReleaseError("public site health gate did not pass") from last_error


def _safe_relative(path):
    if (not isinstance(path, str) or not path or len(path) > 512
            or "\\" in path or "\x00" in path or path.startswith("/")):
        raise ReleaseError("archive contains an unsafe path")
    parts = path.split("/")
    if any(part in ("", ".", "..") or part.startswith(".") for part in parts):
        raise ReleaseError("archive contains an unsafe path")
    if any(not re.fullmatch(r"[A-Za-z0-9_-][A-Za-z0-9._-]*", part) for part in parts):
        raise ReleaseError("archive contains an unsupported path")
    if len(parts) == 1:
        if path not in PUBLIC_FILES:
            raise ReleaseError("release contains a path outside the public allowlist")
    elif parts[0] not in PUBLIC_DIRS:
        raise ReleaseError("release contains a path outside the public allowlist")
    return path


def _validate_root(root):
    """Check every root ancestor using lstat without following links."""
    path = Path(os.path.abspath(os.fspath(root)))
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        try:
            info = current.lstat()
        except OSError as exc:
            raise ReleaseError("site root or an ancestor is unavailable") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ReleaseError("site root or an ancestor is not a real directory")
    return path


def _validate_parent(root, relative, create=False):
    current = root
    for part in PurePosixPath(relative).parts[:-1]:
        current = current / part
        try:
            info = current.lstat()
        except FileNotFoundError:
            if not create:
                continue
            try:
                current.mkdir(mode=0o755)
            except FileExistsError:
                pass
            info = current.lstat()
        except OSError as exc:
            raise ReleaseError("cannot safely inspect a public target directory") from exc
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ReleaseError("a public target parent is not a real directory")


def _target_snapshot(root, relative):
    _validate_parent(root, relative)
    path = root.joinpath(*PurePosixPath(relative).parts)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ReleaseError("cannot safely inspect a public target") from exc
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ReleaseError("an existing public target is not a single-link regular file")
    try:
        content = path.read_bytes()
    except OSError as exc:
        raise ReleaseError("cannot safely read an existing public target") from exc
    after = path.lstat()
    if (not stat.S_ISREG(after.st_mode) or after.st_nlink != 1
            or (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino)):
        raise ReleaseError("a public target changed while being inspected")
    return {
        "content": content,
        "mode": stat.S_IMODE(info.st_mode),
        "uid": info.st_uid,
        "gid": info.st_gid,
        "dev": info.st_dev,
        "ino": info.st_ino,
    }


def _metadata_matches(path, snapshot, content):
    try:
        info = path.lstat()
        return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and info.st_dev == snapshot["dev"] and info.st_ino == snapshot["ino"]
                and stat.S_IMODE(info.st_mode) == snapshot["mode"]
                and info.st_uid == snapshot["uid"] and info.st_gid == snapshot["gid"]
                and path.read_bytes() == content)
    except OSError:
        return False


def _atomic_write(path, content, mode, uid, gid):
    fd, temporary = tempfile.mkstemp(prefix=".site-release-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, uid, gid)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ReleaseManager:
    def __init__(self, root=ROOT, archive_path=ARCHIVE, backup_dir=BACKUP_DIR,
                 uid_getter=os.geteuid, health_checker=None, before_health=None,
                 rollback_hook=None):
        self.root = Path(root)
        self.archive_path = Path(archive_path)
        self.backup_dir = Path(backup_dir)
        self.uid_getter = uid_getter
        self.health_checker = health_checker or PublicHealthChecker()
        self.before_health = before_health
        self.rollback_hook = rollback_hook

    def _load_release(self, expected_digest):
        expected_digest = _sha256(expected_digest, "SITE_RELEASE_SHA256")
        stream = None
        try:
            fd = os.open(self.archive_path, os.O_RDONLY | os.O_NOFOLLOW)
            stream = os.fdopen(fd, "rb")
            archive_info = os.fstat(stream.fileno())
            if not stat.S_ISREG(archive_info.st_mode) or archive_info.st_nlink != 1:
                raise ReleaseError("release archive must be a single-link regular file")
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != expected_digest:
                raise ReleaseError("release archive SHA256 does not match SITE_RELEASE_SHA256")
            if self.archive_path.lstat().st_ino != archive_info.st_ino:
                raise ReleaseError("release archive changed during verification")
            stream.seek(0)
            with tarfile.open(fileobj=stream, mode="r:gz") as archive:
                members = archive.getmembers()
                if not members or len(members) > 100000:
                    raise ReleaseError("release archive has an invalid member count")
                found = {}
                seen_members = set()
                manifest_data = None
                total = 0
                for member in members:
                    if not member.isfile() or member.issym() or member.islnk() or member.pax_headers:
                        raise ReleaseError("release archive contains a non-regular or extended member")
                    if member.size < 0:
                        raise ReleaseError("release archive contains an invalid member size")
                    total += member.size
                    if total > MAX_BYTES + MAX_MANIFEST_BYTES:
                        raise ReleaseError("release archive exceeds the uncompressed size limit")
                    if member.name in seen_members:
                        raise ReleaseError("release archive contains duplicate members")
                    seen_members.add(member.name)
                    if member.name == "release-manifest.json":
                        if member.size > MAX_MANIFEST_BYTES:
                            raise ReleaseError("release manifest exceeds the size limit")
                        reader = archive.extractfile(member)
                        manifest_data = reader.read(MAX_MANIFEST_BYTES + 1) if reader else None
                        if manifest_data is None or len(manifest_data) != member.size:
                            raise ReleaseError("release manifest could not be read")
                    elif member.name.startswith("payload/"):
                        relative = _safe_relative(member.name[len("payload/"):])
                        found[relative] = member
                    else:
                        raise ReleaseError("release archive contains an unexpected member")
                if manifest_data is None:
                    raise ReleaseError("release manifest is missing")
                try:
                    manifest = json.loads(manifest_data.decode("utf-8"),
                                          object_pairs_hook=_unique_object)
                except (UnicodeError, json.JSONDecodeError) as exc:
                    raise ReleaseError("release manifest is not valid UTF-8 JSON") from exc
                if (not isinstance(manifest, dict)
                        or set(manifest) - {"source_sha256", "source_commit", "entries"}):
                    raise ReleaseError("release manifest has an unsupported schema")
                source_sha = _sha256(manifest.get("source_sha256"), "manifest source_sha256")
                source_commit = manifest.get("source_commit")
                if (source_commit is not None and
                        (not isinstance(source_commit, str)
                         or not re.fullmatch(r"[0-9a-fA-F]{40}", source_commit))):
                    raise ReleaseError("manifest source_commit must be a 40-character hexadecimal SHA")
                entries = manifest.get("entries")
                if not isinstance(entries, list) or not entries:
                    raise ReleaseError("release manifest entries must be a non-empty list")
                expected = {}
                payload_size = 0
                for entry in entries:
                    if not isinstance(entry, dict) or set(entry) != {"path", "sha256", "size"}:
                        raise ReleaseError("release manifest entry has an unsupported schema")
                    relative = _safe_relative(entry["path"])
                    if relative in expected:
                        raise ReleaseError("release manifest contains duplicate paths")
                    if type(entry["size"]) is not int or entry["size"] < 0:
                        raise ReleaseError("release manifest contains an invalid size")
                    payload_size += entry["size"]
                    if payload_size > MAX_BYTES:
                        raise ReleaseError("release payload exceeds the size limit")
                    expected[relative] = (entry["sha256"], entry["size"])
                if _entries_fingerprint(entries) != source_sha:
                    raise ReleaseError("manifest source_sha256 does not match canonical entries")
                if "index.html" not in expected:
                    raise ReleaseError("release must contain the public index.html")
                if set(found) != set(expected):
                    raise ReleaseError("archive payload and manifest entries do not match")
                payload = {}
                for relative, member in found.items():
                    expected_hash, expected_size = expected[relative]
                    if member.size != expected_size:
                        raise ReleaseError("payload size does not match its manifest entry")
                    reader = archive.extractfile(member)
                    data = reader.read(MAX_BYTES + 1) if reader else None
                    if data is None or len(data) != expected_size:
                        raise ReleaseError("payload could not be read at its declared size")
                    actual_hash = hashlib.sha256(data).hexdigest()
                    if actual_hash != _sha256(expected_hash, "manifest entry sha256"):
                        raise ReleaseError("payload SHA256 does not match its manifest entry")
                    payload[relative] = data
            after_info = self.archive_path.lstat()
            if ((after_info.st_dev, after_info.st_ino, after_info.st_size,
                 after_info.st_mtime_ns) !=
                    (archive_info.st_dev, archive_info.st_ino, archive_info.st_size,
                     archive_info.st_mtime_ns)):
                raise ReleaseError("release archive changed during verification")
            after_digest = hashlib.sha256()
            stream.seek(0)
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                after_digest.update(block)
            if after_digest.hexdigest() != expected_digest:
                raise ReleaseError("release archive changed during verification")
            return source_sha, payload
        except ReleaseError:
            raise
        except (OSError, EOFError, tarfile.TarError) as exc:
            raise ReleaseError("release archive could not be safely inspected") from exc
        finally:
            if stream is not None:
                stream.close()

    def inspect(self, expected_digest):
        source_sha, payload = self._load_release(expected_digest)
        root = _validate_root(self.root)
        for relative in payload:
            _validate_parent(root, relative)
            _target_snapshot(root, relative)
        return {"release": source_sha, "files": len(payload), "operation": "inspect"}

    def apply(self, expected_digest):
        if self.uid_getter() != 0:
            raise ReleaseError("apply operation requires root")
        source_sha, payload = self._load_release(expected_digest)
        root = _validate_root(self.root)
        self._prepare_backup_area()
        lock_path = self.backup_dir / ".lock"
        if lock_path.is_symlink():
            raise ReleaseError("release lock file must not be a symlink")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            lock_info = os.fstat(fd)
            if not stat.S_ISREG(lock_info.st_mode) or lock_info.st_nlink != 1:
                raise ReleaseError("release lock file is not a private regular file")
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "r+b", closefd=False) as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                return self._apply_locked(root, source_sha, payload)
        finally:
            os.close(fd)

    def _prepare_backup_area(self):
        try:
            path = Path(os.path.abspath(os.fspath(self.backup_dir)))
            current = Path(path.anchor)
            for part in path.parts[1:]:
                current = current / part
                try:
                    info = current.lstat()
                except FileNotFoundError:
                    current.mkdir(mode=0o700)
                    info = current.lstat()
                if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                    raise ReleaseError("private release backup path is not a real directory")
        except OSError as exc:
            raise ReleaseError("private release backup directory is unavailable") from exc
        os.chmod(path, 0o700)

    def _apply_locked(self, root, source_sha, payload):
        snapshots = {name: _target_snapshot(root, name) for name in payload}
        run_dir = self.backup_dir / f"run-{time.time_ns()}-{os.getpid()}"
        run_dir.mkdir(mode=0o700)
        files_dir = run_dir / "files"
        files_dir.mkdir(mode=0o700)
        planned_paths = [
            name for name, snapshot in snapshots.items()
            if snapshot is None or snapshot["content"] != payload[name]
        ]
        new_paths = [name for name in planned_paths if snapshots[name] is None]
        metadata = {
            "source_sha256": source_sha,
            "planned_paths": planned_paths,
            "new_paths": new_paths,
            "files": [],
        }
        for name, snapshot in snapshots.items():
            if snapshot is None or snapshot["content"] == payload[name]:
                continue
            backup_name = hashlib.sha256(name.encode("utf-8")).hexdigest()
            backup_path = files_dir / backup_name
            fd = os.open(backup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(snapshot["content"])
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(backup_path, 0o600)
            metadata["files"].append({
                "name": backup_name, "path": name,
                "sha256": hashlib.sha256(snapshot["content"]).hexdigest(),
                "size": len(snapshot["content"]), "mode": snapshot["mode"],
                "uid": snapshot["uid"], "gid": snapshot["gid"],
            })
        meta_path = run_dir / "metadata.json"
        meta_path.write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
        os.chmod(meta_path, 0o600)

        # Verify all originals again before the first root-tree write.
        for name, snapshot in snapshots.items():
            if snapshot is None:
                if _target_snapshot(root, name) is not None:
                    raise ReleaseError("a public target changed during release preparation")
            else:
                path = root.joinpath(*PurePosixPath(name).parts)
                if not _metadata_matches(path, snapshot, snapshot["content"]):
                    raise ReleaseError("a public target changed during release preparation")

        written = []
        hook_started = False
        try:
            # Publish assets before pages, and the entry page only after its dependencies.
            for name in sorted(payload, key=lambda path: (
                    path == "index.html", not path.startswith("assets/"), path)):
                data = payload[name]
                _validate_parent(root, name, create=True)
                path = root.joinpath(*PurePosixPath(name).parts)
                snapshot = snapshots[name]
                if snapshot is None:
                    if _target_snapshot(root, name) is not None:
                        raise ReleaseError("a public target changed during release apply")
                    mode, uid, gid = 0o644, root.stat().st_uid, root.stat().st_gid
                else:
                    if not _metadata_matches(path, snapshot, snapshot["content"]):
                        raise ReleaseError("a public target changed during release apply")
                    if snapshot["content"] == data:
                        continue
                    mode, uid, gid = snapshot["mode"], snapshot["uid"], snapshot["gid"]
                _atomic_write(path, data, mode, uid, gid)
                written.append(name)
                current = path.lstat()
                if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1
                        or path.read_bytes() != data):
                    raise ReleaseError("written public file failed verification")
            if self.before_health is not None:
                hook_started = True
                self.before_health()
            healthy = self.health_checker(root, payload)
            if healthy is not True:
                raise ReleaseError("release health check failed")
        except Exception as exc:
            rollback_error = None
            try:
                self._rollback(root, snapshots, payload, written)
            except Exception as rollback_exc:
                rollback_error = rollback_exc
            if hook_started and self.rollback_hook is not None:
                try:
                    self.rollback_hook()
                except Exception as rollback_exc:
                    rollback_error = rollback_error or rollback_exc
            if rollback_error is not None:
                raise ReleaseError("release failed and automatic rollback was incomplete") from rollback_error
            if isinstance(exc, ReleaseError):
                raise
            raise ReleaseError("release failed; original public files were restored") from exc
        return {"release": source_sha, "files": len(payload), "operation": "apply"}

    @staticmethod
    def _rollback(root, snapshots, payload, written):
        for name in reversed(written):
            path = root.joinpath(*PurePosixPath(name).parts)
            snapshot = snapshots[name]
            try:
                info = path.lstat()
                expected = snapshot or {
                    "mode": 0o644, "uid": root.stat().st_uid, "gid": root.stat().st_gid,
                }
                if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
                        or stat.S_IMODE(info.st_mode) != expected["mode"]
                        or info.st_uid != expected["uid"] or info.st_gid != expected["gid"]
                        or path.read_bytes() != payload[name]):
                    raise ReleaseError("a public file changed during rollback")
                if snapshot is None:
                    path.unlink()
                else:
                    _atomic_write(path, snapshot["content"], snapshot["mode"],
                                  snapshot["uid"], snapshot["gid"])
            except OSError as exc:
                raise ReleaseError("could not restore a public target") from exc


def main():
    operation = os.environ.get("SITE_RELEASE_OPERATION", "inspect").strip().lower()
    try:
        digest = os.environ.get("SITE_RELEASE_SHA256")
        if digest is None:
            raise ReleaseError("SITE_RELEASE_SHA256 is required")
        scripts_dir = str(Path(__file__).resolve().parent)
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        try:
            from server_release_prerequisites import ServerPrerequisites
            prerequisites = ServerPrerequisites()
        except Exception as exc:
            raise ReleaseError("release prerequisite checker is unavailable") from exc

        if operation == "inspect":
            try:
                prerequisite_report = prerequisites.audit()
            except Exception as exc:
                raise ReleaseError("release prerequisite audit failed") from exc
            manager = ReleaseManager()
            result = manager.inspect(digest)
            result["prerequisites"] = _prerequisite_summary(prerequisite_report)
        elif operation == "apply":
            if os.geteuid() != 0:
                raise ReleaseError("apply operation requires root")
            try:
                prerequisite_report = prerequisites.validate()
            except Exception as exc:
                raise ReleaseError("release prerequisites are not ready") from exc
            manager = ReleaseManager(before_health=prerequisites.prepare,
                                     rollback_hook=prerequisites.rollback)
            result = manager.apply(digest)
            result["prerequisites"] = _prerequisite_summary(prerequisite_report)
        else:
            raise ReleaseError("SITE_RELEASE_OPERATION must be inspect or apply")
        print(json.dumps(result, sort_keys=True))
        return 0
    except ReleaseError as exc:
        print(f"server_release: {exc}", file=sys.stderr)
        return 1


def _prerequisite_summary(report):
    private_dirs = report.get("private_directories", [])
    email = report.get("email", {})
    php = report.get("php", {})
    return {
        "ready": bool(report.get("ready")),
        "blockers": list(report.get("blockers", [])),
        "eligible_servers": len(report.get("servers", [])),
        "private_directories_ready": all(item.get("valid") for item in private_dirs),
        "email_ready": bool(email.get("mail_enabled")),
        "php_curl_enabled": bool(php.get("curl_enabled")),
        "php_configured_version": php.get("configured_version"),
    }


if __name__ == "__main__":
    raise SystemExit(main())