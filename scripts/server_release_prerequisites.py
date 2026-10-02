#!/usr/bin/env python3
"""Readiness checks and narrowly-scoped nginx routing transaction for releases."""

import glob
import ipaddress
import os
from pathlib import Path
import pwd
import grp
import re
import shutil
import stat
import subprocess
import tempfile
import time

try:
    import server_privacy as privacy
except ModuleNotFoundError:
    from . import server_privacy as privacy


ROOT = "/home/websites/artivoai.com"
ROUTING_INCLUDE = "/etc/nginx/snippets/codehouse-release-routing.conf"
BACKUP_DIR = "/var/backups/codehouse-release-routing"
LEAD_DIRS = ("/home/websites/.codehouse-leads",
             "/home/websites/.codehouse-lead-rate")
EMAIL_CONFIG = "/home/artivoai/htdocs/zoho_secrets/zoho.json"
REDIRECTS = (
    ("/dimiourgia-site/", "https://codehouse.gr/dimioyrgia-site/"),
    ("/blog/checklist-dorean-istoselida/",
     "https://codehouse.gr/blog/checklist-dorean-istoselida-epixeirisi/"),
)


class PrerequisiteError(Exception):
    """Release prerequisites cannot be satisfied safely."""


def _values(node):
    return privacy.value(node)


def _walk(nodes):
    for node in nodes:
        yield node
        if node.children is not None:
            yield from _walk(node.children)


def _endpoint(value):
    value = value.strip()
    if value.startswith("unix:"):
        socket = value[5:].rstrip(":")
        return ("unix", socket) if socket.startswith("/") else None
    host = value
    port = None
    if value.startswith("[") and "]:" in value:
        host, port = value[1:].split("]:", 1)
    elif value.count(":") == 1:
        host, port = value.rsplit(":", 1)
    if not port or not port.isdigit() or not 1 <= int(port) <= 65535:
        return None
    try:
        if not ipaddress.ip_address(host).is_loopback:
            return None
    except ValueError:
        return None
    return ("tcp", f"{host}:{int(port)}")


def _pool_endpoint(value):
    value = value.strip().strip('"').strip("'")
    if value.startswith("/"):
        return ("unix", value)
    if value.startswith("unix:"):
        return _endpoint(value)
    # FPM accepts both 127.0.0.1:9000 and [::1]:9000.
    return _endpoint(value)


def _allowed_paths(value):
    if not value:
        return []
    return [part for part in value.split(":") if part]


def _path_allowed(path, allowed):
    path = os.path.normpath(path)
    for item in allowed:
        item = os.path.normpath(item)
        if item == "/" or path == item or path.startswith(item.rstrip("/") + "/"):
            return True
    return False


def _atomic_write(path, data, mode, uid, gid):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=".codehouse-routing-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, uid, gid)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ServerPrerequisites:
    def __init__(self, root=ROOT, nginx_root="/etc/nginx",
                 backup_dir=BACKUP_DIR, privacy_include=None,
                 routing_include=ROUTING_INCLUDE, routing_snippet=None,
                 email_config=EMAIL_CONFIG, pool_config_paths=None,
                 php_config_root="/etc/php", legacy_pool_dir="/etc/php-fpm.d",
                 lead_dirs=None,
                 uid_getter=os.geteuid, command_runner=subprocess.run,
                 nginx_bin=None, pwd_lookup=pwd.getpwnam, grp_lookup=grp.getgrnam,
                 stat_probe=os.stat, access_probe=None):
        self.root = Path(root)
        self.nginx_root = Path(nginx_root)
        self.backup_dir = Path(backup_dir)
        self.privacy_include = privacy_include or privacy.PRIVACY_INCLUDE
        self.routing_include = str(routing_include)
        self.routing_snippet = Path(routing_snippet) if routing_snippet else (
            self.nginx_root / "snippets" / Path(routing_include).name)
        self.email_config = Path(email_config)
        self.lead_dirs = tuple(Path(p) for p in (lead_dirs or LEAD_DIRS))
        self.pool_config_paths = ([Path(p) for p in pool_config_paths]
                                  if pool_config_paths is not None else None)
        self.php_config_root = Path(php_config_root)
        self.legacy_pool_dir = Path(legacy_pool_dir)
        self.uid_getter = uid_getter
        self.run = command_runner
        self.nginx_bin = nginx_bin
        self.pwd_lookup = pwd_lookup
        self.grp_lookup = grp_lookup
        self.stat_probe = stat_probe
        self.access_probe = access_probe
        self._transaction = None
        self._last_audit = None
        self._resolved_php_identity = None

    def _pool_paths(self):
        if self.pool_config_paths is not None:
            return sorted(set(self.pool_config_paths), key=str)
        paths = glob.glob(str(self.php_config_root / "*" / "fpm" / "pool.d" / "*.conf"))
        paths += glob.glob(str(self.legacy_pool_dir / "*.conf"))
        return sorted({Path(p) for p in paths}, key=str)

    @staticmethod
    def _parse_pools(path):
        """Read only explicitly permitted FPM pool settings; never retain other lines."""
        pools, current = [], None
        try:
            stream = Path(path).open("r", encoding="utf-8", errors="strict")
        except (OSError, UnicodeError):
            return pools
        with stream:
            for line in stream:
                stripped = line.strip()
                section = re.fullmatch(r"\[([^\]\r\n]{1,128})\]", stripped)
                if section:
                    current = {"listen": None, "user": None, "group": None,
                               "open_basedir": None, "source": Path(path)}
                    pools.append(current)
                    continue
                if current is None or not stripped or stripped.startswith((";", "#")):
                    continue
                match = re.match(r"^(listen|user|group|php_admin_value\[open_basedir\])\s*=\s*(.*?)\s*$",
                                 stripped, re.I)
                if not match:
                    continue
                key = match.group(1).lower()
                val = match.group(2).strip().strip('"').strip("'")
                target = "open_basedir" if key.startswith("php_admin_value") else key
                current[target] = val
        return pools

    def _php_config_for_pool(self, source):
        try:
            relative = Path(source).relative_to(self.php_config_root)
            version = relative.parts[0]
            return self.php_config_root / version / "fpm" / "php.ini", (
                self.php_config_root / version / "fpm" / "conf.d")
        except (ValueError, IndexError):
            return None, None

    @staticmethod
    def _filtered_ini_value(path):
        """Return only a filtered open_basedir setting, not the source line."""
        try:
            with Path(path).open("r", encoding="utf-8", errors="strict") as stream:
                for line in stream:
                    match = re.match(r"^\s*open_basedir\s*=\s*(.*?)\s*(?:[;#].*)?$",
                                     line, re.I)
                    if match:
                        value = match.group(1).strip().strip('"').strip("'")
                        if value:
                            return value
        except (OSError, UnicodeError):
            return None
        return None

    def _selected_servers(self):
        paths = privacy.discover(self.nginx_root)
        selected = []
        for path in paths:
            try:
                text = path.read_text(encoding="utf-8")
                nodes = privacy.parse(text)
            except (OSError, UnicodeError, privacy.PrivacyError) as exc:
                raise PrerequisiteError("cannot safely inspect nginx configuration") from exc
            for server in privacy.server_blocks(nodes):
                try:
                    if privacy.eligible(server):
                        names, roots = privacy.server_info(server)
                        selected.append({"path": path, "server": server,
                                         "nodes": nodes, "names": names,
                                         "root": roots[0][0], "text": text})
                except privacy.PrivacyError as exc:
                    raise PrerequisiteError("an ambiguous target nginx server was found") from exc
        return selected

    def _private_dir(self, path, uid):
        try:
            info = Path(path).lstat()
        except FileNotFoundError:
            return {"path": str(path), "state": "will_create", "valid": True}
        except OSError:
            return {"path": str(path), "state": "unavailable", "valid": False}
        valid = (stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                 and info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700)
        return {"path": str(path), "state": "present", "valid": valid}

    @staticmethod
    def _mode_allows(info, uid, gid, requested):
        if uid == 0:
            return True
        mode = stat.S_IMODE(info.st_mode)
        if uid == info.st_uid:
            bits = (mode >> 6) & 7
        elif gid == info.st_gid:
            bits = (mode >> 3) & 7
        else:
            bits = mode & 7
        return bits & requested == requested

    def _email_status(self, php_uid=None, php_gid=None):
        try:
            info = self.stat_probe(self.email_config)
            present = stat.S_ISREG(info.st_mode)
        except (OSError, TypeError):
            return {"present": False, "readable": False}
        if self.access_probe is not None:
            try:
                readable = bool(self.access_probe(str(self.email_config), os.R_OK))
            except (OSError, TypeError):
                readable = False
        elif php_uid is None or php_gid is None:
            readable = False
        else:
            readable = self._mode_allows(info, php_uid, php_gid, 4)
            parent = self.email_config.parent
            while readable:
                try:
                    parent_info = self.stat_probe(parent)
                except (OSError, TypeError):
                    readable = False
                    break
                readable = stat.S_ISDIR(parent_info.st_mode) and self._mode_allows(
                    parent_info, php_uid, php_gid, 1)
                if parent == parent.parent:
                    break
                parent = parent.parent
        return {"present": present, "readable": present and readable}

    def _curl_status(self, pool):
        _, conf_d = self._php_config_for_pool(pool["source"])
        if conf_d is None:
            return False
        try:
            entries = list(conf_d.iterdir())
        except OSError:
            return False
        for entry in entries:
            if "curl" not in entry.name.lower() or not entry.name.lower().endswith(".ini"):
                continue
            try:
                info = entry.lstat()
                # Enabled FPM extension links are expected to be links; stat confirms
                # their target exists without reading extension/config contents.
                if stat.S_ISLNK(info.st_mode):
                    target_info = self.stat_probe(entry)
                    if stat.S_ISREG(target_info.st_mode):
                        return True
            except OSError:
                continue
        return False

    def audit(self):
        blockers = []
        records = []
        pools = []
        self._resolved_php_identity = None
        for path in self._pool_paths():
            pools.extend(self._parse_pools(path))
        try:
            selected = self._selected_servers()
        except PrerequisiteError:
            selected = []
            blockers.append("nginx_configuration_unreadable")
        if not selected:
            blockers.append("no_eligible_server")
        expected_privacy, selectors = privacy.private_rules(None)
        privacy_ok = True
        for item in selected:
            active = privacy.include_active(item["server"], self.privacy_include)
            if not active:
                privacy_ok = False
            records.append({"config": item["path"].name[:160],
                            "server_names": [str(n)[:120] for n in item["names"][:16]],
                            "root": item["root"][:240],
                            "privacy_include_active": active})
        privacy_snippet = self.nginx_root / "snippets" / Path(self.privacy_include).name
        try:
            actual = privacy_snippet.resolve(strict=True).read_text(encoding="utf-8")
            if actual != expected_privacy:
                privacy_ok = False
        except (OSError, UnicodeError):
            privacy_ok = False
        if not privacy_ok:
            blockers.append("privacy_include_not_ready")

        endpoints = []
        for item in selected:
            for location in privacy.direct(item["server"].children, "location"):
                for node in _walk([location]):
                    if node.children is None and _values(node)[:1] == ["fastcgi_pass"]:
                        args = _values(node)
                        if len(args) >= 2:
                            endpoint = _endpoint(args[1])
                            endpoints.append(endpoint)
        distinct = set(e for e in endpoints if e is not None)
        if not endpoints:
            blockers.append("php_endpoint_missing")
        if len(distinct) != 1 or len(distinct) != len(set(endpoints)):
            blockers.append("php_endpoint_ambiguous")
        endpoint = next(iter(distinct)) if len(distinct) == 1 else None
        matched = []
        if endpoint is not None:
            for pool in pools:
                if pool["listen"] and _pool_endpoint(pool["listen"]) == endpoint:
                    matched.append(pool)
        if len(matched) != 1:
            blockers.append("php_pool_not_unique")
        php_uid = php_gid = None
        user_label = None
        basedir_values = []
        php_version_ini = None
        curl_enabled = False
        if len(matched) == 1:
            pool = matched[0]
            try:
                user = self.pwd_lookup(pool["user"]) if pool["user"] else None
                if user is None:
                    raise KeyError
                php_uid = user.pw_uid
                user_label = str(user.pw_name)[:64]
                group = self.grp_lookup(pool["group"]) if pool["group"] else None
                php_gid = group.gr_gid if group else user.pw_gid
                self._resolved_php_identity = (php_uid, php_gid)
            except (KeyError, OSError):
                blockers.append("php_identity_unresolved")
            if pool["open_basedir"]:
                basedir_values.append(pool["open_basedir"])
            php_version_ini, _ = self._php_config_for_pool(pool["source"])
            global_basedir = self._filtered_ini_value(php_version_ini) if php_version_ini else None
            if global_basedir:
                basedir_values.append(global_basedir)
            curl_enabled = self._curl_status(pool)
            if not curl_enabled:
                blockers.append("php_curl_not_enabled")

        private_dirs = [self._private_dir(path, php_uid) if php_uid is not None else
                        {"path": str(path), "state": "unknown", "valid": False}
                        for path in self.lead_dirs]
        if any(not record["valid"] for record in private_dirs):
            blockers.append("private_directory_not_ready")
        required_paths = [str(self.root), *(str(p) for p in self.lead_dirs),
                          str(self.email_config.parent)]
        open_basedir_ok = True
        for value in basedir_values:
            allowed = _allowed_paths(value)
            if any(not _path_allowed(path, allowed) for path in required_paths):
                open_basedir_ok = False
        if not open_basedir_ok:
            blockers.append("open_basedir_disallows_required_paths")
        email = self._email_status(php_uid, php_gid)
        if not email["present"] or not email["readable"]:
            blockers.append("email_config_not_ready")
        result = {
            "ready": not blockers,
            "blockers": sorted(set(blockers)),
            "servers": records[:32],
            "php": {"endpoint_count": len(endpoints), "pool_match_count": len(matched),
                    "user": user_label, "curl_enabled": curl_enabled,
                    "open_basedir_configured": bool(basedir_values),
                    "open_basedir_allows_required_paths": open_basedir_ok},
            "private_directories": private_dirs,
            "email": {"present": email["present"], "readable": email["readable"],
                      "mail_enabled": email["present"] and email["readable"]},
        }
        self._last_audit = result
        return result

    def validate(self):
        result = self.audit()
        if not result["ready"]:
            raise PrerequisiteError("release prerequisites are not ready: " +
                                    ", ".join(result["blockers"]))
        return result

    def _nginx(self):
        if self.nginx_bin:
            return self.nginx_bin
        for candidate in ("/usr/sbin/nginx", "/usr/bin/nginx", "/sbin/nginx"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return shutil.which("nginx")

    def _command(self, args):
        try:
            result = self.run(args, stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, check=False, text=True)
        except OSError as exc:
            raise PrerequisiteError("nginx command could not be run") from exc
        if result.returncode:
            raise PrerequisiteError("nginx validation or reload command failed")

    def _reload(self, nginx):
        systemctl = shutil.which("systemctl")
        self._command([systemctl, "reload", "nginx"] if systemctl
                      else [nginx, "-s", "reload"])

    @staticmethod
    def _redirect_status(location):
        args = _values(location)
        if len(args) < 2:
            return "conflict"
        selector = tuple(args[1:])
        for route, target in REDIRECTS:
            if selector in (( "=", route), ("=", route.rstrip("/"))):
                children = location.children or []
                returns = [_values(n) for n in children if n.children is None
                           and _values(n)[:1] == ["return"]]
                if len(returns) == 1 and returns[0] in (
                        ["return", "301", target], ["return", "301", target.rstrip("/")]):
                    return "equivalent"
                return "conflict"
        return None

    def _routing_content(self):
        return "".join(
            f"location = {route} {{ return 301 {target}; }}\n"
            for route, target in REDIRECTS
        ).encode("utf-8")

    def _ensure_backup(self):
        path = Path(os.path.abspath(os.fspath(self.backup_dir)))
        current = Path(path.anchor)
        for part in path.parts[1:]:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                current.mkdir(mode=0o700)
                info = current.lstat()
            except OSError as exc:
                raise PrerequisiteError("routing backup directory is unavailable") from exc
            if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                raise PrerequisiteError("routing backup directory is unsafe")
        os.chmod(path, 0o700)

    def prepare(self):
        if self.uid_getter() != 0:
            raise PrerequisiteError("prepare operation requires root")
        audit = self.validate()
        if self._resolved_php_identity is None:
            raise PrerequisiteError("PHP-FPM identity could not be resolved")
        uid, gid = self._resolved_php_identity
        # Never touch an existing private directory or inspect its contents.
        for path in self.lead_dirs:
            if not path.exists() and not path.is_symlink():
                path.mkdir(mode=0o700)
                os.chown(path, uid, gid)
                os.chmod(path, 0o700)

        selected = self._selected_servers()
        if not selected:
            raise PrerequisiteError("no eligible nginx server blocks found")
        self._ensure_backup()
        nginx = self._nginx()
        if not nginx:
            raise PrerequisiteError("nginx executable not found")
        self._command([nginx, "-t"])
        edits_by_path = {}
        shared_content = self._routing_content()
        checked_configs = set()
        for item in selected:
            server = item["server"]
            if item["path"] not in checked_configs:
                if privacy.include_outside_targets(item["nodes"], self.routing_include):
                    raise PrerequisiteError(
                        "release-routing include exists outside selected server blocks")
                checked_configs.add(item["path"])
            active_includes = [node for node in privacy.direct(server.children, "include")
                               if _values(node)[1:] == [self.routing_include]]
            nested_includes = [node for node in _walk(server.children)
                               if _values(node)[:1] == ["include"]
                               and _values(node)[1:] == [self.routing_include]
                               and node not in active_includes]
            if nested_includes:
                raise PrerequisiteError("release-routing include is nested in a target server")
            if len(active_includes) > 1:
                raise PrerequisiteError("duplicate release-routing include in target server")
            statuses = []
            for location in privacy.direct(server.children, "location"):
                status = self._redirect_status(location)
                if status:
                    statuses.append(status)
            if "conflict" in statuses:
                raise PrerequisiteError("an exact routing location conflicts with the release redirect")
            # Known equivalent existing locations remain untouched. Avoid duplicate
            # selectors by adding the managed include only when both routes are absent.
            if "equivalent" in statuses:
                if len(statuses) < 2:
                    raise PrerequisiteError("mixed existing routing rules require manual review")
                continue
            if active_includes:
                continue
            source = item["path"]
            opening = server.body_start
            if opening is None:
                raise PrerequisiteError("target nginx server boundary is ambiguous")
            edits_by_path.setdefault(source, []).append(opening)

        changes = {}
        for source, openings in edits_by_path.items():
            original_text = next(item["text"] for item in selected
                                 if item["path"] == source)
            old = original_text.encode("utf-8")
            updated = original_text
            for opening in sorted(set(openings), reverse=True):
                updated = (updated[:opening] + "\n    include " +
                           self.routing_include + ";" + updated[opening:])
            info = source.stat()
            changes[source] = (old, updated.encode("utf-8"), stat.S_IMODE(info.st_mode),
                               info.st_uid, info.st_gid)
        snippet = self.routing_snippet
        try:
            target = snippet.resolve(strict=True)
            snippet_old = target.read_bytes()
            snippet_info = target.stat()
            snippet_meta = (stat.S_IMODE(snippet_info.st_mode), snippet_info.st_uid,
                            snippet_info.st_gid)
        except FileNotFoundError:
            if snippet.is_symlink():
                raise PrerequisiteError("release-routing snippet symlink is dangling")
            try:
                target = snippet.parent.resolve(strict=True) / snippet.name
            except OSError as exc:
                raise PrerequisiteError("nginx snippet directory is unavailable") from exc
            snippet_old = None
            snippet_meta = (0o644, os.geteuid(), os.getegid())
        if snippet_old is not None and snippet_old != shared_content:
            # Idempotent install accepts exactly the managed content only.
            raise PrerequisiteError("existing release-routing snippet differs from managed rules")
        if not changes and snippet_old is not None:
            self._transaction = None
            self._reload(nginx)
            return {"operation": "prepare", "changed": False}
        self._ensure_backup()
        files = dict(changes)
        if snippet_old != shared_content:
            files[target] = (snippet_old, shared_content, *snippet_meta)
        snapshots = {}
        for path, (old, _, mode, uid, gid) in files.items():
            info = path.stat() if path.exists() else None
            snapshots[path] = (old, mode, uid, gid,
                               (info.st_dev, info.st_ino) if info else None)
            if old is not None:
                name = f"{time.time_ns()}-{len(snapshots):03d}.bak"
                backup = self.backup_dir / name
                fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
                with os.fdopen(fd, "wb") as stream:
                    stream.write(old)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(backup, 0o600)
        for path, (old, _, mode, uid, gid) in files.items():
            if old is None:
                if path.exists() or path.is_symlink():
                    raise PrerequisiteError("nginx configuration changed during preparation")
            else:
                info = path.stat()
                if path.read_bytes() != old or (stat.S_IMODE(info.st_mode), info.st_uid,
                                                info.st_gid) != (mode, uid, gid):
                    raise PrerequisiteError("nginx configuration changed during preparation")
        try:
            for path, (old, updated, mode, uid, gid) in files.items():
                if old != updated:
                    _atomic_write(path, updated, mode, uid, gid)
            self._command([nginx, "-t"])
            self._reload(nginx)
        except Exception as exc:
            self._transaction = {"files": files, "nginx": nginx}
            try:
                self.rollback()
            except Exception as rollback_exc:
                raise PrerequisiteError("routing change failed and rollback was incomplete") from rollback_exc
            if isinstance(exc, PrerequisiteError):
                raise
            raise PrerequisiteError("routing change failed; original nginx files were restored") from exc
        self._transaction = {"files": files, "nginx": nginx}
        return {"operation": "prepare", "changed": True}

    def rollback(self):
        if not self._transaction:
            return False
        transaction = self._transaction
        for path, (old, updated, mode, uid, gid) in transaction["files"].items():
            if old is not None:
                try:
                    info = path.stat()
                    current = path.read_bytes()
                    metadata = (stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)
                except OSError:
                    current, metadata = None, None
                if current == old and metadata == (mode, uid, gid):
                    continue
                if current != updated or metadata != (mode, uid, gid):
                    raise PrerequisiteError("nginx configuration changed before rollback")
            if old is None:
                try:
                    current = path.read_bytes()
                except FileNotFoundError:
                    if path.is_symlink():
                        raise PrerequisiteError("routing snippet changed before rollback")
                    continue
                if current != updated:
                    raise PrerequisiteError("routing snippet changed before rollback")
                path.unlink()
            else:
                _atomic_write(path, old, mode, uid, gid)
        self._command([transaction["nginx"], "-t"])
        self._reload(transaction["nginx"])
        self._transaction = None
        return True
