#!/usr/bin/env python3
"""SEO overrides must remain separate from visible page content and fallbacks."""
import ast
import html
import json
from pathlib import Path
import re
import unittest
from seo_metadata import replace_metadata

ROOT = Path(__file__).resolve().parents[1]


class MetadataTest(unittest.TestCase):
    def test_generator_overrides_and_fallbacks(self):
        tree = ast.parse((ROOT / "scripts/generate-studio.py").read_text())
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "document")
        data = json.loads((ROOT / "assets/studio/data.json").read_text())
        scope = {
            "DATA": data, "esc": lambda s: html.escape(str(s), quote=True),
            "route": lambda p, lang: "/en" + p if lang == "en" else p,
            "page_url": lambda p, lang: "/en" + p if lang == "en" else p,
            "asset_prefix": lambda d: "../" * d,
            "header": lambda *args: "", "footer": lambda *args: "",
        }
        exec(compile(ast.Module(body=[func], type_ignores=[]), "<document>", "exec"), scope)
        targets = list(data["pages"].items()) + [
            (f'/services/{s["slug"]}/', s) for s in data["services"]
        ]
        for path, entry in targets:
            for lang in ("el", "en"):
                with self.subTest(path=path, lang=lang):
                    doc = scope["document"](path, lang, "Fallback", "Fallback description", "<h1>Untouched</h1>", 1)
                    self.assertIn(html.escape(entry["seoTitle"][lang]) + " · Codehouse</title>", doc)
                    self.assertEqual(doc.count('content="' + html.escape(entry["seoDescription"][lang]) + '"'), 2)
                    self.assertIn("<h1>Untouched</h1>", doc)
                    self.assertLessEqual(len(entry["seoDescription"]["en"]), 155)
        data["pages"] = {}
        for service in data["services"]:
            service.pop("seoTitle", None)
            service.pop("seoDescription", None)
        for path in ("/", "/services/web-design/", "/studio/"):
            doc = scope["document"](path, "el", "Fallback", "Fallback description", "", 1)
            self.assertIn("<title>Fallback · Codehouse</title>", doc)
            self.assertIn('name="description" content="Fallback description"', doc)

    def test_replacement_changes_only_four_fields(self):
        original = '''<head><title>Old</title><meta name="description" content="Old">
<meta property="og:title" content="Old"><meta property="og:description" content="Old">
<meta property="og:image" content="/keep.png"><link rel="canonical" href="/keep/">
<style>h1 {color:red}</style></head><body><h1>Keep me</h1></body>'''
        updated = replace_metadata(original, "New & title", "New description")
        pattern = r'<title>.*?</title>|<meta (?:name="description"|property="og:(?:title|description)") content="[^"]*">'
        self.assertEqual(re.sub(pattern, "", original), re.sub(pattern, "", updated))
        self.assertEqual(updated, replace_metadata(updated, "New & title", "New description"))


if __name__ == "__main__":
    unittest.main()
