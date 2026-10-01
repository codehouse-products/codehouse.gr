#!/usr/bin/env python3
"""Dependency-free checks for sitemap, public links, assets and language pairs."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://codehouse.gr"
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


class Document(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links = []
        self.images = []
        self.alternates = {}
        self.canonical = None
        self.h1s = 0
        self.noindex = False
        self.ids = set()
        self.lang = None
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "html":
            self.lang = attrs.get("lang")
        if tag == "h1":
            self.h1s += 1
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "img" and attrs.get("src"):
            self.images.append(attrs)
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if tag == "link" and attrs.get("hreflang"):
            self.alternates[attrs["hreflang"]] = attrs.get("href")
        if tag == "meta" and attrs.get("name") == "robots":
            self.noindex = "noindex" in attrs.get("content", "")


def local_file(path):
    path = ROOT / unquote(path.lstrip("/"))
    return path / "index.html" if path.is_dir() else path


def main():
    urls = [e.text for e in ET.parse(ROOT / "sitemap.xml").findall(f".//{{{NS}}}loc")]
    errors = []
    docs = {}
    if len(urls) != len(set(urls)):
        errors.append("Duplicate sitemap URLs")
    for url in urls:
        path = local_file(urlsplit(url).path)
        if not path.is_file():
            errors.append(f"Missing sitemap page: {url}")
            continue
        doc = Document(path.read_text())
        docs[path] = doc
        if doc.noindex:
            errors.append(f"Noindex page in sitemap: {url}")
        if doc.canonical != url:
            errors.append(f"Wrong canonical {url}: {doc.canonical}")
        if doc.h1s != 1:
            errors.append(f"Expected one H1 {url}: {doc.h1s}")
        if urlsplit(url).path.startswith("/en/") and doc.lang != "en":
            errors.append(f"Wrong English document lang: {url}")
        for lang, alternate in doc.alternates.items():
            if not alternate.startswith(BASE):
                errors.append(f"Wrong alternate host: {url}: {alternate}")
            elif not local_file(urlsplit(alternate).path).is_file():
                errors.append(f"Missing {lang} alternate {url}: {alternate}")
    checked_links = 0
    for page, doc in list(docs.items()):
        for href in doc.links:
            parts = urlsplit(href)
            if parts.scheme not in ("", "http", "https") or parts.netloc not in ("", "codehouse.gr", "www.codehouse.gr"):
                continue
            if not parts.path:
                target = page
            elif parts.path.startswith("/"):
                target = local_file(parts.path)
            else:
                target = page.parent / unquote(parts.path)
                if target.is_dir():
                    target = target / "index.html"
            checked_links += 1
            if not target.is_file():
                errors.append(f"Broken link {page.relative_to(ROOT)}: {href}")
            elif parts.fragment and target.suffix == ".html":
                destination = docs.get(target)
                if not destination:
                    destination = Document(target.read_text())
                    docs[target] = destination
                if unquote(parts.fragment) not in destination.ids:
                    errors.append(f"Missing anchor {page.relative_to(ROOT)}: {href}")
        for image in doc.images:
            source = urlsplit(image["src"])
            if source.scheme or source.netloc:
                continue
            target = local_file(source.path) if source.path.startswith("/") else page.parent / unquote(source.path)
            if not target.is_file():
                errors.append(f"Broken image {page.relative_to(ROOT)}: {image['src']}")
            if "alt" not in image:
                errors.append(f"Missing alt {page.relative_to(ROOT)}: {image['src']}")
    if errors:
        print("\n".join(sorted(set(errors))))
        sys.exit(1)
    print(f"PASS: {len(urls)} sitemap pages, {checked_links} internal links, real language targets, local images and canonical metadata.")


if __name__ == "__main__":
    main()