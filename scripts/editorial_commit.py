#!/usr/bin/env python3
"""Advance only the reviewed-public branch after a narrow verified article diff."""
import argparse
import base64
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request
from zoneinfo import ZoneInfo


def git(source, *args, env=None):
    result = subprocess.run(["git", "-C", str(source), *args], env=env,
                            capture_output=True, text=True)
    if result.returncode:
        # Git/network diagnostics may contain authentication material. Do not echo.
        raise RuntimeError(f"Editorial Git operation failed: {args[0]}")
    return result.stdout.strip()


def acknowledge(source, slug):
    path = Path(source) / "editorial/published.json"
    records = json.loads(path.read_text())
    if not records or records[-1]["slug"] != slug or records[-1]["status"] != "pending":
        raise RuntimeError("No matching pending publication to confirm")
    records[-1]["status"] = "published"
    records[-1]["confirmed_at"] = datetime.now(ZoneInfo("Europe/Athens")).isoformat()
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")


def commit(source, report, expected, acknowledgment=False):
    source = Path(source).resolve(strict=True)
    if not re.fullmatch("[0-9a-f]{40}", expected):
        raise RuntimeError("Invalid source commit")
    if git(source, "rev-parse", "HEAD") != expected:
        raise RuntimeError("Source commit changed")
    token = os.environ["GH_TOKEN"]
    repo = os.environ["GITHUB_REPOSITORY"]
    if repo != "codehouse-products/codehouse.gr":
        raise RuntimeError("Unexpected publication repository")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/git/ref/heads/releases/reviewed-public",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        current = json.load(response)["object"]["sha"]
    if current != expected:
        raise RuntimeError("Reviewed source changed concurrently")
    allowed = ({"editorial/published.json"} if acknowledgment else {
        "blog/index.html", "sitemap.xml", "editorial/published.json",
        f'blog/{report["slug"]}/index.html'})
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", report["slug"]):
        raise RuntimeError("Invalid prepared slug")
    if acknowledgment:
        if git(source, "status", "--porcelain"):
            raise RuntimeError("Checkout is not clean before server confirmation")
        acknowledge(source, report["slug"])
        report = dict(report, changed=["editorial/published.json"])
    changes = set(git(source, "diff", "--name-only", "HEAD").splitlines())
    changes |= set(git(source, "ls-files", "--others", "--exclude-standard").splitlines())
    if changes != set(report["changed"]) or not changes <= allowed:
        raise RuntimeError("Unapproved changes in the editorial checkout")
    if not changes:
        return expected
    if changes != allowed:
        raise RuntimeError("Incomplete editorial publication")
    git(source, "add", "--", *sorted(changes))
    git(source, "-c", "user.name=Codehouse Editorial",
        "-c", "user.email=editorial@users.noreply.github.com",
        "commit", "-m", f'{"Confirm server publication" if acknowledgment else "Prepare reviewed article"}: {report["slug"]}')
    sha = git(source, "rev-parse", "HEAD")
    environment = dict(os.environ)
    auth = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    environment.update({
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
        "GIT_CONFIG_VALUE_0": "AUTHORIZATION: basic " + auth,
        "GIT_TERMINAL_PROMPT": "0",
    })
    # No force, no main writes, no workflow-file changes. Competing releases
    # cannot be overwritten because a stale push is not a fast-forward.
    git(source, "push", "origin", "HEAD:refs/heads/releases/reviewed-public", env=environment)
    with urllib.request.urlopen(request, timeout=30) as response:
        if json.load(response)["object"]["sha"] != sha:
            raise RuntimeError("Remote publication reference verification failed")
    return sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--acknowledge", action="store_true")
    args = parser.parse_args()
    try:
        sha = commit(args.source, json.loads(Path(args.report).read_text()), args.expected, args.acknowledge)
    except Exception:
        parser.exit(1, "Editorial commit refused; inspect the safe preflight checks.\n")
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"commit={sha}\n")
    print(f"Verified editorial source commit: {sha}")


if __name__ == "__main__":
    main()
