#!/usr/bin/env python3
"""Regression tests for the reviewed daily queue; never contact a live lead API."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from editorial_commit import acknowledge
from editorial_queue import EditorialError, load_queue, prepare, prose, validate
from editorial_view import render_article
from verify_editorial import Article, verify

ROOT = Path(__file__).resolve().parent.parent


class EditorialQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.source = Path(self.temp.name) / "site"
        self.source.mkdir()
        for item in ROOT.iterdir():
            if item.name in {"editorial", "blog"}:
                shutil.copytree(item, self.source / item.name)
            elif item.name == "sitemap.xml":
                shutil.copy(item, self.source / item.name)
            elif not item.name.startswith("."):
                (self.source / item.name).symlink_to(item, target_is_directory=item.is_dir())
        self.now = datetime.fromisoformat("2026-10-14T10:00:00+03:00")
        self.documents = load_queue(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def test_seven_original_source_backed_articles(self):
        self.assertEqual(len(self.documents), 7)
        self.assertTrue(all(len(prose(d).split()) >= 550 for d in self.documents))

    def test_before_ten_never_publishes(self):
        original = (self.source / "sitemap.xml").read_bytes()
        report = prepare(self.source, self.now.replace(hour=9, minute=59))
        self.assertFalse(report["ready"])
        self.assertEqual((self.source / "sitemap.xml").read_bytes(), original)
        self.assertEqual(json.loads((self.source / "editorial/published.json").read_text()), [])

    def test_first_article_visible_and_complete(self):
        report = prepare(self.source, self.now)
        verify(self.source, report)
        self.assertEqual(len(report["changed"]), 4)
        self.assertEqual(report["remaining"], 6)

    def test_unconfirmed_same_day_retries_same_article(self):
        first = prepare(self.source, self.now)
        second = prepare(self.source, self.now + timedelta(minutes=30))
        self.assertEqual(first["slug"], second["slug"])
        self.assertEqual(second["changed"], [])
        self.assertEqual(second["reason"], "retry_same_day")

    def test_confirmation_prevents_second_article_same_day(self):
        first = prepare(self.source, self.now)
        acknowledge(self.source, first["slug"])
        second = prepare(self.source, self.now + timedelta(minutes=30))
        self.assertFalse(second["ready"])
        self.assertEqual(second["reason"], "already_published_today")

    def test_failed_server_apply_does_not_skip_article_next_day(self):
        first = prepare(self.source, self.now)
        second = prepare(self.source, self.now + timedelta(days=1))
        self.assertEqual(first["slug"], second["slug"])
        self.assertEqual(second["reason"], "retry_previous_day")
        records = json.loads((self.source / "editorial/published.json").read_text())
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["date"], "2026-10-15")
        verify(self.source, second)

    def test_next_day_selects_next_only_after_confirmation(self):
        first = prepare(self.source, self.now)
        acknowledge(self.source, first["slug"])
        second = prepare(self.source, self.now + timedelta(days=1))
        self.assertNotEqual(first["slug"], second["slug"])
        self.assertEqual(second["remaining"], 5)

    def test_exhaustion_stops_and_preserves_existing_blog(self):
        original_blog = (self.source / "blog/index.html").read_text()
        for day in range(7):
            report = prepare(self.source, self.now + timedelta(days=day))
            verify(self.source, report)
            acknowledge(self.source, report["slug"])
        report = prepare(self.source, self.now + timedelta(days=7))
        self.assertFalse(report["ready"])
        self.assertEqual(report["reason"], "queue_exhausted")
        blog = (self.source / "blog/index.html").read_text()
        self.assertEqual(blog.count("<!-- daily-editorial:start -->"), 1)
        for name in ["kataskeyi-eshop-ellada-kostos", "qr-menou-estiatorio-kafe"]:
            self.assertEqual(blog.count(f'href="/blog/{name}/"'), original_blog.count(f'href="/blog/{name}/"'))

    def test_winter_clock_at_ten_athens(self):
        before = prepare(self.source, datetime.fromisoformat("2026-11-01T07:59:00+00:00"))
        self.assertFalse(before["ready"])
        after = prepare(self.source, datetime.fromisoformat("2026-11-01T08:00:00+00:00"))
        self.assertTrue(after["ready"])
        record = json.loads((self.source / "editorial/published.json").read_text())[0]
        self.assertTrue(record["published_at"].endswith("+02:00"))

    def test_summer_clock_at_ten_athens(self):
        before = prepare(self.source, datetime.fromisoformat("2026-07-01T06:59:00+00:00"))
        self.assertFalse(before["ready"])
        after = prepare(self.source, datetime.fromisoformat("2026-07-01T07:00:00+00:00"))
        self.assertTrue(after["ready"])

    def test_naive_clock_refused(self):
        with self.assertRaises(EditorialError):
            prepare(self.source, datetime(2026, 10, 14, 10))

    def test_collision_never_overwrites_existing_page(self):
        path = self.source / f'blog/{self.documents[0]["slug"]}/index.html'
        path.parent.mkdir()
        path.write_text("Existing page")
        with self.assertRaises(EditorialError):
            prepare(self.source, self.now)
        self.assertEqual(path.read_text(), "Existing page")

    def test_missing_related_url_refused(self):
        doc = deepcopy(self.documents[0])
        doc["related"][0]["url"] = "/missing-guide/"
        with self.assertRaises(EditorialError):
            validate(doc, self.source)

    def test_untrusted_source_refused(self):
        doc = deepcopy(self.documents[0])
        doc["sources"][0]["url"] = "https://example.com/fake-report"
        with self.assertRaises(EditorialError):
            validate(doc, self.source)

    def test_duplicate_topic_refused(self):
        with self.assertRaises(EditorialError):
            validate(self.documents[0], self.source, [self.documents[0]])

    def test_queue_path_traversal_refused(self):
        path = self.source / "editorial/queue.json"
        queue = json.loads(path.read_text())
        queue["articles"][0] = "../contact/index"
        path.write_text(json.dumps(queue))
        with self.assertRaises(EditorialError):
            load_queue(self.source)

    def test_renderer_escapes_content_and_json(self):
        doc = deepcopy(self.documents[0])
        doc["sections"][0]["paragraphs"][0] = '<img src=x onerror="alert(1)">'
        doc["title"] = "Safe title </script><script>alert(1)</script>"
        rendered = render_article(doc, self.now.isoformat(), self.source)
        self.assertNotIn("<img src=x", rendered)
        self.assertNotIn("<script>alert(1)", rendered)
        Article(rendered)

    def test_invalid_blog_markers_do_not_partially_write(self):
        (self.source / "blog/index.html").write_text("<!-- daily-editorial:start -->")
        with self.assertRaises(EditorialError):
            prepare(self.source, self.now)
        self.assertFalse((self.source / f'blog/{self.documents[0]["slug"]}/index.html').exists())
        self.assertEqual(json.loads((self.source / "editorial/published.json").read_text()), [])

    def test_acknowledgment_requires_matching_pending_article(self):
        with self.assertRaises(RuntimeError):
            acknowledge(self.source, "not-an-article")
        report = prepare(self.source, self.now)
        with self.assertRaises(RuntimeError):
            acknowledge(self.source, "other-article")
        acknowledge(self.source, report["slug"])
        with self.assertRaises(RuntimeError):
            acknowledge(self.source, report["slug"])


if __name__ == "__main__":
    unittest.main()
