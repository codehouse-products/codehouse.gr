#!/usr/bin/env python3
"""Assert article visibility, metadata and existing lead-form contract."""
import argparse
from datetime import datetime
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET


class Article(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.h1 = 0
        self.canonical = None
        self.inputs = set()
        self.form = None
        self.scripts = []
        self.schema = []
        self.in_json = False
        self.json_buffer = ""
        self.links = []
        self.assets = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonical = attrs.get("href")
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag in {"input", "select", "textarea"}:
            self.inputs.add(attrs.get("name"))
        if tag == "form" and "data-contact-form" in attrs:
            self.form = attrs
        if tag == "script":
            if attrs.get("src"):
                self.scripts.append(attrs["src"])
            self.in_json = attrs.get("type") == "application/ld+json"
            self.json_buffer = ""
        if tag in {"script", "img", "link"}:
            asset = attrs.get("src", attrs.get("href", ""))
            if asset.startswith("/assets/"):
                self.assets.append(asset)

    def handle_data(self, data):
        if self.in_json:
            self.json_buffer += data

    def handle_endtag(self, tag):
        if tag == "script" and self.in_json:
            self.schema.append(json.loads(self.json_buffer))
            self.in_json = False


def verify(source, report):
    source = Path(source)
    slug = report["slug"]
    url = f"https://codehouse.gr/blog/{slug}/"
    text = (source / f"blog/{slug}/index.html").read_text()
    article = Article(text)
    assert article.h1 == 1
    assert article.canonical == url
    assert article.form and article.form.get("action") == "/lead.php"
    assert article.form.get("method") == "post"
    assert article.form.get("data-locale") == "el"
    assert {"name", "email", "description", "service", "website"} <= article.inputs
    assert "/assets/studio/studio.js" in article.scripts
    assert "/assets/studio/privacy.js" in article.scripts
    assert "/aporrito/" in article.links
    assert all((source / asset.lstrip("/")).is_file() for asset in article.assets)
    schemas = {item["@type"]: item for item in article.schema if "@type" in item}
    assert {"BlogPosting", "BreadcrumbList"} <= schemas.keys()
    post = schemas["BlogPosting"]
    assert post["mainEntityOfPage"]["@id"] == url
    assert post["inLanguage"] == "el-GR"
    assert datetime.fromisoformat(post["datePublished"]).tzinfo is not None
    assert "/en/blog/" in article.links
    assert f"/en/blog/{slug}/" not in article.links
    assert f'href="/blog/{slug}/"' in (source / "blog/index.html").read_text()
    locs = [item.text for item in ET.parse(source / "sitemap.xml").iter()
            if item.tag.endswith("}loc")]
    assert locs.count(url) == 1
    for href in article.links:
        parts = urlsplit(href)
        if parts.path.startswith("/") and not parts.netloc:
            path = source / parts.path.lstrip("/")
            if parts.path.endswith("/"):
                path /= "index.html"
            assert path.is_file(), href
    print("PASS: article URL, Blog card, sitemap, sources, schema and real contact form.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    verify(args.source, json.loads(Path(args.report).read_text()))


if __name__ == "__main__":
    main()
