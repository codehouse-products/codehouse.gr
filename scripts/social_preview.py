#!/usr/bin/env python3
"""Use a real loading-film frame for the two homepage sharing cards."""
import html
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
IMAGE_PATH = "assets/studio/images/codehouse-loading-preview.jpg"
IMAGE_URL = "https://codehouse.gr/" + IMAGE_PATH


def update_home_preview(source, language):
    alt = (
        "Codehouse — καρέ από το βίντεο με το μολύβι και το χειρόγραφο λογότυπο CH."
        if language == "el" else
        "Codehouse — a frame from the graphite film with the hand-drawn CH logo."
    )
    # Keep page-specific titles, descriptions, canonical URLs and body intact.
    pattern = r'<meta\b(?=[^>]*\b(?:property|name)=["\'](?:og:image(?::[^"\']*)?|twitter:card|twitter:image(?::[^"\']*)?)["\'])[^>]*>'
    source = re.sub(pattern, "", source, flags=re.I)
    tags = (
        f'<meta property="og:image" content="{IMAGE_URL}">'
        f'<meta property="og:image:secure_url" content="{IMAGE_URL}">'
        '<meta property="og:image:type" content="image/jpeg">'
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="630">'
        f'<meta property="og:image:alt" content="{html.escape(alt, quote=True)}">'
        '<meta name="twitter:card" content="summary_large_image">'
        f'<meta name="twitter:image" content="{IMAGE_URL}">'
        f'<meta name="twitter:image:alt" content="{html.escape(alt, quote=True)}">'
    )
    if "</head>" not in source:
        raise ValueError("Homepage has no closing head")
    return source.replace("</head>", tags + "</head>", 1)


def main():
    for filename, language in (("index.html", "el"), ("en/index.html", "en")):
        path = ROOT / filename
        path.write_text(update_home_preview(path.read_text(), language))
    print("Updated Greek and English homepage sharing metadata")


if __name__ == "__main__":
    main()
