#!/usr/bin/env python3
"""Conservative nginx privacy inspection and opt-in protection installer."""

import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time


ROOT = "/home/websites/artivoai.com"
PRIVACY_INCLUDE = "/etc/nginx/snippets/codehouse-privacy.conf"
DOMAIN_NAMES = {"codehouse.gr", "www.codehouse.gr"}
SKIP_SUFFIXES = {".key", ".pem", ".crt", ".cer", ".p12", ".pfx", ".der", ".pub"}
EMBEDDED_RULES = r"""location ^~ /leads/ { return 404; }
location ^~ /scripts/ { return 404; }
location ^~ /attached_assets/ { return 404; }
location ^~ /docs/ { return 404; }
location ~ /\.(?!well-known/) { return 404; }
location ~* \.(jsonl|log|env|sql|sqlite|ini|bak)$ { return 404; }
location = /main.py { return 404; }
location = /pyproject.toml { return 404; }
location = /uv.lock { return 404; }
location = /replit.md { return 404; }
location = /router.php { return 404; }
location = /nginx-private.conf { return 404; }
location = /nginx-perf.conf { return 404; }
"""
EXTRA_LOCATIONS = (
    'location ^~ /.git/ { return 404; }\n'
    'location ^~ /.github/ { return 404; }\n'
    'location ^~ /.agents/ { return 404; }\n'
)


class PrivacyError(Exception):
    pass


class Token:
    def __init__(self, value, start, end):
        self.value, self.start, self.end = value, start, end


class Node:
    def __init__(self, header, start, end, children=None, body_start=None):
        self.header, self.start, self.end = header, start, end
        self.children, self.body_start = children, body_start


def tokenize(text):
    """Tokenize nginx syntax while preserving source offsets; reject ambiguity."""
    tokens, i, n = [], 0, len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue
        if text[i] == "#":
            end = text.find("\n", i)
            i = n if end < 0 else end + 1
            continue
        start, char = i, text[i]
        if char in "{};":
            tokens.append(Token(char, i, i + 1))
            i += 1
            continue
        value, quote = [], None
        while i < n:
            char = text[i]
            if quote:
                if char == "\\":
                    if i + 1 >= n:
                        raise PrivacyError("invalid quoted escape")
                    value.extend((char, text[i + 1]))
                    i += 2
                elif char == quote:
                    quote = None
                    i += 1
                else:
                    value.append(char)
                    i += 1
            elif char in "\"'":
                quote = char
                i += 1
            elif char.isspace() or char in "{};":
                break
            elif char == "\\" and i + 1 < n:
                value.extend((char, text[i + 1]))
                i += 2
            elif char == "#":
                end = text.find("\n", i)
                i = n if end < 0 else end
                break
            else:
                value.append(char)
                i += 1
        if quote:
            raise PrivacyError("unterminated quote")
        if not value:
            if i == start:
                raise PrivacyError("invalid token")
            continue
        tokens.append(Token("".join(value), start, i))
    return tokens


def parse(text):
    tokens, index = tokenize(text), 0

    def block(opened=False):
        nonlocal index
        nodes, header = [], []
        while index < len(tokens):
            token = tokens[index]
            index += 1
            if token.value == ";":
                if not header:
                    raise PrivacyError("empty directive")
                nodes.append(Node(header, header[0].start, token.end))
                header = []
            elif token.value == "{":
                if not header:
                    raise PrivacyError("empty block header")
                children = block(True)
                end = tokens[index - 1].end
                nodes.append(Node(header, header[0].start, end, children, token.end))
                header = []
            elif token.value == "}":
                if not opened or header:
                    raise PrivacyError("unexpected closing brace")
                return nodes
            else:
                header.append(token)
        if opened or header:
            raise PrivacyError("unterminated nginx block or directive")
        return nodes

    return block()


def value(node):
    return [token.value for token in node.header]


def direct(nodes, name):
    return [node for node in nodes if node.header and node.header[0].value == name]


def server_blocks(nodes):
    found = []
    for node in nodes:
        # sites-enabled and conf.d files are parsed in their http{} include
        # context, so their server blocks are direct top-level nodes here.
        if node.children is not None and node.header and node.header[0].value == "server":
            found.append(node)
        if node.children is not None and node.header and node.header[0].value == "http":
            found.extend(child for child in node.children if child.children is not None
                         and child.header and child.header[0].value == "server")
    return found


def server_info(server):
    names = [arg for item in direct(server.children, "server_name") for arg in value(item)[1:]]
    roots = [value(item)[1:] for item in direct(server.children, "root")]
    return names, roots


def eligible(server):
    names, roots = server_info(server)
    if len(roots) > 1:
        raise PrivacyError("ambiguous direct root in candidate server")
    exact_domain = bool(DOMAIN_NAMES.intersection(names))
    if exact_domain and not roots and redirect_only(server):
        return False
    if exact_domain and (len(roots) != 1 or not root_matches(roots[0])):
        raise PrivacyError("exact domain server does not have the required direct root")
    other_codehouse_subdomain = any(
        name.endswith(".codehouse.gr") and name not in DOMAIN_NAMES for name in names
    )
    return (len(roots) == 1 and root_matches(roots[0])
            and (exact_domain or not other_codehouse_subdomain))


def root_matches(args):
    return len(args) == 1 and args[0].rstrip("/") == ROOT.rstrip("/")


def redirect_only(server):
    returns = [value(node) for node in direct(server.children, "return")]
    handlers = {"location", "try_files", "proxy_pass", "fastcgi_pass", "uwsgi_pass",
                "scgi_pass", "grpc_pass", "index", "alias"}
    return (len(returns) == 1 and len(returns[0]) >= 2
            and returns[0][1] in {"301", "302", "307", "308"}
            and not any(node.children is not None or value(node)[0] in handlers
                        for node in server.children))


def safe_config_path(path):
    return not any(Path(str(path)).suffix.lower() == suffix for suffix in SKIP_SUFFIXES)


def discover(nginx_root):
    root = Path(nginx_root)
    paths = []
    for folder, pattern in ((root / "sites-enabled", None), (root / "conf.d", "*.conf")):
        if not folder.is_dir():
            continue
        entries = folder.iterdir()
        for entry in entries:
            if pattern and not entry.name.endswith(".conf"):
                continue
            try:
                if not entry.is_file():
                    continue
                resolved = entry.resolve(strict=True)
                if not safe_config_path(entry) or not safe_config_path(resolved):
                    continue
                paths.append(resolved)
            except OSError:
                continue
    return sorted(set(paths), key=str)


def private_rules(rules_path):
    if rules_path is None:
        raw = EMBEDDED_RULES
    else:
        try:
            raw = Path(rules_path).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise PrivacyError("privacy rules file unavailable") from exc
    nodes = parse(raw)
    if not nodes or any(node.children is None or value(node)[0] != "location" for node in nodes):
        raise PrivacyError("privacy rules must contain only location blocks")
    selectors = set()
    for node in nodes:
        header = value(node)
        if len(header) < 3:
            raise PrivacyError("invalid privacy location")
        selector = tuple(header[1:])
        if selector in selectors:
            raise PrivacyError("duplicate privacy location")
        selectors.add(selector)
        returns = [value(child) for child in node.children if child.children is None]
        if returns != [["return", "404"]]:
            raise PrivacyError("privacy location must contain only return 404")
    return raw.rstrip() + "\n" + EXTRA_LOCATIONS, selectors


def location_selector(node):
    header = value(node)
    return tuple(header[1:]) if header and header[0] == "location" else ()


def private_collision(node, selectors):
    header = value(node)
    if not header or header[0] != "location":
        return False
    selector = location_selector(node)
    protected_dirs = {"/leads/", "/scripts/", "/attached_assets/", "/docs/",
                      "/.git/", "/.github/", "/.agents/"}
    protected_exact = {"/main.py", "/pyproject.toml", "/uv.lock", "/replit.md",
                       "/router.php", "/nginx-private.conf", "/nginx-perf.conf"}
    same = selector in selectors
    path = selector[-1] if selector else ""
    allowed_path_selector = (len(selector) == 1 or
                             (len(selector) == 2 and selector[0] in ("=", "^~")))
    same_path = path in protected_dirs | protected_exact and allowed_path_selector
    if not (same or same_path):
        return False
    if node.children is None:
        raise PrivacyError("privacy location collision has no block")
    has_deny = False
    for child in node.children:
        directive = value(child)
        if child.children is not None:
            raise PrivacyError("privacy location collision is not a known deny-only rule")
        if directive in (["return", "403"], ["return", "404"], ["return", "410"],
                         ["deny", "all"], ["internal"]):
            has_deny = True
        elif directive not in (["access_log", "off"], ["log_not_found", "off"]):
            raise PrivacyError("privacy location collision is not a known deny-only rule")
    if not has_deny:
        raise PrivacyError("privacy location collision is not deny-only")
    return True


def include_active(server, include_path=PRIVACY_INCLUDE):
    includes = direct(server.children, "include")
    matching = [node for node in includes if value(node)[1:] == [include_path]]
    if len(matching) > 1:
        raise PrivacyError("duplicate privacy include in server block")
    return bool(matching)


def include_outside_targets(nodes, include_path):
    """Find a managed include outside a selected server context."""
    servers = set(id(node) for node in server_blocks(nodes) if eligible(node))

    def walk(items, inside_selected_server=False):
        for node in items:
            selected = inside_selected_server or (
                node.children is not None and node.header
                and node.header[0].value == "server" and id(node) in servers
            )
            if node.header and node.header[0].value == "include" and value(node)[1:] == [include_path]:
                if not selected:
                    return True
            if node.children is not None and walk(node.children, selected):
                return True
        return False

    return walk(nodes)


def inspect_records(paths, include_path=PRIVACY_INCLUDE):
    records = []
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
            servers = server_blocks(parse(text))
            for server in servers:
                if eligible(server):
                    names, roots = server_info(server)
                    locations = []
                    for location in direct(server.children, "location"):
                        head = value(location)
                        # Report only bounded location headers, never directive bodies.
                        locations.append(" ".join(head[:8])[:240])
                    records.append({
                        "config": path.name, "server_names": names, "root": roots[0][0],
                        "locations": locations,
                        "privacy_include_active": include_active(server, include_path),
                    })
        except (OSError, UnicodeError, PrivacyError) as exc:
            raise PrivacyError("cannot safely inspect nginx configuration") from exc
    return records


class PrivacyManager:
    def __init__(self, nginx_root="/etc/nginx",
                 backup_dir="/var/backups/codehouse-nginx-privacy",
                 rules_path=None, command_runner=subprocess.run, nginx_bin=None,
                 uid_getter=os.geteuid, include_path=PRIVACY_INCLUDE):
        self.nginx_root = Path(nginx_root)
        self.backup_dir = Path(backup_dir)
        self.rules_path = Path(rules_path) if rules_path is not None else None
        self.run = command_runner
        self.nginx_bin = nginx_bin
        self.uid_getter = uid_getter
        self.include_path = include_path

    def inspect(self):
        return inspect_records(discover(self.nginx_root), self.include_path)

    def _command(self, args):
        try:
            result = self.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                              check=False, text=True)
        except OSError as exc:
            raise PrivacyError("nginx command could not be run") from exc
        if result.returncode:
            # Do not relay nginx stderr: it can echo sensitive configuration text.
            raise PrivacyError("nginx validation or reload command failed")

    def _nginx(self):
        if self.nginx_bin:
            return self.nginx_bin
        for path in ("/usr/sbin/nginx", "/usr/bin/nginx", "/sbin/nginx"):
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        return shutil.which("nginx")

    @staticmethod
    def _atomic(path, data, mode=None, uid=None, gid=None):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".privacy-", dir=str(path.parent))
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if mode is not None:
                os.chmod(temp_name, mode)
            if uid is not None and gid is not None:
                os.chown(temp_name, uid, gid)
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _backup(self, path, content, mode, uid, gid):
        self.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.backup_dir.is_symlink() or not self.backup_dir.is_dir():
            raise PrivacyError("backup directory is not a safe directory")
        os.chmod(self.backup_dir, 0o700)
        digest = hashlib.sha256(str(path).encode()).hexdigest()[:16]
        name = f"{time.time_ns()}-{digest}.bak"
        backup = self.backup_dir / name
        self._atomic(backup, content, 0o600, os.geteuid(), os.getegid())

    def protect(self):
        if self.uid_getter() != 0:
            raise PrivacyError("protect operation requires root")
        if not self._nginx():
            raise PrivacyError("nginx executable not found")
        nginx = self._nginx()
        self.backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.backup_dir.is_symlink() or not self.backup_dir.is_dir():
            raise PrivacyError("backup directory is not a safe directory")
        os.chmod(self.backup_dir, 0o700)
        lock_path = self.backup_dir / ".lock"
        if lock_path.is_symlink():
            raise PrivacyError("privacy lock file must not be a symlink")
        with open(lock_path, "a+b") as lock:
            os.chmod(lock_path, 0o600)
            fcntl.flock(lock, fcntl.LOCK_EX)
            return self._protect_locked(nginx)

    def _protect_locked(self, nginx):
        paths = discover(self.nginx_root)
        if not paths:
            raise PrivacyError("no enabled nginx configuration files found")
        _, selectors = private_rules(self.rules_path)
        targets, changes = [], {}
        for path in paths:
            try:
                original = path.read_bytes()
                text = original.decode("utf-8")
                nodes = parse(text)
                if include_outside_targets(nodes, self.include_path):
                    raise PrivacyError("privacy include is referenced outside selected servers")
                edits = []
                target_count = 0
                for server in server_blocks(nodes):
                    if not eligible(server):
                        continue
                    if include_active(server, self.include_path):
                        target_count += 1
                        continue
                    children = server.children
                    removals = [node for node in direct(children, "location")
                                if private_collision(node, selectors)]
                    opening = server.body_start
                    if opening is None:
                        raise PrivacyError("server block boundary is ambiguous")
                    edits.extend((node.start, node.end, "") for node in removals)
                    edits.append((opening, opening, f"\n    include {self.include_path};"))
                    target_count += 1
                if target_count:
                    targets.extend([path] * target_count)
                if edits:
                    updated = text
                    for start, end, replacement in sorted(edits, reverse=True):
                        updated = updated[:start] + replacement + updated[end:]
                    info = path.stat()
                    changes[path] = (original, updated.encode("utf-8"), stat.S_IMODE(info.st_mode),
                                     info.st_uid, info.st_gid)
            except (OSError, UnicodeError, PrivacyError) as exc:
                if isinstance(exc, PrivacyError):
                    raise
                raise PrivacyError("cannot safely prepare nginx configuration") from exc
        if not targets:
            raise PrivacyError("no eligible server blocks found")
        snippet = Path(self.include_path)
        if snippet.is_symlink():
            raise PrivacyError("privacy snippet path must not be a symlink")
        snippet_content = private_rules(self.rules_path)[0].encode("utf-8")
        old_snippet = snippet.read_bytes() if snippet.exists() else None
        if old_snippet is not None and old_snippet != snippet_content:
            raise PrivacyError("existing privacy snippet differs from reviewed rules")
        if not changes:
            if old_snippet is None:
                raise PrivacyError("active privacy include is missing")
            self._command([nginx, "-t"])
            self._reload(nginx)
            return len(targets)
        snippet_meta = (stat.S_IMODE(snippet.stat().st_mode), snippet.stat().st_uid,
                        snippet.stat().st_gid) if old_snippet is not None else (
                            0o644, os.geteuid(), os.getegid())
        for path, (old, _, mode, uid, gid) in changes.items():
            self._backup(path, old, mode, uid, gid)
        if old_snippet is not None:
            self._backup(snippet, old_snippet, *snippet_meta)
        # A concurrent administrator edit must not be overwritten or rolled back.
        for path, (original, _, mode, uid, gid) in changes.items():
            info = path.stat()
            if (path.is_symlink() or path.read_bytes() != original
                    or (stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid) != (mode, uid, gid)):
                raise PrivacyError("nginx configuration changed during preparation")
        if snippet.is_symlink() or (snippet.read_bytes() if snippet.exists() else None) != old_snippet:
            raise PrivacyError("privacy snippet changed during preparation")
        try:
            self._atomic(snippet, snippet_content, *snippet_meta)
            for path, (_, updated, mode, uid, gid) in changes.items():
                self._atomic(path, updated, mode, uid, gid)
            self._command([nginx, "-t"])
            self._reload(nginx)
        except Exception as exc:
            try:
                self._rollback(changes, snippet, old_snippet, snippet_meta, nginx)
            except Exception as rollback_error:
                raise PrivacyError("privacy changes failed and automatic rollback was incomplete") from rollback_error
            if isinstance(exc, PrivacyError):
                raise
            raise PrivacyError("privacy changes failed; original files were restored") from exc
        return len(targets)

    def _reload(self, nginx):
        systemctl = shutil.which("systemctl")
        if systemctl:
            self._command([systemctl, "reload", "nginx"])
        else:
            self._command([nginx, "-s", "reload"])

    def _rollback(self, changes, snippet, old_snippet, snippet_meta, nginx):
        for path, (original, _, mode, uid, gid) in changes.items():
            self._atomic(path, original, mode, uid, gid)
        if old_snippet is None:
            try:
                snippet.unlink()
            except FileNotFoundError:
                pass
        else:
            self._atomic(snippet, old_snippet, *snippet_meta)
        try:
            self._command([nginx, "-t"])
            self._reload(nginx)
        except PrivacyError:
            raise PrivacyError("privacy changes rolled back; old nginx configuration could not be reloaded")


def main():
    operation = os.environ.get("SITE_OPERATION", "inspect").strip().lower()
    manager = PrivacyManager()
    try:
        if operation == "inspect":
            print(json.dumps(manager.inspect(), ensure_ascii=True, indent=2))
        elif operation == "protect":
            print(f"Protected {manager.protect()} eligible server block(s).")
        else:
            raise PrivacyError("SITE_OPERATION must be inspect or protect")
    except PrivacyError as exc:
        print(f"server_privacy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())