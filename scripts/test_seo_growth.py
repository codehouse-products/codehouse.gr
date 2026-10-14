#!/usr/bin/env python3
"""Check service navigation and contact interactions without sending real leads."""
import json
import os
from playwright.sync_api import sync_playwright

BASE = "https://" + os.environ["REPLIT_DEV_DOMAIN"]
CHROMIUM = os.environ.get(
    "CHROMIUM_PATH",
    "/nix/store/5afrhwm7zqn1vb7p5z1mc2rkh2grsfgz-ungoogled-chromium-138.0.7204.100/bin/chromium",
)


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=CHROMIUM, headless=True, args=["--no-sandbox"]
        )
        for prefix in ("", "/en"):
            for width in (360, 390, 430, 768, 1440):
                context = browser.new_context(viewport={"width": width, "height": 900})
                context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                response = page.goto(BASE + prefix + "/seo/", wait_until="domcontentloaded")
                assert response.status == 200
                assert page.locator("h1").count() == 1
                assert "SEO / GEO" in page.locator("h1").inner_text()
                assert page.locator("#monthly-work").count() == 1
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), (prefix, width)
                assert page.locator('link[rel="canonical"]').get_attribute("href") == "https://codehouse.gr" + prefix + "/seo/"
                schema = [
                    item for script in page.locator('script[type="application/ld+json"]').all()
                    for item in json.loads(script.text_content()).get("@graph", [])
                    if item.get("@type") == "Service"
                ]
                assert len(schema) == 1 and "GEO" in schema[0]["name"]
                menu = page.locator("[data-legacy-mobile-menu]")
                if menu.locator("summary").is_visible():
                    menu.locator("summary").click()
                    assert menu.locator(f'a[href="{prefix}/seo/"]').is_visible()
                    page.keyboard.press("Escape")
                    assert not menu.evaluate("element => element.open")
                assert not errors, errors
                context.close()

            context = browser.new_context(viewport={"width": 390, "height": 844})
            context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
            page = context.new_page()
            requests, failed = [], [False]

            def lead(route):
                requests.append(route.request.post_data_json)
                route.fulfill(
                    status=500 if failed[0] else 200,
                    content_type="application/json",
                    body=json.dumps({"ok": not failed[0], "saved": not failed[0], "mail": not failed[0]}),
                )

            page.route("**/lead.php", lead)
            page.goto(BASE + prefix + "/seo/", wait_until="domcontentloaded")
            page.locator("main a.btn-primary").first.click()
            page.wait_for_url("**/contact/**")
            form = page.locator("[data-contact-form]")
            for fail in (False, True):
                failed[0] = fail
                form.locator('[name="name"]').fill("Synthetic SEO enquiry")
                form.locator('[name="email"]').fill("seo-test@example.invalid")
                form.locator('[name="service"]').select_option("seo")
                form.locator('[name="description"]').fill("Synthetic monthly SEO/GEO enquiry without real delivery.")
                form.locator('[type="submit"]').click()
                if fail:
                    page.wait_for_function("document.querySelector('.form-status').getAttribute('role') === 'alert'")
                    assert form.locator('[name="service"]').input_value() == "seo"
                    assert form.locator('[name="description"]').input_value().startswith("Synthetic")
                else:
                    page.wait_for_function("document.querySelector('[name=\"name\"]').value === ''")
                assert requests[-1]["service"] == "seo" and requests[-1]["_form"] == "studio"
            context.close()
        browser.close()
    print("PASS: SEO/GEO at five widths in both languages, mobile menu, service CTA and mocked contact success/failure.")


if __name__ == "__main__":
    main()
