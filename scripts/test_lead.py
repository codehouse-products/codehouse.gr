#!/usr/bin/env python3
"""Isolated HTTP regression tests for lead.php (requires PHP CLI)."""

import http.client
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
LEAD_SOURCE = REPO_ROOT / "lead.php"
PRODUCTION_ZOHO_CONFIG = "/home/artivoai/htdocs/zoho_secrets/zoho.json"


def unused_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class LeadEndpointHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="lead-http-test-")
        self.sandbox = Path(self.temp_dir.name)
        self.webroot = self.sandbox / "public"
        self.webroot.mkdir()
        self.endpoint = self.webroot / "lead.php"

        # Force Zoho mail to remain unavailable in this clone, regardless of
        # whether production credentials happen to exist on the test machine.
        source = LEAD_SOURCE.read_text(encoding="utf-8")
        original_config_reference = "'" + PRODUCTION_ZOHO_CONFIG + "'"
        self.assertEqual(source.count(original_config_reference), 1)
        isolated_config = self.sandbox / "not-a-real-zoho-config.json"
        self.endpoint.write_text(
            source.replace(original_config_reference, "'" + str(isolated_config) + "'"),
            encoding="utf-8",
        )

        php = shutil.which("php")
        if not php:
            self.skipTest("PHP CLI is required for lead.php HTTP regression tests")
        self.port = unused_port()
        self.server = subprocess.Popen(
            [php, "-S", f"127.0.0.1:{self.port}", "-t", str(self.webroot)],
            cwd=self.webroot,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._wait_for_server()

    def tearDown(self):
        if getattr(self, "server", None) is not None:
            self.server.terminate()
            try:
                self.server.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server.kill()
                self.server.wait(timeout=3)
        if getattr(self, "temp_dir", None) is not None:
            self.temp_dir.cleanup()

    def _wait_for_server(self):
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if self.server.poll() is not None:
                self.fail(f"Temporary PHP server exited with status {self.server.returncode}")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                    return
            except OSError:
                time.sleep(0.05)
        self.fail("Temporary PHP server did not start")

    def post(self, body, content_type="application/json"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request(
            "POST",
            "/lead.php",
            body=body,
            headers={"Content-Type": content_type},
        )
        response = connection.getresponse()
        status = response.status
        response_body = response.read()
        connection.close()
        payload = json.loads(response_body.decode("utf-8"))
        self.assertNotIn("debug", payload)
        return status, payload

    @staticmethod
    def studio_payload(**overrides):
        payload = {
            "_form": "studio",
            "name": "Test Contact",
            "company": "Test Company",
            "email": "contact@example.test",
            "service": "web",
            "description": "A test project description.",
            "budget": "under 1000",
            "website": "",
        }
        payload.update(overrides)
        return payload

    def saved_leads_path(self):
        return self.sandbox / ".codehouse-leads" / "leads.jsonl"

    def test_malformed_json_is_rejected(self):
        status, payload = self.post(b'{"_form":')
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_payload")
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["saved"])

    def test_studio_required_fields_and_email_are_validated(self):
        missing_name = self.studio_payload()
        del missing_name["name"]
        status, payload = self.post(json.dumps(missing_name))
        self.assertEqual(status, 422)
        self.assertFalse(payload["saved"])

        missing_email = self.studio_payload()
        del missing_email["email"]
        status, payload = self.post(json.dumps(missing_email))
        self.assertEqual(status, 422)
        self.assertFalse(payload["saved"])

        invalid_email = self.studio_payload(email="not-an-email")
        status, payload = self.post(json.dumps(invalid_email))
        self.assertEqual(status, 422)
        self.assertFalse(payload["saved"])
        self.assertFalse(self.saved_leads_path().exists())

    def test_description_uses_unicode_character_minimum(self):
        status, payload = self.post(json.dumps(self.studio_payload(description="αβγδεζηθ")))
        self.assertEqual(status, 422)
        self.assertFalse(payload["saved"])

        status, payload = self.post(json.dumps(self.studio_payload(description="αβγδεζηθικ")))
        self.assertEqual(status, 202)
        self.assertEqual(payload, {"ok": True, "saved": True, "mail": False})

    def test_studio_honeypot_is_rejected_without_success(self):
        status, payload = self.post(json.dumps(self.studio_payload(website="bot-filled")))
        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["saved"])
        self.assertFalse(self.saved_leads_path().exists())

    def test_oversized_request_is_rejected(self):
        status, payload = self.post(b"x" * 32769)
        self.assertEqual(status, 413)
        self.assertEqual(payload["error"], "payload_too_large")
        self.assertFalse(payload["saved"])

    def test_studio_submission_is_persisted_and_mail_failure_is_explicit(self):
        status, payload = self.post(json.dumps(self.studio_payload()))
        self.assertEqual(status, 202)
        self.assertEqual(payload, {"ok": True, "saved": True, "mail": False})

        saved_path = self.saved_leads_path()
        self.assertTrue(saved_path.is_file())
        self.assertEqual(saved_path.parent, self.sandbox / ".codehouse-leads")
        self.assertFalse((self.webroot / ".codehouse-leads").exists())
        self.assertEqual(saved_path.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(saved_path.stat().st_mode & 0o777, 0o600)
        records = [json.loads(line) for line in saved_path.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["_form"], "studio")
        self.assertEqual(records[0]["email"], "contact@example.test")
        self.assertNotIn("website", records[0])

    def test_legacy_name_and_phone_are_preserved(self):
        legacy = {
            "name": "Legacy Contact",
            "phone": "+30 6900000000",
            "email": "",
            "needs": "Website",
        }
        status, payload = self.post(json.dumps(legacy))
        self.assertEqual(status, 202)
        self.assertEqual(payload, {"ok": True, "saved": True, "mail": False})

        record = json.loads(self.saved_leads_path().read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(record["name"], legacy["name"])
        self.assertEqual(record["phone"], legacy["phone"])
        self.assertEqual(record["needs"], legacy["needs"])

    def test_rate_limit_rejects_seventh_valid_submission(self):
        for _ in range(6):
            status, payload = self.post(json.dumps(self.studio_payload()))
            self.assertEqual(status, 202)
            self.assertEqual(payload, {"ok": True, "saved": True, "mail": False})

        status, payload = self.post(json.dumps(self.studio_payload()))
        self.assertEqual(status, 429)
        self.assertEqual(payload["error"], "rate_limited")
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["saved"])
        self.assertEqual(len(self.saved_leads_path().read_text(encoding="utf-8").splitlines()), 6)

    def test_storage_symlink_is_rejected(self):
        link = self.sandbox / ".codehouse-leads"
        target = self.sandbox / "external-target"
        target.mkdir()
        try:
            link.symlink_to(target, target_is_directory=True)
        except OSError as error:
            self.skipTest(f"Symlink creation is unavailable: {error}")

        status, payload = self.post(json.dumps(self.studio_payload()))
        self.assertEqual(status, 500)
        self.assertEqual(payload["error"], "storage_unavailable")
        self.assertFalse(payload["saved"])
        self.assertFalse((target / "leads.jsonl").exists())

    def test_get_still_redirects_to_offer(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request("GET", "/lead.php")
        response = connection.getresponse()
        response.read()
        connection.close()
        self.assertEqual(response.status, 301)
        self.assertEqual(response.getheader("Location"), "/prosfora/")


if __name__ == "__main__":
    unittest.main()