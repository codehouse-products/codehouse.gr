#!/usr/bin/env python3
"""Check portfolio hover isolation in both languages, without external writes."""
import os
from playwright.sync_api import sync_playwright

BASE = "https://" + os.environ["REPLIT_DEV_DOMAIN"]
CHROMIUM = os.environ.get(
    "CHROMIUM_PATH",
    "/nix/store/5afrhwm7zqn1vb7p5z1mc2rkh2grsfgz-ungoogled-chromium-138.0.7204.100/bin/chromium",
)
STATE = """cards => cards.map(card => {
  const image = card.querySelector('.project-image');
  const overlay = getComputedStyle(image, '::after');
  return {
    opacity: Number(overlay.opacity),
    color: overlay.backgroundColor,
    pointerEvents: overlay.pointerEvents,
    filters: [card, image, image.querySelector('img')].map(e => getComputedStyle(e).filter)
  };
})"""

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
    desktop = browser.new_context(viewport={"width": 1440, "height": 900})
    desktop.add_init_script("localStorage.setItem('cookieConsent','rejected')")
    page = desktop.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    for route in ("/", "/en/", "/projects/", "/en/projects/"):
        page.goto(BASE + route, wait_until="domcontentloaded")
        page.wait_for_function("!document.documentElement.classList.contains('intro-pending')")
        cards = page.locator(".project-card")
        assert cards.count() == 4, route
        for selected in (0, 1):
            cards.nth(selected).hover()
            page.wait_for_timeout(350)
            for index, state in enumerate(cards.evaluate_all(STATE)):
                assert state["opacity"] == (0 if index == selected else 1), (route, state)
                assert state["color"] == "rgba(128, 128, 128, 0.55)"
                assert state["pointerEvents"] == "none"
                assert all(value == "none" for value in state["filters"]), (route, state)
        page.locator("main h1").hover()
        page.wait_for_timeout(350)
        assert all(state["opacity"] == 0 for state in cards.evaluate_all(STATE)), route
    mobile = browser.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
    )
    mobile.add_init_script("localStorage.setItem('cookieConsent','rejected')")
    phone = mobile.new_page()
    phone.goto(BASE + "/projects/", wait_until="domcontentloaded")
    phone.locator(".project-card .project-image").first.tap()
    phone.wait_for_url("**/projects/high-hope/", wait_until="domcontentloaded")
    phone.goto(BASE + "/projects/", wait_until="domcontentloaded")
    assert all(state["opacity"] == 0 for state in phone.locator(".project-card").evaluate_all(STATE))
    assert not errors, errors
    browser.close()
print("Project hover: bilingual home/portfolio, switching, reset, sharp images and touch passed.")