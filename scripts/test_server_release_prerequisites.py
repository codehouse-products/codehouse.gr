#!/usr/bin/env python3
"""Isolated safety tests for production release prerequisites."""

import os
from pathlib import Path
import pwd
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

try:
    import server_privacy as privacy
    from server_release_prerequisites import (
        PrerequisiteError, ServerPrerequisites, _endpoint, _pool_endpoint,
    )
except ModuleNotFoundError:
    from scripts import server_privacy as privacy
    from scripts.server_release_prerequisites import (
        PrerequisiteError, ServerPrerequisites, _endpoint, _pool_endpoint,
    )


class ReleasePrerequisiteTests(unittest.TestCase):
    def test_endpoint_mapping_is_loopback_or_unix_only(self):
        self.assertEqual(_endpoint("127.0.0.1:9000"), ("tcp", "127.0.0.1:9000"))
        self.assertEqual(_endpoint("[::1]:9000"), ("tcp", "::1:9000"))
        self.assertEqual(_endpoint("unix:/run/php/php-fpm.sock"),
                         ("unix", "/run/php/php-fpm.sock"))
        self.assertIsNone(_endpoint("localhost:9000"))
        self.assertIsNone(_endpoint("0.0.0.0:9000"))
        self.assertEqual(_pool_endpoint("127.0.0.1:9000"),
                         _endpoint("127.0.0.1:9000"))
        self.assertEqual(_pool_endpoint("/run/php/php8.2-fpm.sock"),
                         _endpoint("unix:/run/php/php8.2-fpm.sock"))

    def test_pool_parser_retains_only_allowlisted_settings(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "pool.conf"
            path.write_text(
                "[www]\nlisten = 127.0.0.1:9000\nuser = www-data\n"
                "group = www-data\nenv[MAIL_TOKEN] = TOP-SECRET\n"
                "php_admin_value[open_basedir] = /srv/site:/srv/data\n",
                encoding="utf-8",
            )
            pools = ServerPrerequisites._parse_pools(path)
            self.assertEqual(len(pools), 1)
            self.assertEqual(pools[0]["listen"], "127.0.0.1:9000")
            self.assertEqual(pools[0]["open_basedir"], "/srv/site:/srv/data")
            self.assertNotIn("TOP-SECRET", repr(pools))

    def test_private_directory_check_never_reads_historical_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / ".codehouse-leads"
            directory.mkdir(mode=0o700)
            sentinel = directory / "leads.jsonl"
            sentinel.write_text("historical private sentinel", encoding="utf-8")
            os.chmod(directory, 0o700)
            manager = ServerPrerequisites(root=temporary)
            owner = directory.stat().st_uid
            read_bytes = Path.read_bytes

            def guarded_read(path):
                if path == sentinel:
                    raise AssertionError("historical data must not be opened")
                return read_bytes(path)

            with mock.patch.object(Path, "read_bytes", guarded_read):
                result = manager._private_dir(directory, owner)
            self.assertTrue(result["valid"])
            before = (sentinel.stat().st_ino, sentinel.stat().st_mtime_ns,
                      sentinel.read_bytes())
            self.assertEqual(before[2], b"historical private sentinel")
            self.assertEqual((sentinel.stat().st_ino, sentinel.stat().st_mtime_ns,
                              sentinel.read_bytes()), before)

    def test_absent_and_wrong_private_directories(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            absent = root / "missing"
            manager = ServerPrerequisites(root=temporary)
            self.assertEqual(manager._private_dir(absent, os.getuid())["state"],
                             "will_create")
            wrong_mode = root / "wrong"
            wrong_mode.mkdir(mode=0o755)
            os.chmod(wrong_mode, 0o755)
            self.assertFalse(manager._private_dir(wrong_mode, os.getuid())["valid"])
            self.assertFalse(manager._private_dir(wrong_mode, os.getuid() + 1)["valid"])
            link = root / "linked"
            link.symlink_to(wrong_mode)
            self.assertFalse(manager._private_dir(link, os.getuid())["valid"])

    def _nginx_fixture(self, root, command_runner):
        nginx = root / "nginx"
        (nginx / "sites-enabled").mkdir(parents=True)
        (nginx / "snippets").mkdir()
        privacy_include = "/etc/nginx/snippets/codehouse-privacy.conf"
        expected, _ = privacy.private_rules(None)
        (nginx / "snippets" / "codehouse-privacy.conf").write_text(
            expected, encoding="utf-8")
        config = nginx / "sites-enabled" / "site.conf"
        config.write_text(
            "server {\n    server_name codehouse.gr www.codehouse.gr;\n"
            "    root /home/websites/artivoai.com;\n"
            f"    include {privacy_include};\n"
            "    location / { try_files $uri $uri/ =404; }\n"
            "}\n"
            "server {\n    server_name unrelated.example;\n"
            "    root /srv/unrelated;\n    return 200 ok;\n}\n",
            encoding="utf-8",
        )
        private_dirs = (root / "leads", root / "rate")
        for path in private_dirs:
            path.mkdir(mode=0o700)
        identity = SimpleNamespace(pw_uid=os.getuid(), pw_gid=os.getgid(),
                                   pw_name="www-data")
        group = SimpleNamespace(gr_gid=os.getgid())

        class ReadyManager(ServerPrerequisites):
            def validate(self):
                self._resolved_php_identity = (identity.pw_uid, identity.pw_gid)
                return {"php": {"user": "www-data"}}

        manager = ReadyManager(
            root="/home/websites/artivoai.com", nginx_root=nginx,
            backup_dir=root / "backups", routing_include=(
                "/etc/nginx/snippets/codehouse-release-routing.conf"),
            privacy_include=privacy_include,
            routing_snippet=nginx / "snippets" / "codehouse-release-routing.conf",
            lead_dirs=private_dirs, uid_getter=lambda: 0,
            command_runner=command_runner, nginx_bin="/usr/sbin/nginx",
            pwd_lookup=lambda name: identity, grp_lookup=lambda name: group,
        )
        return manager, config

    def test_routing_include_changes_selected_server_only_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = []

            def runner(args, **kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args, 0)

            manager, config = self._nginx_fixture(root, runner)
            original = config.read_bytes()
            result = manager.prepare()
            self.assertTrue(result["changed"])
            installed = config.read_text(encoding="utf-8")
            self.assertIn("include /etc/nginx/snippets/codehouse-release-routing.conf;",
                          installed)
            self.assertEqual(installed.count("include /etc/nginx/snippets/codehouse-release-routing.conf;"), 1)
            self.assertIn("server_name unrelated.example;", installed)
            self.assertEqual(installed.count("server_name unrelated.example;"), 1)
            snippet = manager.routing_snippet.read_text(encoding="utf-8")
            self.assertIn("location = /dimiourgia-site/ { return 301 https://codehouse.gr/dimioyrgia-site/; }",
                          snippet)
            self.assertTrue(manager.rollback())
            self.assertEqual(config.read_bytes(), original)
            self.assertFalse(manager.routing_snippet.exists())
            self.assertGreaterEqual(len(calls), 4)

    def test_nginx_validation_failure_restores_original_files(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            calls = []

            def runner(args, **kwargs):
                calls.append(args)
                # Baseline test succeeds; test against staged config fails;
                # rollback test and reload succeed.
                if args[-1:] == ["-t"] and sum(call[-1:] == ["-t"] for call in calls) == 2:
                    return subprocess.CompletedProcess(args, 1)
                return subprocess.CompletedProcess(args, 0)

            manager, config = self._nginx_fixture(root, runner)
            original = config.read_bytes()
            with self.assertRaises(PrerequisiteError):
                manager.prepare()
            self.assertEqual(config.read_bytes(), original)
            self.assertFalse(manager.routing_snippet.exists())
            self.assertIsNone(manager._transaction)

    def test_audit_never_returns_pool_or_email_secrets(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            nginx = root / "nginx"
            (nginx / "sites-enabled").mkdir(parents=True)
            (nginx / "snippets").mkdir()
            expected, _ = privacy.private_rules(None)
            (nginx / "snippets" / "codehouse-privacy.conf").write_text(expected)
            (nginx / "sites-enabled" / "site.conf").write_text(
                "server { server_name codehouse.gr; root /home/websites/artivoai.com; "
                "include /etc/nginx/snippets/codehouse-privacy.conf; "
                "location ~ \\.php$ { fastcgi_pass 127.0.0.1:9000; } }")
            pool = root / "pool.conf"
            pool.write_text("[www]\nlisten = 127.0.0.1:9000\nuser = root\n"
                            "env[SECRET] = pool-secret-value\n")
            manager = ServerPrerequisites(
                nginx_root=nginx, root="/home/websites/artivoai.com",
                pool_config_paths=[pool], php_config_root=root / "php",
                lead_dirs=[root / "missing-a", root / "missing-b"],
                email_config=root / "private" / "zoho.json",
                pwd_lookup=lambda name: pwd.getpwnam("root"),
            )
            report = manager.audit()
            self.assertNotIn("pool-secret-value", repr(report))
            self.assertNotIn("access_token", repr(report))
            self.assertIn("email_config_not_ready", report["blockers"])


if __name__ == "__main__":
    unittest.main()