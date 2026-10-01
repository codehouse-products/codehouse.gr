#!/usr/bin/env python3
"""Browser regression checks. Form network calls are intercepted: no email sent."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "https://" + os.environ["REPLIT_DEV_DOMAIN"]
CHROMIUM = os.environ.get(
    "CHROMIUM_PATH",
    "/nix/store/5afrhwm7zqn1vb7p5z1mc2rkh2grsfgz-ungoogled-chromium-138.0.7204.100/bin/chromium",
)
OUTPUT = Path("/tmp/codehouse-qa")
OUTPUT.mkdir(exist_ok=True)

def visit(page, route):
    # The homepage continuously downloads hero films. Network idle is not a
    # readiness signal for this site; wait for the actual UI under test instead.
    response = page.goto(BASE + route, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector("main h1")
    page.wait_for_function(
        "getComputedStyle(document.body).getPropertyValue('--sans').includes('Noto Sans')"
    )
    page.wait_for_function(
        "!document.documentElement.classList.contains('intro-pending')",
        timeout=15000,
    )
    page.evaluate("document.fonts.ready")
    return response


def assert_images(page):
    page.locator("img").evaluate_all("(images)=>images.forEach(i=>i.loading='eager')")
    page.wait_for_function("[...document.images].every(i=>i.complete)", timeout=20000)
    failures = page.locator("img").evaluate_all(
        "(images)=>images.filter(i=>!i.complete || i.naturalWidth===0).map(i=>i.src)"
    )
    assert not failures, f"Broken images: {failures}"


def main():
    report = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        context = browser.new_context(ignore_https_errors=True)
        context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
        page = context.new_page()
        console_errors = []
        page.on("pageerror", lambda error: console_errors.append(str(error)))
        for name, width, height in (("desktop", 1440, 900), ("tablet", 768, 1024), ("mobile", 360, 800)):
            page.set_viewport_size({"width": width, "height": height})
            visit(page, "/")
            assert page.locator("h1").count() == 1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), f"{name} horizontal overflow"
            page.locator(".site-footer").scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            assert_images(page)
            page.evaluate("scrollTo(0,0)")
            page.wait_for_timeout(300)
            page.screenshot(path=str(OUTPUT / f"{name}-home.png"), full_page=True)
            if width <= 768 and page.locator(".menu-toggle").is_visible():
                toggle = page.locator(".menu-toggle")
                toggle.click()
                assert toggle.get_attribute("aria-expanded") == "true"
                assert page.evaluate("document.querySelector('main').inert")
                menu = page.locator(".menu-panel")
                assert menu.is_visible()
                page.keyboard.press("Shift+Tab")
                assert page.evaluate("document.querySelector('.menu-panel').contains(document.activeElement)")
                page.keyboard.press("Tab")
                assert page.evaluate("document.querySelector('.menu-panel').contains(document.activeElement)")
                page.screenshot(path=str(OUTPUT / f"{name}-menu.png"))
                page.keyboard.press("Escape")
                assert toggle.get_attribute("aria-expanded") == "false"
                assert not page.evaluate("document.querySelector('main').inert")
                assert toggle.evaluate("(el)=>el===document.activeElement")
            rail = page.locator(".service-rail").first
            rail.scroll_into_view_if_needed()
            rail.evaluate("(el)=>el.scrollLeft=0")
            rail.focus()
            page.keyboard.press("ArrowRight")
            page.wait_for_timeout(600)
            assert rail.evaluate("(el)=>el.scrollLeft > 0"), f"{name}: slider keyboard scroll"
            rail.evaluate("(el)=>el.scrollLeft=0")
            page.wait_for_timeout(500)
            report.append(f"{name}: responsive, images, menu and keyboard slider passed")
        page.set_viewport_size({"width": 1440, "height": 900})
        visit(page, "/")
        first = page.locator(".service-card").first
        first.scroll_into_view_if_needed()
        first.hover()
        page.wait_for_timeout(500)
        if page.locator(".service-card img").count():
            filters = page.locator(".service-card").evaluate_all(
                "(cards)=>cards.filter(c=>c.querySelector('img')).map(c=>getComputedStyle(c.querySelector('img')).filter)"
            )
            if first.locator("img").count():
                assert filters[0] in ("none", "blur(0px)"), f"Active image unexpectedly blurred {filters}"
            if page.locator(".service-card:not(.is-active) img").count():
                assert any("blur" in value and value != "blur(0px)" for value in filters), f"No sibling image blur {filters}"
            report.append("Service hover: active image clear, sibling images blurred")
        else:
            assert page.locator(".service-image.photo-empty").count() == page.locator(".service-card").count()
            assert "is-active" in first.get_attribute("class")
            report.append("Service hover: intentionally blank frames retain active-card behavior")
        page.screenshot(path=str(OUTPUT / "desktop-service-hover.png"))
        page.set_viewport_size({"width": 360, "height": 800})
        page.locator(".menu-toggle").click()
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(300)
        assert not page.evaluate("document.querySelector('main').inert")
        assert not page.locator("body").evaluate("(el)=>el.classList.contains('menu-open')")
        report.append("Menu resize cleanup: background remains operable")
        for route in ("/services/", "/services/web-design/", "/projects/", "/projects/high-hope/", "/studio/", "/contact/"):
            response = visit(page, route)
            assert response.status == 200, f"Broken route {route}: {response.status}"
            assert page.locator("h1").count() == 1
            alternate = page.locator('link[hreflang="en"]').get_attribute("href")
            assert alternate, f"No same-page EN {route}"
            english_path = alternate.replace("https://codehouse.gr", "")
            response = visit(page, english_path)
            assert response.status == 200
            assert page.locator("html").get_attribute("lang") == "en"
            assert_images(page)
        report.append("Core internal pages and English equivalents passed")
        # Exercise UI states with explicit controlled test responses, not live mail.
        visit(page, "/en/contact/")
        form = page.locator("[data-contact-form]")
        outcomes = []
        for status, payload in ((202, {"ok": True, "saved": True, "mail": False}), (500, {"ok": False, "saved": False}), (200, {"ok": True, "saved": True, "mail": True})):
            def controlled_response(route):
                route.fulfill(status=status, content_type="application/json", body=json.dumps(payload))
            page.route("**/lead.php", controlled_response)
            form.locator('[name="name"]').fill("Automated QA")
            form.locator('[name="email"]').fill("qa@example.invalid")
            form.locator('[name="description"]').fill("Controlled UI test; no live submission.")
            form.locator('[name="service"]').select_option("web")
            form.locator('[type="submit"]').click()
            page.wait_for_timeout(400)
            text = form.locator(".form-status").inner_text()
            if status == 202:
                assert "saved" in text.lower() and "sent." not in text.lower(), text
            elif status == 500:
                assert form.locator('[name="name"]').input_value() == "Automated QA"
                assert form.locator(".form-status").get_attribute("role") == "alert"
            else:
                assert "sent" in text.lower(), text
                assert form.locator('[name="name"]').input_value() == ""
            assert form.locator('[type="submit"]').is_enabled()
            outcomes.append(text)
            page.unroute("**/lead.php")
        report.append("Controlled form states: saved-not-emailed, server failure with retained inputs, actual sent response")
        page.emulate_media(reduced_motion="reduce")
        visit(page, "/")
        assert page.locator("h1").is_visible()
        assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches")
        report.append("Reduced-motion content visible")
        # Use a genuine touch-enabled browser context rather than only a narrow
        # desktop viewport. CDP events exercise the native horizontal scroller.
        touch_context = browser.new_context(
            ignore_https_errors=True, has_touch=True, is_mobile=True,
            viewport={"width": 390, "height": 844}
        )
        touch_context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
        touch_page = touch_context.new_page()
        visit(touch_page, "/")
        touch_rail = touch_page.locator(".service-rail").first
        touch_rail.scroll_into_view_if_needed()
        touch_page.wait_for_timeout(500)
        bounds = touch_rail.bounding_box()
        y = min(bounds["y"] + 120, 700)
        cdp = touch_context.new_cdp_session(touch_page)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 330, "y": y}]})
        for x in range(310, 60, -25):
            cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": x, "y": y}]})
            touch_page.wait_for_timeout(20)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        touch_page.wait_for_timeout(700)
        assert touch_rail.evaluate("(el)=>el.scrollLeft > 0"), "Native touch swipe did not scroll"
        touch_page.locator(".service-card").nth(1).tap()
        touch_page.wait_for_url("**/services/e-commerce/", wait_until="domcontentloaded")
        touch_page.wait_for_selector("main h1")
        assert "/services/" in touch_page.url and touch_page.url.rstrip("/") != BASE + "/services"
        report.append("Genuine mobile touch: native swipe and single-tap service navigation")
        touch_context.close()
        # A new visitor must not load optional trackers before choosing consent.
        consent_context = browser.new_context(ignore_https_errors=True)
        consent_page = consent_context.new_page()
        trackers = []
        consent_page.on("request", lambda request: trackers.append(request.url) if any(host in request.url for host in ("googletagmanager.com", "clarity.ms")) else None)
        visit(consent_page, "/")
        assert consent_page.locator(".studio-consent").is_visible()
        assert not trackers, f"Optional tracker loaded before consent: {trackers}"
        consent_page.locator(".studio-consent button").first.click()
        assert not consent_page.locator(".studio-consent").count()
        assert consent_page.evaluate("localStorage.getItem('cookieConsent')") == "rejected"
        assert not trackers
        report.append("New studio consent: no GA/Clarity before consent or after rejection")
        consent_context.close()
        assert not console_errors, f"Browser errors: {console_errors}"
        browser.close()
    (OUTPUT / "report.json").write_text(json.dumps({"checks": report, "form_test_messages": outcomes}, indent=2))
    print("\n".join(report))
    print(f"PASS. Screenshots and report: {OUTPUT}")


if __name__ == "__main__":
    main()