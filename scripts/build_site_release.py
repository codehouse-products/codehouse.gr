#!/usr/bin/env python3
"""Build a reproducible, public-files-only archive from a pinned checkout."""

import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile

from server_release import MAX_BYTES, PUBLIC_DIRS, PUBLIC_FILES, ReleaseError, _safe_relative


def build(source, output, expected_commit):
    source = Path(source).resolve(strict=True)
    output = Path(output)
    actual = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != expected_commit:
        raise ReleaseError("source checkout does not match the reviewed commit")
    paths = subprocess.check_output(
        ["git", "-C", str(source), "ls-files", "-z"]
    ).decode("utf-8").split("\0")
    paths = sorted(p for p in paths if p and (
        p in PUBLIC_FILES or p.split("/")[0] in PUBLIC_DIRS
    ))
    entries, payload, total = [], {}, 0
    for relative in paths:
        _safe_relative(relative)
        target = source
        for part in relative.split("/"):
            target /= part
            if target.is_symlink():
                raise ReleaseError("source contains a symlink")
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ReleaseError("source contains a non-regular or hardlinked file")
            total += info.st_size
            if total > MAX_BYTES:
                raise ReleaseError("public release exceeds its size limit")
            data = stream.read()
        if len(data) != info.st_size:
            raise ReleaseError("source file changed during packaging")
        git_hash = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        reviewed_hash = subprocess.check_output(
            ["git", "-C", str(source), "rev-parse", expected_commit + ":" + relative],
            text=True,
        ).strip()
        if git_hash != reviewed_hash:
            raise ReleaseError("source file differs from the pinned Git tree")
        payload[relative] = data
        entries.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest(),
                        "size": len(data)})
    if "index.html" not in payload or "lead.php" not in payload:
        raise ReleaseError("release is missing its homepage or form endpoint")
    fingerprint = hashlib.sha256(
        json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    manifest = json.dumps({"source_sha256": fingerprint, "entries": entries},
                          sort_keys=True, separators=(",", ":")).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for name, data in [("release-manifest.json", manifest)] + [
                    ("payload/" + path, payload[path]) for path in sorted(payload)
                ]:
                    item = tarfile.TarInfo(name)
                    item.size, item.mode, item.mtime = len(data), 0o644, 0
                    archive.addfile(item, io.BytesIO(data))
    os.chmod(output, 0o600)
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return {"source_commit": actual, "source_sha256": fingerprint,
            "archive_sha256": digest, "files": len(entries), "bytes": total}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.source, args.output, args.commit), sort_keys=True))
    except (ReleaseError, OSError, subprocess.CalledProcessError) as exc:
        parser.exit(1, "build_site_release: public release verification failed\n")


if __name__ == "__main__":
    main()