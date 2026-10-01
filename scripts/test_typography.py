#!/usr/bin/env python3
"""Check Greek/English typography parity and native glyphs, without submitting forms."""
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright
from test_hero_video import BASE, CHROMIUM

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = "Υπηρεσίες ΆΈΉΊΌΎΏ άέήίόύώ Ελληνικά Services English 0123456789"
ROLES = ["body", "main h1", "main h2",
         ".hero-intro > p, .page-intro > p, .bhero > .sub, .pf-lead",
         ".nav-links, .legacy-editorial-nav",
         ".eyebrow, .lp-kicker, .bkicker"]


def verify_coverage():
    locations = ET.parse(ROOT / "sitemap.xml").findall(".//{*}loc")
    for location in locations:
        path = urlparse(location.text).path.strip("/")
        source = (ROOT / path / "index.html").read_text()
        assert "studio.css" in source or "legacy.css" in source, path
    print(f"PASS: shared typography reaches all {len(locations)} sitemap pages")


def metrics(page):
    return page.evaluate("""selectors => selectors.map(selector => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const style = getComputedStyle(element);
      return Object.fromEntries(['fontFamily','fontSize','fontWeight','fontStyle',
        'lineHeight','letterSpacing'].map(key => [key,style[key]]));
    })""", ROLES)


def verify_native_glyphs(page):
    for family in ["Noto Sans", "Roboto Mono"]:
        page.evaluate("""async ({family,text}) => {
          document.querySelector('#typography-probe')?.remove();
          const probe = document.createElement('span');
          probe.id = 'typography-probe';
          probe.textContent = text;
          probe.setAttribute('aria-hidden','true');
          Object.assign(probe.style, {position:'fixed',left:'0',top:'0',
            opacity:'0',fontFamily:family,fontSize:'16px',fontWeight:'400'});
          document.body.append(probe);
          await document.fonts.load(`400 16px "${family}"`, text);
          await document.fonts.ready;
          // CDP's glyph-font report can retain the fallback from the previous
          // paint, even after loading resolves. Wait for a rendered frame.
          await new Promise(resolve =>
            requestAnimationFrame(() => requestAnimationFrame(resolve)));
        }""", {"family": family, "text": SAMPLE})
        session = page.context.new_cdp_session(page)
        session.send("DOM.enable")
        session.send("CSS.enable")
        root = session.send("DOM.getDocument")["root"]["nodeId"]
        node = session.send("DOM.querySelector",
                            {"nodeId": root, "selector": "#typography-probe"})["nodeId"]
        fonts = session.send("CSS.getPlatformFontsForNode", {"nodeId": node})["fonts"]
        assert fonts and all(font["isCustomFont"] and
                             font["familyName"].startswith(family)
                             for font in fonts), (family, fonts)
        session.detach()
    page.locator("#typography-probe").evaluate("element => element.remove()")


def main():
    verify_coverage()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM,
                                              args=["--no-sandbox"])
        context = browser.new_context(ignore_https_errors=True,
                                       reduced_motion="reduce")
        context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
        # New studio, editorial/blog, and legacy offer/form templates.
        for width in [360, 1024, 1440]:
            for path in ["/", "/services/", "/blog/", "/prosfora/"]:
                pages = []
                for prefix in ["", "/en"]:
                    page = context.new_page()
                    page.set_viewport_size({"width": width, "height": 900})
                    page.goto(BASE + prefix + path, wait_until="domcontentloaded")
                    page.wait_for_function(
                        "getComputedStyle(document.body).getPropertyValue('--sans').includes('Noto Sans')"
                    )
                    page.evaluate("document.fonts.ready")
                    verify_native_glyphs(page)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth + 1"
                    ), (prefix + path, width, "horizontal overflow")
                    pages.append(page)
                greek, english = [metrics(page) for page in pages]
                for role, el, en in zip(ROLES, greek, english):
                    if el is not None and en is not None:
                        assert el == en, (path, width, role, el, en)
                print(f"PASS: GR/EN families, sizes, weights, styles and native glyphs: {path} {width}px")
                for page in pages:
                    page.close()
        browser.close()


if __name__ == "__main__":
    main()