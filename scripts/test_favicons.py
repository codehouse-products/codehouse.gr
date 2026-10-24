#!/usr/bin/env python3
"""Check every public icon declaration and all legacy fallback image variants."""
import unittest
from pathlib import Path
from PIL import Image
from sync_favicons import ROOT, ICON_LINKS, normalize_icons
from server_release import PUBLIC_DIRS


class FaviconsTest(unittest.TestCase):
    def test_correct_icons_can_precede_other_head_metadata(self):
        source = '<html><head>' + ICON_LINKS + '<meta name="robots" content="noindex, follow"></head></html>'
        self.assertEqual(normalize_icons(source), source)

    def test_public_pages(self):
        pages = [ROOT / "index.html"]
        for folder in PUBLIC_DIRS:
            pages.extend((ROOT / folder).rglob("*.html"))
        for page in pages:
            text = page.read_text()
            if "</head>" not in text:
                continue
            with self.subTest(page=page.relative_to(ROOT)):
                self.assertIn(ICON_LINKS, text)
                self.assertEqual(text, normalize_icons(text))

    def test_raster_variants(self):
        for size in (16, 32, 48, 64, 96, 180, 192, 512):
            with self.subTest(size=size):
                im = Image.open(ROOT / f"assets/img/favicon-{size}.png").convert("RGB")
                self.assertEqual(im.size, (size, size))
                self.assertEqual(im.getpixel((0, 0)), (255, 255, 255))
                r, g, b = im.split()
                self.assertEqual(r.tobytes(), g.tobytes())
                self.assertEqual(g.tobytes(), b.tobytes())

    def test_cache_busted_icons_and_apple_touch_icon(self):
        for path, size in (
            ("assets/img/codehouse-favicon-512.png", 512),
            ("assets/img/codehouse-favicon-180.png", 180),
            ("assets/img/apple-touch-icon.png", 180),
        ):
            with self.subTest(path=path):
                im = Image.open(ROOT / path).convert("RGB")
                self.assertEqual(im.size, (size, size))
                r, g, b = im.split()
                self.assertEqual(r.tobytes(), g.tobytes())
                self.assertEqual(g.tobytes(), b.tobytes())

    def test_ico(self):
        with Image.open(ROOT / "favicon.ico") as im:
            self.assertTrue({(16, 16), (32, 32), (48, 48), (64, 64)} <= im.ico.sizes())

    def test_old_declarations_are_removed(self):
        html = '<head><link rel="shortcut icon" href="old.ico"><link rel="apple-touch-icon" href="old.png"></head>'
        self.assertEqual(normalize_icons(html), "<head>" + ICON_LINKS + "</head>")


if __name__ == "__main__":
    unittest.main()
