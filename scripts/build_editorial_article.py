#!/usr/bin/env python3
"""Build one sourced bilingual editorial article; do not consume the daily queue."""
import argparse
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from editorial_queue import NS, validate
from editorial_view import render_article

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://codehouse.gr"
MARKER = "<!-- generated-by: build_editorial_article.py -->"


def word_count(document):
    """Count article prose and visible link labels, excluding SEO metadata."""
    parts = [document["answer"]]
    for section in document["sections"]:
        parts.extend([section["heading"], *section.get("paragraphs", []),
                      *section.get("steps", []), *section.get("bullets", [])])
    for item in document["faq"]:
        parts.extend([item["question"], item["answer"]])
    visible = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\1", " ".join(parts))
    return len(re.findall(r"\b[\wά-ώΆ-Ώ]+(?:['’][\wά-ώΆ-Ώ]+)*\b", visible))


def build(slug, root=ROOT):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        raise ValueError("Invalid article slug")
    source = root / "editorial/articles" / f"{slug}.json"
    document = json.loads(source.read_text(encoding="utf-8"))
    if document["slug"] != slug:
        raise ValueError("Source slug mismatch")
    published = datetime.fromisoformat(document["published_at"])
    if published.utcoffset() is None:
        raise ValueError("Publication date must contain a timezone")
    prepared = []
    for locale, prefix in (("el", ""), ("en", "/en")):
        content = document if locale == "el" else dict(document["en"], slug=slug)
        validate(content, root)
        if len(content["title"]) > 60 or len(content["description"]) > 155:
            raise ValueError("SEO title or description is too long")
        content["include_budget"] = False
        url = f"{prefix}/blog/{slug}/"
        output = root / url.strip("/") / "index.html"
        if output.exists() and not output.read_text().startswith(MARKER):
            raise ValueError(f"Refusing to overwrite an unrelated page: {url}")
        alternate = f"{SITE}{'/en' if locale == 'el' else ''}/blog/{slug}/"
        page = MARKER + "\n" + render_article(
            content, document["published_at"], root, locale=locale, alternate_url=alternate
        )
        start, end = f"<!-- editorial-article:{slug}:start -->", f"<!-- editorial-article:{slug}:end -->"
        label = "Διάβασε →" if locale == "el" else "Read →"
        card = (
            f'{start}\n<a class="bcard" href="{url}"><span class="tag">{escape(content["category"])}</span>'
            f'<h2>{escape(content["title"])}</h2><p>{escape(content["description"])}</p>'
            f'<span class="meta"><time datetime="{published.date().isoformat()}">'
            f'{published.strftime("%d/%m/%Y")}</time><span class="read">{label}</span></span></a>\n{end}'
        )
        listing_path = root / prefix.strip("/") / "blog/index.html"
        listing = listing_path.read_text(encoding="utf-8")
        if start in listing:
            if listing.count(start) != 1 or listing.count(end) != 1:
                raise ValueError("Ambiguous article card markers")
            listing = listing[:listing.index(start)] + card + listing[listing.index(end) + len(end):]
        else:
            match = re.search(r'<(?:main|div)\b[^>]*class="bgrid"[^>]*>', listing)
            if not match:
                raise ValueError("Blog card container not found")
            listing = listing[:match.end()] + "\n" + card + listing[match.end():]
        prepared.append((output, page, listing_path, listing, url, word_count(content)))

    # Validate everything before writing either language. Leave queue/ledger untouched.
    ET.register_namespace("", NS)
    sitemap_path = root / "sitemap.xml"
    sitemap = ET.fromstring(sitemap_path.read_bytes())
    updated_urls = [item[4] for item in prepared] + ["/blog/", "/en/blog/"]
    for url in updated_urls:
        matches = [entry for entry in sitemap if entry.findtext(f"{{{NS}}}loc") == SITE + url]
        if len(matches) > 1:
            raise ValueError(f"Duplicate sitemap URL: {url}")
        if matches:
            entry = matches[0]
        else:
            entry = ET.SubElement(sitemap, f"{{{NS}}}url")
            ET.SubElement(entry, f"{{{NS}}}loc").text = SITE + url
        modified = entry.find(f"{{{NS}}}lastmod")
        if modified is None:
            modified = ET.SubElement(entry, f"{{{NS}}}lastmod")
        modified.text = document["dateModified"]
    for output, page, listing_path, listing, url, words in prepared:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page, encoding="utf-8")
        listing_path.write_text(listing, encoding="utf-8")
        print(f"{url}: {words} words")
    ET.indent(sitemap, space="  ")
    sitemap_path.write_text(ET.tostring(sitemap, encoding="unicode", xml_declaration=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    build(parser.parse_args().slug)
