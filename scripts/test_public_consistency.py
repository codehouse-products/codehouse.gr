#!/usr/bin/env python3
"""Protect shared branding/privacy coverage across indexed public routes."""
from pathlib import Path
import re
import importlib.util
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def verify_migration_safety():
    spec = importlib.util.spec_from_file_location("legacy_refresh", ROOT / "scripts/refresh_legacy.py")
    refresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(refresh)
    schema = '<script type="application/ld+json">{"description":"https://www.clarity.ms/tag/example"}</script>'
    form_script = '<script>document.querySelector("#quizForm").addEventListener("submit", sendLead);</script>'
    source = f"<html><head>{schema}</head><body>{form_script}</body></html>"
    result = refresh.unify_privacy(source)
    assert schema in result and form_script in result
    mixed = '<script>window.dataLayer = window.dataLayer || []; initializeForm();</script>'
    try:
        refresh.unify_privacy(mixed)
    except ValueError:
        pass
    else:
        raise AssertionError("Unrecognized mixed analytics/application scripts must require review")
    assert refresh.unify_privacy(result) == result
    print("PASS: migration preserves data/form scripts, rejects unknown mixed scripts and is idempotent")


def main():
    verify_migration_safety()
    locations = ET.parse(ROOT / "sitemap.xml").findall(".//{*}loc")
    for location in locations:
        route = urlparse(location.text).path
        page = ROOT / route.strip("/") / "index.html"
        source = page.read_text()
        for asset in ("privacy.js", "privacy.css"):
            assert f"assets/studio/{asset}" in source, (route, asset)
        assert "data-privacy-settings" in source, (route, "missing privacy settings")
        if route.startswith("/en/"):
            assert re.search(r'<button\b[^>]*data-privacy-settings[^>]*>Privacy settings</button>', source), (route, "privacy settings language")
        scripts = re.findall(r"<script\b[^>]*>.*?</script\s*>", source, re.I | re.S)
        for script in scripts:
            assert not re.search(
                r'cookie_banner(?:\.min)?\.js|googletagmanager\.com/gtag/|'
                r'clarity\.ms/tag/|window\.dataLayer\s*=\s*window\.dataLayer',
                script,
            ), (route, "unconditional tracker or old consent banner")
        header = re.search(
            r'<header\b[^>]*class="(?:site-header|legacy-editorial-nav)"[^>]*>.*?</header>',
            source, re.S,
        )
        assert header and "logo-user-black.png" in header[0], (route, "header brand")
        footer = re.search(r"<footer\b.*?</footer>", source, re.S)
        assert footer and "logo-user-white.png" in footer[0], (route, "footer brand")
    print(f"PASS: {len(locations)} pages share current branding, privacy choices and opt-in-only analytics")


if __name__ == "__main__":
    main()