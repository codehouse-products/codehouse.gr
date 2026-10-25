#!/usr/bin/env python3
"""Protect individual bilingual article generation and publication separation."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from build_editorial_article import ROOT, build, MARKER, word_count

SLUG = os.environ.get("EDITORIAL_SLUG", "pos-na-epilexeis-etaireia-seo-geo")


class ArticleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        source = ROOT / f"editorial/articles/{SLUG}.json"
        self.document = json.loads(source.read_text())
        paths = [
            source.relative_to(ROOT), Path("contact/index.html"), Path("en/contact/index.html"),
            Path("blog/index.html"), Path("en/blog/index.html"), Path("sitemap.xml"),
            Path("editorial/queue.json"), Path("editorial/published.json"),
        ]
        for document in (self.document, self.document["en"]):
            paths.extend(Path(item["url"].strip("/")) / "index.html" for item in document["related"])
        for path in paths:
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, destination)

    def test_source_quality(self):
        for document in (self.document, self.document["en"]):
            self.assertLessEqual(len(document["title"]), 60)
            self.assertLessEqual(len(document["description"]), 155)
            self.assertGreaterEqual(word_count(document), 1000)
            self.assertEqual(len(document["faq"]), 6)
            self.assertTrue(any(section.get("steps") for section in document["sections"]))
            self.assertFalse(document["include_budget"])

    def test_generation_is_idempotent_and_does_not_consume_queue(self):
        before = {name: (self.root / f"editorial/{name}.json").read_bytes() for name in ("queue", "published")}
        build(SLUG, self.root)
        def snapshot():
            return {p.relative_to(self.root): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob("*") if p.is_file()}
        first = snapshot()
        build(SLUG, self.root)
        self.assertEqual(first, snapshot())
        for name, content in before.items():
            self.assertEqual(content, (self.root / f"editorial/{name}.json").read_bytes())
        for prefix in ("", "en/"):
            page = (self.root / f"{prefix}blog/{SLUG}/index.html").read_text()
            self.assertTrue(page.startswith(MARKER))
            self.assertEqual(len(re.findall(r"<h1\b", page)), 1)
            self.assertIn('action="/lead.php"', page)
            self.assertIn("data-contact-form", page)
            self.assertNotIn('name="budget"', page)
            self.assertIn(f'href="/{prefix}seo/"', page)
            self.assertIn(f'href="/{prefix}contact/"', page)
            schemas = [json.loads(text) for text in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page)]
            article = next(schema for schema in schemas if schema.get("@type") == "Article")
            self.assertEqual(article["dateModified"], self.document["dateModified"])
            faq = next(schema for schema in schemas if schema.get("@type") == "FAQPage")
            self.assertEqual(len(faq["mainEntity"]), 6)
            listing = (self.root / f"{prefix}blog/index.html").read_text()
            self.assertEqual(listing.count(f'href="/{prefix}blog/{SLUG}/"'), 1)

    def test_invalid_translation_does_not_write_public_pages(self):
        self.document["en"]["description"] = "too short"
        (self.root / f"editorial/articles/{SLUG}.json").write_text(json.dumps(self.document))
        before = (self.root / "blog/index.html").read_bytes()
        with self.assertRaises(ValueError):
            build(SLUG, self.root)
        self.assertEqual(before, (self.root / "blog/index.html").read_bytes())
        self.assertFalse((self.root / f"blog/{SLUG}/index.html").exists())


if __name__ == "__main__":
    unittest.main()
