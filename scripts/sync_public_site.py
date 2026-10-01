#!/usr/bin/env python3
"""Synchronize real language pairs and the public sitemap after generation.

Never discover public pages by blindly crawling the repository: previews,
admin tools and form endpoints are deliberately excluded.
"""
import re
from pathlib import Path
from datetime import date
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://codehouse.gr"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
ET.register_namespace("", NS)


def route(path):
    relative = path.relative_to(ROOT).parent.as_posix()
    return "/" if relative == "." else f"/{relative}/"


def pair_html(path, greek, english):
    source = path.read_text()
    source = re.sub(r'<link\b[^>]*\bhreflang=["\'][^"\']+["\'][^>]*>\s*', "", source, flags=re.I)
    links = "\n".join(
        f'<link rel="alternate" hreflang="{lang}" href="{BASE}{url}">'
        for lang, url in (("el", greek), ("en", english), ("x-default", greek))
    )
    source = source.replace("</head>", links + "\n</head>", 1)
    # Archival navigation gets a truthful same-page switch only once the
    # translated document exists. Core studio templates already have a switch.
    if 'class="legacy-editorial-nav"' in source:
        source = re.sub(r'<!-- locale-pair -->.*?<!-- /locale-pair -->\s*', "", source, flags=re.S)
        current = "en" if route(path).startswith("/en/") else "el"
        label = "Γλώσσα" if current == "el" else "Language"
        switch = (
            f'<!-- locale-pair --><nav class="legacy-language" aria-label="{label}">'
            f'<a href="{greek}" lang="el"' + (' aria-current="page"' if current == "el" else "")
            + '>GR</a><span aria-hidden="true"> / </span>'
            f'<a href="{english}" lang="en"' + (' aria-current="page"' if current == "en" else "")
            + '>EN</a></nav><!-- /locale-pair -->'
        )
        source = source.replace('<details class="legacy-mobile-nav"', switch + '\n  <details class="legacy-mobile-nav"', 1)
    path.write_text(source)


def main():
    english_root = ROOT / "en"
    pairs = 0
    if english_root.exists():
        for english_file in sorted(english_root.rglob("index.html")):
            greek_file = ROOT / english_file.relative_to(english_root)
            if greek_file.exists():
                greek, english = route(greek_file), route(english_file)
                pair_html(greek_file, greek, english)
                pair_html(english_file, greek, english)
                pairs += 1
    sitemap = ROOT / "sitemap.xml"
    tree = ET.parse(sitemap)
    root = tree.getroot()
    existing = {url.findtext(f"{{{NS}}}loc") for url in root}
    candidates = [ROOT / "index.html"]
    for folder in ("services", "projects", "studio", "contact", "en"):
        directory = ROOT / folder
        if directory.exists():
            candidates.extend(directory.rglob("index.html"))
    added = 0
    for path in sorted(set(candidates)):
        source = path.read_text()
        if re.search(r'<meta\b[^>]*content=["\'][^"\']*noindex', source, re.I):
            continue
        url = BASE + route(path)
        if url in existing:
            continue
        entry = ET.SubElement(root, f"{{{NS}}}url")
        for key, value in (("loc", url), ("lastmod", date.today().isoformat()), ("changefreq", "monthly"), ("priority", "0.7")):
            ET.SubElement(entry, f"{{{NS}}}{key}").text = value
        existing.add(url)
        added += 1
    ET.indent(tree, space="  ")
    tree.write(sitemap, encoding="UTF-8", xml_declaration=True)
    print(f"Synced {pairs} real language pairs; added {added} public sitemap URLs; total {len(existing)}.")


if __name__ == "__main__":
    main()