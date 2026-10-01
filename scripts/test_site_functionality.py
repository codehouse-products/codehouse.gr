#!/usr/bin/env python3
"""Public-preview functional checks; all writes and analytics are intercepted.

Controlled lead responses test client UI only. No leads, emails or analytics
events leave this browser. Uses the existing hero-video Chromium/Python path.
"""
import json
from urllib.parse import urlsplit
from playwright.sync_api import expect, sync_playwright
from test_hero_video import BASE, CHROMIUM


class SafeBrowser:
    def __init__(self, browser, consent="rejected", **options):
        self.context = browser.new_context(
            ignore_https_errors=True, reduced_motion="reduce", **options
        )
        self.analytics = []
        self.leads = []
        self.blocked_writes = []
        self.errors = []
        self.pending = []
        self.reply = (500, {"ok": False, "saved": False})
        self.hold = False
        if consent is not None:
            self.context.add_init_script(
                "try { localStorage.setItem('cookieConsent'," + json.dumps(consent) + ") } catch {}"
            )
        self.context.on("page", lambda page: page.on(
            "pageerror", lambda error: self.errors.append(str(error))))
        self.context.route("**/*", self.intercept)

    def intercept(self, route):
        request = route.request
        host = urlsplit(request.url).hostname or ""
        if any(host == domain or host.endswith("." + domain) for domain in (
            "googletagmanager.com", "google-analytics.com", "clarity.ms",
        )):
            self.analytics.append(request.url)
            route.fulfill(status=200, content_type="application/javascript", body="")
        elif urlsplit(request.url).path == "/lead.php":
            self.leads.append(request.post_data_json)
            if self.hold:
                self.pending.append(route)
            else:
                self.fulfill(route)
        elif request.method not in ("GET", "HEAD"):
            self.blocked_writes.append(request.url)
            route.fulfill(status=403, body="QA blocked a live write")
        elif "/qa-deliberate-missing-image.webp" in request.url:
            route.fulfill(status=404, body="Controlled gallery failure")
        else:
            route.continue_()

    def fulfill(self, route):
        status, payload = self.reply
        body = payload if isinstance(payload, str) else json.dumps(payload)
        route.fulfill(status=status, content_type="application/json", body=body)

    def close(self):
        assert not self.errors, self.errors
        assert not self.blocked_writes, self.blocked_writes
        self.context.close()


def visit(page, path):
    response = page.goto(BASE + path, wait_until="domcontentloaded", timeout=60000)
    assert response.status == 200, (path, response.status)
    expect(page.locator("h1")).to_be_visible()
    page.wait_for_function(
        "getComputedStyle(document.body).getPropertyValue('--sans').includes('Noto Sans')"
    )


def test_languages_and_menus(browser):
    safe = SafeBrowser(browser)
    page = safe.context.new_page()
    page.set_viewport_size({"width": 1440, "height": 900})
    # Click the rendered switch, not just the hreflang metadata.
    for path in ("/", "/services/", "/projects/", "/studio/", "/contact/",
                 "/blog/", "/prosfora/"):
        visit(page, path)
        language = page.locator(".language, .legacy-language").first
        language.locator('a[href="/en' + path + '"]').click()
        page.wait_for_url(BASE + "/en" + path, wait_until="domcontentloaded")
        expect(page.locator("html")).to_have_attribute("lang", "en")
        page.locator(".language, .legacy-language").first.locator(
            'a[href="' + path + '"]').click()
        page.wait_for_url(BASE + path, wait_until="domcontentloaded")
        expect(page.locator("html")).to_have_attribute("lang", "el")
    page.set_viewport_size({"width": 360, "height": 800})
    visit(page, "/contact/")
    toggle = page.locator(".menu-toggle")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")
    expect(page.locator(".menu-close")).to_be_focused()
    assert page.locator("main").evaluate("(main)=>main.inert")
    page.keyboard.press("Shift+Tab")
    assert page.locator(".menu-panel").evaluate(
        "(menu)=>menu.contains(document.activeElement)")
    page.keyboard.press("Tab")
    page.keyboard.press("Escape")
    expect(toggle).to_have_attribute("aria-expanded", "false")
    expect(toggle).to_be_focused()
    toggle.click()
    page.locator('.menu-panel a[href="/en/contact/"]').click()
    page.wait_for_url(BASE + "/en/contact/", wait_until="domcontentloaded")
    page.go_back(wait_until="domcontentloaded")
    expect(page.locator(".menu-toggle")).to_have_attribute("aria-expanded", "false")
    assert not page.locator("main").evaluate("(main)=>main.inert")
    page.locator(".menu-toggle").click()
    page.set_viewport_size({"width": 1440, "height": 900})
    expect(page.locator(".menu-toggle")).to_have_attribute("aria-expanded", "false")
    assert not page.locator("main").evaluate("(main)=>main.inert")
    page.set_viewport_size({"width": 360, "height": 800})
    for path in ("/blog/", "/en/blog/", "/prosfora/", "/en/prosfora/"):
        visit(page, path)
        menu = page.locator("[data-legacy-mobile-menu]")
        menu.locator("summary").click()
        expect(menu).to_have_attribute("open", "")
        page.keyboard.press("Escape")
        assert not menu.evaluate("(menu)=>menu.open")
        expect(menu.locator("summary")).to_be_focused()
        menu.locator("summary").click()
        destination = "/en/services/" if path.startswith("/en/") else "/services/"
        menu.locator('a[href="' + destination + '"]').click()
        page.wait_for_url(BASE + destination, wait_until="domcontentloaded")
        page.go_back(wait_until="domcontentloaded")
        assert not page.locator("[data-legacy-mobile-menu]").evaluate("(menu)=>menu.open")
    safe.close()
    print("PASS: GR/EN switch clicks; studio and legacy mobile menus, keyboard, back and resize")


def fill_contact(form, description="Αβγδεζηθικ"):
    form.locator("[name=name]").fill("Controlled QA")
    form.locator("[name=email]").fill("qa@example.invalid")
    form.locator("[name=service]").select_option("web")
    form.locator("[name=description]").fill(description)


def test_contact_forms(browser):
    safe = SafeBrowser(browser)
    page = safe.context.new_page()
    for path in ("/contact/", "/en/contact/"):
        visit(page, path)
        form = page.locator("[data-contact-form]")
        submit = form.locator("[type=submit]")
        submit.click()
        assert not safe.leads
        fill_contact(form)
        for field, value in (("name", "   "), ("email", "not-an-email"),
                             ("description", " αβγδεζηθι "),
                             ("description", "😀😀😀😀😀")):
            fill_contact(form)
            form.locator("[name=" + field + "]").fill(value)
            before = len(safe.leads)
            submit.click()
            assert not form.locator("[name=" + field + "]").evaluate("(field)=>field.validity.valid")
            page.wait_for_timeout(100)
            assert len(safe.leads) == before, (path, field, value)
        fill_contact(form)
        safe.hold = True
        before = len(safe.leads)
        form.evaluate("(form)=>{form.requestSubmit();form.requestSubmit()}")
        expect(submit).to_be_disabled()
        page.wait_for_timeout(150)
        assert len(safe.leads) == before + 1, "Duplicate request while pending"
        assert len(safe.pending) == 1
        payload = safe.leads[-1]
        assert payload["_form"] == "studio" and payload["website"] == ""
        assert payload["description"] == "Αβγδεζηθικ" and payload["service"] == "web"
        safe.reply = (202, {"ok": True, "saved": True, "mail": False})
        safe.fulfill(safe.pending.pop())
        safe.hold = False
        expect(submit).to_be_enabled()
        expect(form.locator(".form-status")).to_have_attribute("role", "status")
        assert form.locator("[name=name]").input_value() == "Controlled QA"
        assert "hello@codehouse.gr" in form.locator(".form-status").inner_text()
        for status, payload in ((500, {"ok": False, "saved": False}), (200, "not-json"),
                                (200, {"ok": True, "saved": True, "mail": True})):
            safe.reply = (status, payload)
            fill_contact(form)
            with page.expect_request("**/lead.php"):
                submit.click()
            expect(submit).to_be_enabled()
            if isinstance(payload, dict) and payload.get("mail"):
                expect(form.locator("[name=name]")).to_have_value("")
                expect(form.locator(".form-status")).to_have_attribute("role", "status")
            else:
                expect(form.locator("[name=name]")).to_have_value("Controlled QA")
                expect(form.locator(".form-status")).to_have_attribute("role", "alert")
        safe.leads.clear()
    safe.close()
    print("PASS: GR/EN contact validation, Unicode minimum, duplicate guard and controlled response states")


def test_legacy_forms(browser):
    safe = SafeBrowser(browser)
    page = safe.context.new_page()
    for path in ("/prosfora/", "/en/prosfora/"):
        visit(page, path)
        form = page.locator("#quizForm")
        next_button = page.locator("#quizNext")
        for _ in range(6):
            next_button.click()
        assert form.locator('.quiz-step.active').get_attribute("data-step") == "7"
        next_button.click()
        assert not safe.leads
        form.locator("[name=name]").fill("Controlled QA")
        form.locator("[name=phone]").fill("+30 6900000000")
        form.locator("[name=email]").fill("not-an-email")
        next_button.click()
        assert not form.locator("[name=email]").evaluate("(field)=>field.validity.valid")
        page.wait_for_timeout(100)
        assert not safe.leads
        # Email remains optional: a blank email with name/phone may be sent.
        form.locator("[name=email]").fill("")
        safe.reply = (500, {"ok": False, "saved": False})
        with page.expect_request("**/lead.php"):
            next_button.click()
        expect(next_button).to_be_enabled()
        expect(form.locator("[name=name]")).to_have_value("Controlled QA")
        expect(page.locator("#quizSubmitStatus")).not_to_be_empty()
        assert safe.leads[-1]["phone"] == "+30 6900000000"
        assert safe.leads[-1]["email"] == "" and "_form" not in safe.leads[-1]
        safe.reply = (202, {"ok": True, "saved": True, "mail": False})
        with page.expect_request("**/lead.php"):
            next_button.click()
        expect(page.locator("#quizSuccess")).to_be_visible()
        safe.leads.clear()
    safe.close()
    print("PASS: GR/EN legacy quiz progression, required fields, optional email validation and retained contracts")


def test_galleries(browser):
    safe = SafeBrowser(browser)
    page = safe.context.new_page()
    for path in ("/", "/en/"):
        for width in (1440, 360):
            page.set_viewport_size({"width": width, "height": 900})
            visit(page, path)
            gallery = page.locator("[data-project-gallery]").first
            images = gallery.locator("[data-gallery-slide]")
            total = images.count()
            assert total >= 2
            next_button = gallery.locator("[data-gallery-direction=next]")
            next_button.scroll_into_view_if_needed()
            next_button.focus()
            page.keyboard.press("Enter")
            expect(gallery).to_have_attribute("data-gallery-index", "1")
            expect(next_button).to_be_focused()
            rail = page.locator("#project-rail")
            before = rail.evaluate("(rail)=>rail.scrollLeft")
            page.keyboard.press("ArrowLeft")
            expect(gallery).to_have_attribute("data-gallery-index", "0")
            assert abs(rail.evaluate("(rail)=>rail.scrollLeft") - before) < 1
            page.keyboard.press("ArrowLeft")
            expect(gallery).to_have_attribute("data-gallery-index", str(total - 1))
            page.keyboard.press("ArrowRight")
            expect(gallery).to_have_attribute("data-gallery-index", "0")
            assert gallery.locator("[data-gallery-slide]:not([hidden])").count() == 1
            broken = images.nth(1)
            source = broken.get_attribute("src")
            broken.evaluate("(image)=>image.src='/qa-deliberate-missing-image.webp'")
            next_button.click()
            expect(gallery.locator("[data-gallery-status]")).to_be_visible()
            expect(gallery.locator("[data-gallery-status]")).not_to_be_empty()
            expect(gallery).to_have_attribute("data-gallery-index", "0")
            assert images.first.evaluate("(image)=>image.naturalWidth>0 && !image.hidden")
            expect(next_button).to_be_enabled()
            broken.evaluate("(image,src)=>image.src=src", source)
            next_button.click()
            expect(gallery).to_have_attribute("data-gallery-index", "1")
            expect(gallery.locator("[data-gallery-status]")).to_be_hidden()
            assert gallery.locator("[data-gallery-slide]:not([hidden])").count() == 1
    safe.close()
    print("PASS: GR/EN desktop/mobile galleries, keyboard focus, wrapping, rail isolation and image-failure retry")


def test_privacy(browser):
    for path in ("/contact/", "/blog/", "/prosfora/", "/en/blog/", "/en/prosfora/"):
        safe = SafeBrowser(browser, consent=None)
        page = safe.context.new_page()
        visit(page, path)
        banner = page.locator(".studio-consent")
        expect(banner).to_be_visible()
        english = path.startswith("/en/")
        expect(banner.locator("a")).to_have_attribute(
            "href", "/en/aporrito/" if english else "/aporrito/")
        assert banner.locator("button").first.text_content() == (
            "Reject optional" if english else "Απόρριψη προαιρετικών")
        assert not safe.analytics, (path, safe.analytics)
        if page.locator("form").count():
            assert page.locator("form").first.get_attribute("data-clarity-mask") == "true"
        banner.locator("button").first.click()
        expect(banner).to_have_count(0)
        assert page.evaluate("localStorage.getItem('cookieConsent')") == "rejected"
        page.reload(wait_until="domcontentloaded")
        expect(banner).to_have_count(0)
        assert not safe.analytics
        page.locator("[data-privacy-settings]").click()
        banner.locator("button").last.click()
        page.wait_for_function(
            "document.querySelector('script[src*=\"googletagmanager.com\"]') && "
            "document.querySelector('script[src*=\"clarity.ms\"]')")
        page.wait_for_timeout(100)
        assert len(safe.analytics) == 2, (path, safe.analytics)
        assert page.evaluate("localStorage.getItem('cookieConsent')") == "accepted"
        assert page.evaluate("""() => dataLayer.some(args =>
            args[0]==='consent' && args[2].analytics_storage==='granted' &&
            args[2].ad_storage==='denied' && args[2].ad_user_data==='denied' &&
            args[2].ad_personalization==='denied')""")
        page.locator("[data-privacy-settings]").click()
        banner.locator("button").last.click()
        assert len(safe.analytics) == 2, "Duplicate tracker bootstrap"
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(100)
        assert len(safe.analytics) == 4, "Stored opt-in did not bootstrap exactly once"
        safe.analytics.clear()
        page.locator("[data-privacy-settings]").click()
        with page.expect_navigation(wait_until="domcontentloaded"):
            banner.locator("button").first.click()
        expect(banner).to_have_count(0)
        assert page.evaluate("localStorage.getItem('cookieConsent')") == "rejected"
        assert not safe.analytics, "Trackers reloaded after revocation"
        assert page.locator('script[src*="googletagmanager.com"],script[src*="clarity.ms"]').count() == 0
        safe.close()
        print(f"PASS: {path}: fresh/rejected/accepted/stored/reopened/revoked consent; analytics mocked")

    # A rejection in one tab must also stop trackers in an already-open tab.
    safe = SafeBrowser(browser, consent=None)
    first = safe.context.new_page()
    visit(first, "/en/blog/")
    first.locator(".studio-consent button").last.click()
    second = safe.context.new_page()
    visit(second, "/en/prosfora/")
    second.wait_for_function("typeof gtag==='function'")
    first.locator("[data-privacy-settings]").click()
    with first.expect_navigation(wait_until="domcontentloaded"):
        first.locator(".studio-consent button").first.click()
    second.wait_for_function(
        "localStorage.getItem('cookieConsent')==='rejected' && "
        "!document.querySelector('script[src*=\"googletagmanager.com\"]')"
    )
    assert not second.locator('script[src*="clarity.ms"]').count()
    safe.close()
    print("PASS: cross-tab consent revocation stops trackers on both legacy pages")


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        try:
            test_languages_and_menus(browser)
            test_contact_forms(browser)
            test_legacy_forms(browser)
            test_galleries(browser)
            test_privacy(browser)
        finally:
            browser.close()
    print("PASS: all functional checks; no real lead POSTs, emails or analytics calls.")


if __name__ == "__main__":
    main()