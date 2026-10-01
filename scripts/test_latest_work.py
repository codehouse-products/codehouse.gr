#!/usr/bin/env python3
"""Verify the four selected client projects on both homepages and viewport sizes."""
from playwright.sync_api import sync_playwright
from test_hero_video import BASE, CHROMIUM

EXPECTED = ["HIGH HOPE", "GERAKOS", "KC TRAVEL", "AKRI"]
WEBSITES = [
    "https://highhopeathens.gr",
    "https://gerakos.gr",
    "https://kctravel.gr",
    "https://akriprojects.gr",
]


def main():
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=CHROMIUM, args=["--no-sandbox"])
        context = browser.new_context(ignore_https_errors=True,
                                      reduced_motion="reduce")
        context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        for route, heading in (("/", "Οι τελευταίες μας δουλειές"),
                               ("/en/", "Our latest work")):
            for width, height in ((1440, 900), (360, 800)):
                page.set_viewport_size({"width": width, "height": height})
                page.goto(BASE + route, wait_until="domcontentloaded")
                assert page.locator("#work h2").inner_text() == heading
                assert page.locator("#project-rail h3").all_text_contents() == EXPECTED
                assert page.locator("#work .project-actions a[target='_blank']").evaluate_all(
                    "(links)=>links.map(link=>link.getAttribute('href'))") == WEBSITES
                assert page.locator("#work .section-heading a").get_attribute("href") == (
                    "/douleies/" if route == "/" else "/en/douleies/")
                for image in page.locator("#project-rail img:not([hidden])").all():
                    image.scroll_into_view_if_needed()
                    image.evaluate(
                        "(i)=>i.complete ? (i.naturalWidth>0 || Promise.reject('Broken image'))"
                        " : new Promise((resolve,reject)=>{i.onload=resolve;i.onerror=reject})")
                    assert image.evaluate(
                        "(i)=>getComputedStyle(i).objectFit==='cover'"), "Project photo is letterboxed"
                    assert image.evaluate(
                        "(i)=>{const a=i.getBoundingClientRect(),b=i.closest('.project-image').getBoundingClientRect();"
                        "return a.width>=b.width-1&&a.height>=b.height-1}"), "Project photo does not fill its frame"
                rail = page.locator("#project-rail")
                rail.evaluate("(r)=>r.scrollLeft=0")
                next_button = page.locator("[data-rail-control='#project-rail'][data-dir='next']")
                page.wait_for_timeout(100)
                for _ in range(6):
                    if next_button.is_disabled():
                        break
                    next_button.click()
                    page.wait_for_timeout(200)
                assert next_button.is_disabled(), "Cannot reach the end of the project rail"
                assert page.locator("[data-rail-position='#project-rail']").inner_text().endswith("/ 04")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
                page.screenshot(path=f"/tmp/latest-work-{width}-{'en' if route=='/en/' else 'el'}.png")
                print(f"PASS: {route} {width}px: four clients, heading, images, links and carousel")
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    main()