#!/usr/bin/env python3
"""Render the first queued article as a noindex local preview, without consumption."""
import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from editorial_queue import load_queue
from editorial_view import render_article


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="generated-artifacts/editorial-preview/index.html")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    document = load_queue(root)[0]
    page = render_article(document, datetime.now(ZoneInfo("Europe/Athens")).isoformat(), root)
    page = page.replace("<head>", '<head><meta name="robots" content="noindex, nofollow">', 1)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page)
    print("Noindex local preview created; queue and public sitemap unchanged.")


if __name__ == "__main__":
    main()
