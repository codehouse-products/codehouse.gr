#!/usr/bin/env python3
"""Protect homepage sharing artwork without modifying the visible website."""
import re
import unittest
from PIL import Image
from social_preview import ROOT, IMAGE_PATH, IMAGE_URL, update_home_preview


class SocialPreviewTest(unittest.TestCase):
    def test_jpeg_image(self):
        with Image.open(ROOT / IMAGE_PATH) as image:
            self.assertEqual(image.format, "JPEG")
            self.assertEqual(image.size, (1200, 630))
        self.assertLess((ROOT / IMAGE_PATH).stat().st_size, 1024 * 1024)

    def test_homepages(self):
        for filename, language in (("index.html", "el"), ("en/index.html", "en")):
            with self.subTest(page=filename):
                source = (ROOT / filename).read_text()
                self.assertEqual(source, update_home_preview(source, language))
                self.assertEqual(source.count(f'<meta property="og:image" content="{IMAGE_URL}">'), 1)
                self.assertIn('name="twitter:card" content="summary_large_image"', source)
                self.assertIn(f'name="twitter:image" content="{IMAGE_URL}"', source)
                self.assertNotIn('property="og:image" content="https://codehouse.gr/assets/studio/images/codehouse-desktop.webp"', source)

    def test_only_image_metadata_changes(self):
        original = (
            '<head><title>Keep title</title><meta name="description" content="Keep description">'
            '<meta property="og:title" content="Keep OG title"><meta property="og:image" content="/old.webp">'
            '</head><body><h1>Keep H1</h1><video src="/keep.mp4"></video></body>'
        )
        updated = update_home_preview(original, "el")
        pattern = r'<meta\b(?=[^>]*\b(?:property|name)="(?:og:image(?::[^"]*)?|twitter:card|twitter:image(?::[^"]*)?)")[^>]*>'
        self.assertEqual(re.sub(pattern, "", original), re.sub(pattern, "", updated))


if __name__ == "__main__":
    unittest.main()
