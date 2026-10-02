#!/usr/bin/env python3
"""Isolated unit tests for the nginx privacy manager."""

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace

from scripts import server_privacy as privacy


RULES = """location ^~ /leads/ { return 404; }
location ^~ /scripts/ { return 404; }
location ^~ /attached_assets/ { return 404; }
location ^~ /docs/ { return 404; }
location ~ /\\.(?!well-known/) { return 404; }
location ~* \\.(jsonl|log|env|sql|sqlite|ini|bak)$ { return 404; }
location = /main.py { return 404; }
location = /pyproject.toml { return 404; }
location = /uv.lock { return 404; }
location = /replit.md { return 404; }
location = /router.php { return 404; }
location = /nginx-private.conf { return 404; }
location = /nginx-perf.conf { return 404; }
"""
LOCAL_RULES = Path(__file__).resolve().parents[1] / "nginx-private.conf"


def server(name="www.codehouse.gr", root=privacy.ROOT, extra=""):
    return (f"server {{\n server_name {name};\n root {root};\n"
            f" location / {{ try_files $uri $uri/ =404; }}\n {extra}\n}}\n")


class ParserTests(unittest.TestCase):
    def test_tokenizer_handles_comments_quotes_and_regex(self):
        text = '''http { # comment
          server { server_name "www.codehouse.gr"; root /home/websites/artivoai.com;
            location ~ "^/a\\{b\\}$" { return 404; }
          }
        }'''
        nodes = privacy.parse(text)
        found = privacy.server_blocks(nodes)
        self.assertEqual(len(found), 1)
        location = privacy.direct(found[0].children, "location")[0]
        self.assertEqual(privacy.value(location)[1], "~")
        self.assertEqual(privacy.value(location)[2], "^/a\\{b\\}$")

    def test_unbalanced_and_unterminated_syntax_fails(self):
        for config in ("server { root /x;", 'server { server_name "oops; }', "server }"):
            with self.subTest(config=config), self.assertRaises(privacy.PrivacyError):
                privacy.parse(config)

    def test_embedded_rules_match_reviewed_file_selectors_and_actions(self):
        def actions(text):
            return {
                tuple(privacy.value(node)[1:]):
                    tuple(tuple(privacy.value(child)) for child in node.children)
                for node in privacy.parse(text)
            }

        local = actions(LOCAL_RULES.read_text(encoding="utf-8"))
        embedded, _ = privacy.private_rules(None)
        generated = actions(embedded)
        self.assertEqual({key: generated[key] for key in local}, local)
        self.assertEqual(set(generated) - set(local),
                         {("^~", "/.git/"), ("^~", "/.github/"), ("^~", "/.agents/")})

    def test_cli_can_run_from_stdin_without_checkout_rules_file(self):
        source = Path(privacy.__file__).read_text(encoding="utf-8")
        source = source.replace(
            'if __name__ == "__main__":\n    raise SystemExit(main())',
            'if __name__ == "__main__":\n'
            '    assert PrivacyManager().rules_path is None\n'
            '    private_rules(None)\n'
            '    class StubManager:\n'
            '        def inspect(self): return []\n'
            '    PrivacyManager = StubManager\n'
            '    raise SystemExit(main())',
        )
        with tempfile.TemporaryDirectory() as cwd:
            env = dict(os.environ, SITE_OPERATION="inspect")
            result = subprocess.run(
                [sys.executable, "-"], input=source, text=True, cwd=cwd, env=env,
                capture_output=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "[]")


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.nginx = self.base / "nginx"
        (self.nginx / "sites-enabled").mkdir(parents=True)
        (self.nginx / "conf.d").mkdir()
        self.backups = self.base / "backups"
        self.rules = self.base / "nginx-private.conf"
        self.rules.write_text(RULES, encoding="utf-8")
        self.snippet = self.nginx / "snippets" / "privacy.conf"
        self.nginx_binary = str(self.base / "nginx-bin")
        self.commands = []
        self.runner = self.successful_runner

    def tearDown(self):
        self.temp.cleanup()

    def successful_runner(self, command, **kwargs):
        self.commands.append(command)
        return SimpleNamespace(returncode=0, stderr="")

    def manager(self, runner=None, uid=0):
        return privacy.PrivacyManager(
            nginx_root=self.nginx, backup_dir=self.backups, rules_path=self.rules,
            command_runner=runner or self.runner, nginx_bin=self.nginx_binary,
            uid_getter=lambda: uid, include_path=str(self.snippet),
        )

    def write_site(self, name="site.conf", content=None, extra=""):
        path = self.nginx / "sites-enabled" / name
        path.write_text(content if content is not None else server(extra=extra), encoding="utf-8")
        return path

    def test_exact_root_and_domain_matching_excludes_subdomains(self):
        sites = self.nginx / "sites-enabled"
        (sites / "targets.conf").write_text(
            server("codehouse.gr") +
            server("www.codehouse.gr") +
            server("api.codehouse.gr") +
            server("other.test", "/srv/unrelated"),
            encoding="utf-8",
        )
        records = self.manager().inspect()
        self.assertEqual(len(records), 2)
        self.assertEqual([r["server_names"] for r in records],
                         [["codehouse.gr"], ["www.codehouse.gr"]])
        self.assertTrue(all(set(r) == {"config", "server_names", "root", "locations",
                                       "privacy_include_active"} for r in records))

    def test_exact_domain_with_missing_or_wrong_root_fails_closed(self):
        self.write_site(content="server { server_name codehouse.gr; }")
        with self.assertRaises(privacy.PrivacyError):
            self.manager().inspect()
        self.write_site(content=server("codehouse.gr", "/srv/elsewhere"))
        with self.assertRaises(privacy.PrivacyError):
            self.manager().protect()

    def test_redirect_only_exact_domains_are_skipped_and_root_slash_is_normalized(self):
        sites = self.nginx / "sites-enabled"
        (sites / "redirects.conf").write_text(
            "server { server_name codehouse.gr; return 301 https://www.codehouse.gr$request_uri; }\n"
            "server { server_name www.codehouse.gr; return 308 https://www.codehouse.gr$request_uri; }\n"
            + server("codehouse.gr", privacy.ROOT + "/"),
            encoding="utf-8",
        )
        records = self.manager().inspect()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["root"], privacy.ROOT + "/")

    def test_missing_root_nonredirect_exact_domain_fails_closed(self):
        self.write_site(content="server { server_name codehouse.gr; listen 80; }")
        with self.assertRaises(privacy.PrivacyError):
            self.manager().inspect()

    def test_discovery_resolves_deduplicates_and_filters_key_files(self):
        available = self.nginx / "available.conf"
        available.write_text(server(), encoding="utf-8")
        (self.nginx / "sites-enabled" / "primary.conf").symlink_to(available)
        (self.nginx / "sites-enabled" / "duplicate.conf").symlink_to(available)
        (self.nginx / "sites-enabled" / "secret.key").write_text("not read")
        confd = self.nginx / "conf.d" / "extra.conf"
        confd.write_text(server("artivoai.com"), encoding="utf-8")
        self.assertEqual(privacy.discover(self.nginx), [available.resolve(), confd.resolve()])

    def test_protect_replaces_private_collision_only_and_is_idempotent(self):
        path = self.write_site(extra=(
            "location ^~ /leads/ { access_log off; log_not_found off; return 403; }\n"
            "location /public/ { try_files $uri =404; }\n"
            "location ~ \\.php$ { fastcgi_pass unix:/run/php.sock; }\n"
        ))
        result = self.manager().protect()
        self.assertEqual(result, 1)
        updated = path.read_text(encoding="utf-8")
        self.assertEqual(updated.count("location ^~ /leads/"), 0)
        self.assertEqual(updated.count(f"include {self.snippet};"), 1)
        self.assertIn("location /public/ { try_files $uri =404; }", updated)
        self.assertLess(updated.index(f"include {self.snippet};"),
                        updated.index(r"location ~ \.php$"))
        self.assertTrue(updated.startswith("server {\n    include "))
        self.assertTrue(self.snippet.is_file())
        self.assertEqual(self.manager().protect(), 1)
        self.assertEqual(updated, path.read_text(encoding="utf-8"))
        self.assertEqual(len(self.commands), 4)
        self.assertEqual(self.backups.stat().st_mode & 0o777, 0o700)
        self.assertTrue(all(file.stat().st_mode & 0o777 == 0o600
                            for file in self.backups.glob("*.bak")))

    def test_unsafe_existing_collision_aborts_before_writes(self):
        path = self.write_site(extra="location ^~ /leads/ { proxy_pass http://private; }\n")
        original = path.read_bytes()
        with self.assertRaises(privacy.PrivacyError):
            self.manager().protect()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(self.snippet.exists())

    def test_concurrent_administrator_edit_is_not_overwritten(self):
        path = self.write_site()
        concurrent = server(extra="# administrator change\n").encode()
        manager = self.manager()
        manager._backup = lambda *args: path.write_bytes(concurrent)
        with self.assertRaisesRegex(privacy.PrivacyError, "changed during preparation"):
            manager.protect()
        self.assertEqual(path.read_bytes(), concurrent)
        self.assertFalse(self.snippet.exists())
        self.assertEqual(self.commands, [])

    def test_validation_failure_restores_exact_original_files(self):
        path = self.write_site()
        original = path.read_bytes()

        def runner(command, **kwargs):
            self.commands.append(command)
            return SimpleNamespace(returncode=1 if len(self.commands) == 1 else 0,
                                   stderr="may contain config secrets")

        with self.assertRaisesRegex(privacy.PrivacyError, "nginx validation"):
            self.manager(runner=runner).protect()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(self.snippet.exists())
        self.assertEqual(len(self.commands), 3)  # failed test, old-config test, reload

    def test_reload_failure_restores_and_reloads_old_configuration(self):
        path = self.write_site()
        original = path.read_bytes()

        def runner(command, **kwargs):
            self.commands.append(command)
            # validation passes, first reload fails, rollback test/reload pass
            code = 1 if len(self.commands) == 2 else 0
            return SimpleNamespace(returncode=code, stderr="")

        with self.assertRaisesRegex(privacy.PrivacyError, "command failed"):
            self.manager(runner=runner).protect()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(self.snippet.exists())
        self.assertEqual(len(self.commands), 4)

    def test_non_root_protect_refuses_without_mutation(self):
        path = self.write_site()
        original = path.read_bytes()
        with self.assertRaisesRegex(privacy.PrivacyError, "requires root"):
            self.manager(uid=1000).protect()
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(self.backups.exists())

    def test_config_symlink_is_preserved_while_target_is_updated(self):
        target = self.nginx / "sites-enabled" / "target.conf"
        target.write_text(server(), encoding="utf-8")
        link = self.nginx / "sites-enabled" / "enabled.conf"
        link.symlink_to(target)
        self.manager().protect()
        self.assertTrue(link.is_symlink())
        self.assertIn(f"include {self.snippet};", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()