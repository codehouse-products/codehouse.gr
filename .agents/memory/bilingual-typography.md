---
name: Bilingual typography
description: Keep Greek and English typography visually consistent without language-specific size corrections.
---

Use the same actual typeface for Greek and Latin within each typography role, including monospace labels. Do not compensate for a Latin-only typeface's Greek fallback with language-specific font-size adjustments.

**Why:** The user explicitly requested the same apparent size and style in Greek and English, authorizing a similar-looking replacement family where necessary.

**How to apply:** Preserve the heading/body hierarchy while matching corresponding roles across languages. Verify native rendered glyph coverage, not just the CSS family name. Compare semantically equivalent elements rather than the first tag of a given kind: translated and legacy markup can order labels and body copy differently.