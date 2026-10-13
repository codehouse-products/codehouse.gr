#!/usr/bin/env python3
"""Verify responsive article navigation and mocked existing contact submission."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "https://" + os.environ["REPLIT_DEV_DOMAIN"]
PAGE = "/generated-artifacts/editorial-preview/index.html"
CHROMIUM = os.environ.get("CHROMIUM_PATH",
    "/nix/store/5afrhwm7zqn1vb7p5z1mc2rkh2grsfgz-ungoogled-chromium-138.0.7204.100/bin/chromium")


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM, headless=True,
                                             args=["--no-sandbox"])
        for width in (360, 390, 430, 768, 1440):
            context = browser.new_context(viewport={"width": width, "height": 900},
                                          is_mobile=width < 760, has_touch=width < 760)
            context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            requests = []
            fail = [False]

            def lead(route):
                requests.append(route.request.post_data_json)
                if fail[0]:
                    route.fulfill(status=500, content_type="application/json",
                                  body=json.dumps({"ok": False}))
                else:
                    route.fulfill(status=200, content_type="application/json",
                                  body=json.dumps({"ok": True, "saved": True, "mail": True}))

            # No real leads or email are sent by this test.
            page.route("**/lead.php", lead)
            page.goto(BASE + PAGE, wait_until="domcontentloaded")
            page.wait_for_selector(".editorial-article")
            assert page.locator("h1").count() == 1
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
            assert page.locator('meta[name="robots"]').get_attribute("content") == "noindex, nofollow"
            if width < 760:
                page.locator(".menu-toggle").click()
                page.wait_for_selector(".menu-panel.open")
                assert page.locator(".menu-panel").get_attribute("aria-hidden") == "false"
                page.locator(".menu-close").click()
                assert page.locator(".menu-toggle").get_attribute("aria-expanded") == "false"
            page.locator('.editorial-toc a[href="#section-1"]').click()
            assert page.locator("#section-1").is_visible()
            page.locator(".editorial-faq details").first.locator("summary").click()
            assert page.locator(".editorial-faq details").first.get_attribute("open") is not None
            form = page.locator("[data-contact-form]")
            form.locator('[name="name"]').fill("Synthetic preview test")
            form.locator('[name="email"]').fill("preview-test@example.invalid")
            form.locator('[name="service"]').select_option("ecommerce")
            form.locator('[name="description"]').fill("Δοκιμή φόρμας χωρίς πραγματική αποστολή.")
            form.locator('[type="submit"]').click()
            page.wait_for_function("document.querySelector('.form-status').textContent.includes('στάλθηκε')")
            assert len(requests) == 1
            assert requests[0]["_form"] == "studio"
            assert requests[0]["service"] == "ecommerce"
            assert form.locator('[name="name"]').input_value() == ""
            fail[0] = True
            form.locator('[name="name"]').fill("Synthetic failure test")
            form.locator('[name="email"]').fill("preview-test@example.invalid")
            form.locator('[name="service"]').select_option("web")
            form.locator('[name="description"]').fill("Δοκιμή διατήρησης δεδομένων σε αποτυχία.")
            form.locator('[type="submit"]').click()
            page.wait_for_function("document.querySelector('.form-status').getAttribute('role') === 'alert'")
            assert form.locator('[name="description"]').input_value().startswith("Δοκιμή")
            assert form.locator('[type="submit"]').is_enabled()
            assert not errors, errors
            context.close()
        browser.close()
    print("PASS: article at five widths, menu, contents, FAQs, mocked success/failure and retained inputs.")


if __name__ == "__main__":
    main()
