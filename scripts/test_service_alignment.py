#!/usr/bin/env python3
"""Ensure service rail snap points retain the section's side margins."""
import os
from playwright.sync_api import sync_playwright

BASE = "https://" + os.environ["REPLIT_DEV_DOMAIN"]
CHROMIUM = os.environ.get(
    "CHROMIUM_PATH",
    "/nix/store/5afrhwm7zqn1vb7p5z1mc2rkh2grsfgz-ungoogled-chromium-138.0.7204.100/bin/chromium",
)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
    for width in (360, 390, 430, 768, 1440):
        context = browser.new_context(viewport={"width": width, "height": 900})
        context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
        page = context.new_page()
        for route in ("/", "/en/"):
            page.goto(BASE + route, wait_until="domcontentloaded")
            rail = page.locator(".service-rail")
            rail.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            initial = rail.evaluate("""r => ({
              imageLeft: r.querySelector('.service-image').getBoundingClientRect().left,
              titleLeft: r.parentElement.querySelector('.section-heading').getBoundingClientRect().left,
              scroll: r.scrollLeft
            })""")
            assert abs(initial["imageLeft"] - initial["titleLeft"]) < 1, (width, route, initial)
            assert initial["scroll"] == 0, (width, route, initial)
            rail.evaluate("r => r.scrollTo({left:r.scrollWidth,behavior:'instant'})")
            page.wait_for_timeout(400)
            end = rail.evaluate("""r => ({
              imageRight: r.querySelector('.service-card:last-child .service-image').getBoundingClientRect().right,
              titleRight: r.parentElement.querySelector('.section-heading').getBoundingClientRect().right,
              scroll: r.scrollLeft
            })""")
            assert end["scroll"] > 0, (width, route, end)
            assert abs(end["imageRight"] - end["titleRight"]) < 1, (width, route, end)
            rail.evaluate("r => r.scrollTo({left:0,behavior:'instant'})")
            page.wait_for_timeout(400)
            assert rail.evaluate("r=>r.scrollLeft") == 0
        context.close()
    browser.close()
print("PASS: service images align with headings at both rail ends in 5 widths and both languages.")
