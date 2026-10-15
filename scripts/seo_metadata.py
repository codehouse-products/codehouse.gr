"""Metadata-only updates shared by full generation and safe partial regeneration."""
import html
import re


def replace_metadata(source, title, description):
    values = {
        "title": f"<title>{html.escape(title, quote=True)}</title>",
        "description": f'<meta name="description" content="{html.escape(description, quote=True)}">',
        "og:title": f'<meta property="og:title" content="{html.escape(title, quote=True)}">',
        "og:description": f'<meta property="og:description" content="{html.escape(description, quote=True)}">',
    }
    for key, replacement in values.items():
        pattern = (r"<title\b[^>]*>.*?</title>" if key == "title" else
                   rf'<meta\b(?=[^>]*\b(?:name|property)=["\']{re.escape(key)}["\'])[^>]*>')
        source, count = re.subn(pattern, lambda _: replacement, source, flags=re.I | re.S)
        if count == 0:
            source = source.replace("</head>", replacement + "</head>", 1)
    return source
