#!/usr/bin/env python3
"""Keep public favicon declarations and raster fallbacks on the approved CH mark."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ICON_LINKS = (
    '<link rel="icon" href="/assets/img/favicon-512.png" type="image/png" sizes="512x512">'
    '<link rel="apple-touch-icon" href="/assets/img/favicon-180.png" sizes="180x180">'
)


def normalize_icons(html):
    # Correct icon tags need not be the final elements in <head>. Social
    # metadata, hreflang and noindex may legitimately follow them.
    icons = re.findall(
        r'<link\b(?=[^>]*\brel=["\'](?:icon|shortcut icon|apple-touch-icon|apple-touch-icon-precomposed)["\'])[^>]*>',
        html, flags=re.I,
    )
    if "".join(icons) == ICON_LINKS:
        return html
    html = re.sub(
        r'<link\b(?=[^>]*\brel=["\'](?:icon|shortcut icon|apple-touch-icon|apple-touch-icon-precomposed)["\'])[^>]*>',
        "", html, flags=re.I,
    )
    return html.replace("</head>", ICON_LINKS + "</head>", 1)


def build_icons():
    from PIL import Image
    import base64

    source = Image.open(ROOT / "assets/studio/logo-user-black.png").convert("RGBA")
    source = source.crop(source.getchannel("A").getbbox())
    # Retain the actual hand-drawn logo; padding protects it from circular crops.
    source.thumbnail((400, 400), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), "white")
    canvas.alpha_composite(source, ((512 - source.width) // 2, (512 - source.height) // 2))
    canvas = canvas.convert("RGB")
    for size in (16, 32, 48, 64, 96, 180, 192, 512):
        canvas.resize((size, size), Image.Resampling.LANCZOS).save(
            ROOT / f"assets/img/favicon-{size}.png"
        )
    canvas.save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    # Also replace the old SVG URL for cached pages still requesting it.
    png = base64.b64encode((ROOT / "assets/img/favicon-512.png").read_bytes()).decode()
    (ROOT / "assets/studio/favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
        f'<image width="512" height="512" href="data:image/png;base64,{png}"/></svg>'
    )


def main():
    from server_release import PUBLIC_DIRS
    build_icons()
    pages = [ROOT / "index.html"]
    for folder in PUBLIC_DIRS:
        pages.extend((ROOT / folder).rglob("*.html"))
    changed = 0
    for page in sorted(set(pages)):
        old = page.read_text()
        if "</head>" not in old:
            continue
        new = normalize_icons(old)
        if new != old:
            page.write_text(new)
            changed += 1
    print(f"Updated icons on {changed} public HTML pages")


if __name__ == "__main__":
    main()
