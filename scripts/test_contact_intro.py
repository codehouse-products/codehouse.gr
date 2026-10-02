#!/usr/bin/env python3
"""Keep the removed contact intro out of generated routes."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContactIntroTests(unittest.TestCase):
    def test_contact_starts_with_existing_details_and_working_form_markup(self):
        for route, removed_title, removed_copy in (
            ("contact/index.html", "Ας δώσουμε μορφή στην ιδέα σου.",
             "Έχεις μια ιδέα; Ας της δώσουμε μορφή."),
            ("en/contact/index.html", "Let’s give your idea form.",
             "Have an idea? Let’s give it form."),
        ):
            with self.subTest(route=route):
                source = (ROOT / route).read_text(encoding="utf-8")
                main = re.search(r"<main\b[^>]*>(.*?)</main>", source, re.S).group(1)
                self.assertNotIn(removed_title, source)
                # The shared footer CTA is outside the removed page intro.
                self.assertNotIn(removed_copy, main)
                self.assertTrue(main.startswith('<section class="contact-layout">'))
                self.assertEqual(source.count("<h1>"), 1)
                self.assertIn('data-contact-form', source)
                for field in ("name", "company", "email", "service", "description", "budget"):
                    self.assertIn(f'name="{field}"', source)
                self.assertIn('type="submit"', source)


if __name__ == "__main__":
    unittest.main()