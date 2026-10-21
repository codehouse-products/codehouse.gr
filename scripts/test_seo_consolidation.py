#!/usr/bin/env python3
"""Read-only metadata/content checks and isolated real HTTP redirect tests."""
from datetime import date
from html import unescape
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import socket
import shutil
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from xml.etree import ElementTree as ET

from server_release_prerequisites import REDIRECTS, ServerPrerequisites

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://codehouse.gr"


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.links, self.meta, self.ids = [], {}, []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "meta":
            self.meta[attrs.get("name", attrs.get("property"))] = attrs.get("content")
        if attrs.get("id"):
            self.ids.append(attrs["id"])


def nodes(item):
    if isinstance(item, dict):
        yield item
        for value in item.values():
            yield from nodes(value)
    elif isinstance(item, list):
        for value in item:
            yield from nodes(value)


def schemas(source):
    return [node for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', source, re.S)
            for node in nodes(json.loads(block))]


class ConsolidationTests(unittest.TestCase):
    def test_bilingual_responsive_content(self):
        from playwright.sync_api import sync_playwright
        base = "https://" + os.environ["REPLIT_DEV_DOMAIN"]
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_PATH") or shutil.which("chromium"),
                args=["--no-sandbox"])
            try:
                for prefix in ("", "en/"):
                    for width in (390, 1440):
                        context = browser.new_context(viewport={"width": width, "height": 900})
                        context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.route("**/lead.php", lambda route: route.abort())
                        for route in ("blog/kataskeyi-eshop-ellada-kostos/",
                                      "blog/dorean-istoselida/", "prosfora/"):
                            response = page.goto(base + "/" + prefix + route,
                                                 wait_until="domcontentloaded")
                            self.assertEqual(response.status, 200)
                            self.assertEqual(page.locator("h1").count(), 1)
                            self.assertTrue(page.evaluate(
                                "document.documentElement.scrollWidth <= innerWidth + 1"),
                                (prefix, width, route))
                            if "kataskeyi" in route:
                                details = page.locator(".article-faq details").first
                                details.locator("summary").click()
                                self.assertTrue(details.locator("p").is_visible())
                                self.assertEqual(page.locator(".article-faq details").count(), 6)
                            elif route == "blog/dorean-istoselida/":
                                page.locator("#checklist").scroll_into_view_if_needed()
                                self.assertTrue(page.locator("#checklist").is_visible())
                            else:
                                page.locator("#what-free-means").scroll_into_view_if_needed()
                                self.assertTrue(page.locator("#what-free-means").is_visible())
                            self.assertFalse(errors, errors)
                        context.close()
            finally:
                browser.close()

    def test_cost_content_metadata_faq_and_links(self):
        for prefix in ("", "en/"):
            route = "/" + prefix + "blog/kataskeyi-eshop-ellada-kostos/"
            source = (ROOT / route.strip("/") / "index.html").read_text()
            doc = Page(source)
            title = unescape(re.search(r"<title>(.*?)</title>", source, re.S)[1])
            self.assertLessEqual(len(title), 65)
            self.assertLessEqual(len(doc.meta["description"]), 155)
            self.assertEqual(doc.meta["og:title"], title)
            self.assertEqual(doc.meta["og:description"], doc.meta["description"])
            body = re.search(r"<article\b.*?</article>", source, re.S)[0]
            self.assertNotRegex(body, r"[€$£]|\d+\s*(?:ευρώ|euros)")
            prose = re.sub(r"<time\b[^>]*>.*?</time>", "", body, flags=re.S)
            self.assertNotRegex(prose, r"\d+\s*[-–]\s*\d+")
            self.assertIn("myDATA", body)
            self.assertIn("GDPR", body)
            self.assertIn("ERP", body)
            self.assertIn("/" + prefix + "services/e-commerce/", doc.links)
            self.assertIn("/" + prefix + "contact/", doc.links)
            service = (ROOT / (prefix + "services/e-commerce/index.html")).read_text()
            self.assertIn(f'href="{route}"', service)
            faq = [item for item in schemas(source) if item.get("@type") == "FAQPage"]
            self.assertEqual(len(faq), 1)
            self.assertEqual(len(faq[0]["mainEntity"]), 6)
            for question in faq[0]["mainEntity"]:
                self.assertIn(unescape(question["name"]), unescape(body))
                self.assertIn(unescape(question["acceptedAnswer"]["text"]), unescape(body))
            posts = [item for item in schemas(source) if item.get("@type") == "BlogPosting"]
            self.assertEqual(posts[0]["dateModified"], date.today().isoformat())
            self.assertEqual(posts[0]["datePublished"], "2026-09-02")
            self.assertEqual(len(doc.ids), len(set(doc.ids)))

    def test_retained_pages_checklist_and_reciprocal_links(self):
        for prefix in ("", "en/"):
            diy = (ROOT / (prefix + "blog/dorean-istoselida/index.html")).read_text()
            offer = (ROOT / (prefix + "prosfora/index.html")).read_text()
            self.assertIn('id="checklist"', diy)
            self.assertGreaterEqual(len(re.findall(r"<h3>", diy)), 12)
            for name in ("Wix", "WordPress.com", "Google Sites"):
                self.assertIn(name, diy)
            self.assertIn("/" + prefix + "prosfora/", Page(diy).links)
            self.assertIn("/" + prefix + "blog/dorean-istoselida/", Page(offer).links)
            self.assertIn('id="what-free-means"', offer)
            self.assertEqual(offer.count('id="quizForm"'), 1)
            listing = (ROOT / (prefix + "blog/index.html")).read_text()
            cards = re.findall(r'<a\b[^>]*class="bcard"[^>]*href="([^"]+)"', listing)
            self.assertEqual(cards.count("/" + prefix + "blog/dorean-istoselida/"), 1)
            for source in (diy, offer):
                doc = Page(source)
                self.assertEqual(len(doc.ids), len(set(doc.ids)))

    def test_sitemap_and_no_retired_internal_links(self):
        retired = {route for route, _ in REDIRECTS}
        tree = ET.parse(ROOT / "sitemap.xml")
        locs = [item.text for item in tree.findall(".//{*}loc")]
        self.assertFalse({BASE + route for route in retired} & set(locs))
        for loc in locs:
            source = (ROOT / loc.removeprefix(BASE).strip("/") / "index.html").read_text()
            for link in Page(source).links:
                link = link.removeprefix(BASE).split("#")[0].split("?")[0]
                self.assertNotIn(link, retired, (loc, link))
        for route, target in REDIRECTS:
            path = ROOT / route.strip("/") / "index.html"
            if path.is_file():
                source = path.read_text()
                self.assertIn('content="noindex, follow"', source)
                self.assertIn(f'rel="canonical" href="{target}"', source)

    def test_real_preview_http_and_nginx_contract(self):
        # Real PHP responses, isolated random port; no lead requests.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        server = subprocess.Popen(["php", "-S", f"127.0.0.1:{port}", "router.php"],
                                  cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args):
                return None
        opener = urllib.request.build_opener(NoRedirect)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/robots.txt", timeout=1).close()
                    break
                except OSError:
                    time.sleep(.05)
            nginx = ServerPrerequisites._routing_content(None).decode()
            for route, target in REDIRECTS:
                self.assertIn(f"location = {route} {{ return 301 {target}; }}", nginx)
                for method in ("GET", "HEAD"):
                    for path in (route, route.rstrip("/")):
                        request = urllib.request.Request(
                            f"http://127.0.0.1:{port}{path}?utm_source=review", method=method)
                        with self.assertRaises(urllib.error.HTTPError) as error:
                            opener.open(request, timeout=3)
                        self.assertEqual(error.exception.code, 301)
                        self.assertEqual(error.exception.headers["Location"],
                                         target.removeprefix(BASE) + "?utm_source=review")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}" + target.removeprefix(BASE)) as response:
                    self.assertEqual(response.status, 200)
        finally:
            server.terminate()
            server.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
