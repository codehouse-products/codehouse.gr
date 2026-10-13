#!/usr/bin/env python3
"""Portfolio snap points must preserve the title and controls alignment."""
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
        for route in ("/", "/en/", "/projects/", "/en/projects/"):
            page.goto(BASE + route, wait_until="domcontentloaded")
            rail = page.locator(".horizontal-rail").filter(has=page.locator(".project-card"))
            rail.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            bounds = rail.evaluate("""r => {
              const section = r.parentElement;
              const heading = section.querySelector('.section-heading') || document.querySelector('.page-intro');
              const rect = heading.getBoundingClientRect();
              const padding = heading.classList.contains('page-intro') ? parseFloat(getComputedStyle(heading).paddingLeft) : 0;
              return {left:rect.left+padding,right:rect.right-padding};
            }""")
            first = rail.locator(".project-image").first
            assert abs(first.bounding_box()["x"] - bounds["left"]) < 1, (width, route)
            assert rail.evaluate("r=>r.scrollLeft") == 0, (width, route)
            overflowing = rail.evaluate("r=>r.scrollWidth > r.clientWidth")
            if rail.get_attribute("id"):
                control = page.locator('[data-rail-control="#project-rail"][data-dir="prev"]')
                assert control.is_disabled()
                assert abs(control.bounding_box()["x"] - bounds["left"]) < 1
                if overflowing:
                    page.locator('[data-rail-control="#project-rail"][data-dir="next"]').click()
                    page.wait_for_timeout(900)
                    assert rail.evaluate("r=>r.scrollLeft") > 0
            rail.evaluate("r=>r.scrollTo({left:r.scrollWidth,behavior:'instant'})")
            page.wait_for_timeout(400)
            last = rail.locator(".project-image").last.bounding_box()
            if overflowing:
                assert abs(last["x"] + last["width"] - bounds["right"]) < 1, (width, route)
            else:
                assert last["x"] + last["width"] <= bounds["right"] + 1
            rail.evaluate("r=>r.scrollTo({left:0,behavior:'instant'})")
            page.wait_for_timeout(400)
            assert abs(first.bounding_box()["x"] - bounds["left"]) < 1, (width, route)
        context.close()
    browser.close()
print("PASS: bilingual home/portfolio alignment and home arrows across 5 screen widths.")
