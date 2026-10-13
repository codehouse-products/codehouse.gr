#!/usr/bin/env python3
"""Prepare at most one reviewed Greek article per Athens calendar day."""
import argparse
from datetime import datetime
import html
import json
from pathlib import Path
import re
from difflib import SequenceMatcher
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET

from editorial_view import render_article

TZ = ZoneInfo("Europe/Athens")
NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
BASE = "https://codehouse.gr"
STATE_PATH = "editorial/published.json"
BEGIN = "<!-- daily-editorial:start -->"
END = "<!-- daily-editorial:end -->"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


class EditorialError(ValueError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def prose(document):
    parts = [document["title"], document["answer"]]
    for section in document["sections"]:
        parts.extend([section["heading"], *section["paragraphs"], *section.get("bullets", [])])
    for faq in document["faq"]:
        parts.extend([faq["question"], faq["answer"]])
    return " ".join(parts)


def validate(document, source, previous=()):
    if not SLUG.fullmatch(document["slug"]) or len(document["slug"]) > 85:
        raise EditorialError("Invalid descriptive article slug")
    if not 35 <= len(document["title"]) <= 110:
        raise EditorialError("Article title length is invalid")
    if not 100 <= len(document["description"]) <= 190:
        raise EditorialError("Article meta description length is invalid")
    if not 30 <= len(document["answer"].split()) <= 95:
        raise EditorialError("Article needs a concise direct answer")
    if len(document["sections"]) < 5 or len(document["faq"]) < 4:
        raise EditorialError("Article needs substantive sections and FAQs")
    text = prose(document)
    if len(text.split()) < 550:
        raise EditorialError("Article has insufficient substantive content")
    if re.search(r"<[^>]+>", text):
        raise EditorialError("Raw HTML is not allowed in editorial prose")
    if re.search(r"εγγυόμαστε.*(?:θέση|κατάταξη)|εγγυημένη πρώτη θέση", text, re.I):
        raise EditorialError("Unsubstantiated ranking guarantee")
    urls = [item["url"] for item in document["sources"]]
    if len(set(urls)) < 2:
        raise EditorialError("At least two distinct authoritative sources are required")
    for url in urls:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "developers.google.com", "support.google.com", "www.w3.org", "web.dev"
        } or parsed.username or parsed.password:
            raise EditorialError("Source URL is outside the reviewed publisher allowlist")
    for item in document["related"]:
        path = item["url"]
        if not path.startswith("/") or ".." in path or "?" in path or "#" in path:
            raise EditorialError("Invalid related article path")
        if not (source / path.strip("/") / "index.html").is_file():
            raise EditorialError("Related link does not exist")
    for old in previous:
        if old["slug"] == document["slug"] or old["title"].casefold() == document["title"].casefold():
            raise EditorialError("Duplicate editorial topic or slug")
        if SequenceMatcher(None, prose(old), text).ratio() > .82:
            raise EditorialError("Near-duplicate editorial article")


def load_queue(source):
    queue = read_json(source / "editorial/queue.json")
    if queue.get("timezone") != "Europe/Athens" or queue.get("publish_time") != "10:00":
        raise EditorialError("Unexpected publication timezone or time")
    documents = []
    for slug in queue["articles"]:
        if not isinstance(slug, str) or not SLUG.fullmatch(slug):
            raise EditorialError("Unsafe queue path")
        document = read_json(source / f"editorial/articles/{slug}.json")
        if document["slug"] != slug:
            raise EditorialError("Queue entry and article slug differ")
        validate(document, source, documents)
        documents.append(document)
    return documents


def blog_with_cards(source, records):
    blog = (source / "blog/index.html").read_text()
    if blog.count(BEGIN) != blog.count(END) or blog.count(BEGIN) > 1:
        raise EditorialError("Blog daily card markers are invalid")
    cards = []
    for record in reversed(records):
        cards.append(
            f'<a class="bcard" href="/blog/{record["slug"]}/">'
            f'<span class="tag">{html.escape(record["category"])}</span>'
            f'<h2>{html.escape(record["title"])}</h2>'
            f'<p>{html.escape(record["description"])}</p>'
            f'<span class="meta"><time datetime="{record["published_at"]}">'
            f'{record["date"]}</time><span class="read">Διάβασε →</span></span></a>'
        )
    block = BEGIN + "\n" + "\n".join(cards) + "\n" + END
    if BEGIN in blog:
        blog = blog[:blog.index(BEGIN)] + block + blog[blog.index(END) + len(END):]
    else:
        match = re.search(r'<main\b[^>]*class="bgrid"[^>]*>', blog)
        if not match:
            raise EditorialError("The existing Blog listing was not found")
        blog = blog[:match.end()] + "\n" + block + blog[match.end():]
    return blog


def sitemap_with_article(source, slug, published_date, retry=False):
    ET.register_namespace("", NS)
    root = ET.fromstring((source / "sitemap.xml").read_bytes())
    url = f"{BASE}/blog/{slug}/"
    entries = [item for item in root if item.findtext(f"{{{NS}}}loc") == url]
    if entries and not retry:
        raise EditorialError("New article URL is already in the sitemap")
    if len(entries) > 1:
        raise EditorialError("Duplicate article sitemap URL")
    if entries:
        entry = entries[0]
        for child in list(entry):
            if child.tag == f"{{{NS}}}lastmod":
                entry.remove(child)
    else:
        entry = ET.SubElement(root, f"{{{NS}}}url")
        ET.SubElement(entry, f"{{{NS}}}loc").text = url
    ET.SubElement(entry, f"{{{NS}}}lastmod").text = published_date
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n"


def prepare(source, now):
    source = Path(source).resolve(strict=True)
    if now.tzinfo is None:
        raise EditorialError("The publication clock must include a timezone")
    now = now.astimezone(TZ)
    today = now.date().isoformat()
    documents = load_queue(source)
    state_file = source / STATE_PATH
    records = read_json(state_file) if state_file.exists() else []
    if len({r["slug"] for r in records}) != len(records) or len({r["date"] for r in records}) != len(records):
        raise EditorialError("Publication history contains duplicate days or slugs")
    if any(r["date"] > today for r in records):
        raise EditorialError("Publication history contains a future date")
    if any(r.get("status") not in {"pending", "published"} for r in records):
        raise EditorialError("Invalid publication confirmation status")
    pending = [r for r in records if r["status"] == "pending"]
    if len(pending) > 1 or (pending and pending[0] != records[-1]):
        raise EditorialError("Invalid pending publication order")
    published = {r["slug"] for r in records}
    remaining = [d for d in documents if d["slug"] not in published]
    if now.hour < 10:
        return {"ready": False, "reason": "before_publication_time", "remaining": len(remaining)}
    if any(r["date"] == today and r["status"] == "published" for r in records):
        return {"ready": False, "reason": "already_published_today", "remaining": len(remaining)}
    if pending and pending[0]["date"] == today:
        record = pending[0]
        path = source / f'blog/{record["slug"]}/index.html'
        if not path.is_file() or f"/blog/{record['slug']}/" not in (source / "blog/index.html").read_text():
            raise EditorialError("Today's publication files are missing")
        # Only a verified server apply confirms consumption of a queue entry.
        return {"ready": True, "reason": "retry_same_day", "slug": record["slug"],
                "remaining": len(remaining), "changed": []}
    if not remaining and not pending:
        return {"ready": False, "reason": "queue_exhausted", "remaining": 0}
    if pending:
        matches = [d for d in documents if d["slug"] == pending[0]["slug"]]
        if not matches:
            raise EditorialError("Pending article is missing from the reviewed queue")
        document = matches[0]
        records.remove(pending[0])
    else:
        document = remaining[0]
    slug = document["slug"]
    destination = source / f"blog/{slug}/index.html"
    if destination.exists() and not pending:
        raise EditorialError("Refusing to overwrite an existing article URL")
    published_at = now.replace(microsecond=0).isoformat()
    record = {key: document[key] for key in ("slug", "title", "description", "category")}
    record.update({"date": today, "published_at": published_at, "status": "pending"})
    records.append(record)
    # Build every result before touching the workspace.
    payload = {
        f"blog/{slug}/index.html": render_article(document, published_at, source),
        "blog/index.html": blog_with_cards(source, records),
        "sitemap.xml": sitemap_with_article(source, slug, today, retry=bool(pending)),
        STATE_PATH: json.dumps(records, ensure_ascii=False, indent=2) + "\n",
    }
    for relative, content in payload.items():
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return {"ready": True, "reason": "retry_previous_day" if pending else "new_article", "slug": slug,
            "remaining": len(remaining) if pending else len(remaining) - 1, "changed": sorted(payload)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        report = prepare(args.source, datetime.now(TZ))
    except (EditorialError, KeyError, OSError, ValueError) as exc:
        parser.exit(1, f"Editorial preparation refused: {exc}\n")
    Path(args.report).write_text(json.dumps(report) + "\n")
    if report["remaining"] <= 2:
        print(f'::warning::Editorial queue has {report["remaining"]} articles remaining; replenish reviewed content.')
    print(json.dumps(report))


if __name__ == "__main__":
    main()
