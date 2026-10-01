#!/usr/bin/env python3
"""Targeted legacy-shell regressions; never select or submit form answers."""
from pathlib import Path

from playwright.sync_api import sync_playwright
from test_hero_video import BASE, CHROMIUM

OUTPUT = Path("/tmp/codehouse-visual-consistency")
ROUTES = (
    "/aporrito/",
    "/prosfora/",
    "/dorean-istoselida/",
    "/seo/",
    "/dimioyrgia-site/",
)

# Composite translucent backgrounds over ancestor surfaces. For an image-backed
# dark caption, white beneath its background is the conservative contrast bound:
# darker image pixels only increase contrast with its light foreground.
CONTRAST = """element => {
  const parse = color => color.match(/[\\d.]+/g).map(Number);
  const over = (foreground, background) => [0, 1, 2].map(index =>
    foreground[index] * (foreground[3] ?? 1) +
    background[index] * (1 - (foreground[3] ?? 1)));
  const luminance = color => color.slice(0, 3).map(value => value / 255)
    .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
    .reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0);
  const layers = [];
  for (let ancestor = element; ancestor; ancestor = ancestor.parentElement)
    layers.push(parse(getComputedStyle(ancestor).backgroundColor));
  const background = layers.reverse().reduce(
    (surface, layer) => over(layer, surface), [255, 255, 255]);
  const style = getComputedStyle(element);
  const foreground = over(parse(style.color), background);
  const ratio = (Math.max(luminance(foreground), luminance(background)) + .05) /
    (Math.min(luminance(foreground), luminance(background)) + .05);
  return {ratio, color: style.color, background,
    text: element.textContent.trim().slice(0, 80)};
}"""


def assert_contrast(page, selector, route, minimum=4.5):
    elements = page.locator(selector)
    assert elements.count(), (route, "missing contrast target", selector)
    ratios = []
    for element in elements.all():
        if not element.is_visible():
            continue
        measurement = element.evaluate(CONTRAST)
        assert measurement["ratio"] >= minimum, (route, selector, measurement)
        ratios.append(measurement["ratio"])
    assert ratios, (route, "no visible contrast targets", selector)
    return min(ratios)


def assert_logos(page, route):
    for selector, asset in (
        (".legacy-editorial-brand img", "/assets/studio/logo-user-black.png"),
        (".legacy-editorial-footer .footer-logo", "/assets/studio/logo-user-white.png"),
    ):
        image = page.locator(selector)
        assert image.count() == 1, (route, selector, "missing or duplicated logo")
        assert image.get_attribute("src") == asset, (route, selector, "outdated logo")
        image.scroll_into_view_if_needed()
        page.wait_for_function(
            "selector => { const image = document.querySelector(selector); "
            "return image.complete && image.naturalWidth > 0; }",
            arg=selector,
        )
        assert image.is_visible(), (route, selector, "hidden logo")


def assert_option_focus(page, route, screenshot):
    page.locator("#quizForm").scroll_into_view_if_needed()
    page.locator(".quiz-step.active .opt input").first.focus()
    # Use genuine keyboard navigation to activate :focus-visible without
    # selecting a radio, advancing the questionnaire, or submitting anything.
    page.keyboard.press("Tab")
    page.keyboard.press("Shift+Tab")
    focused = page.locator(".opt input:focus-visible")
    assert focused.count() == 1, (route, "option did not receive keyboard focus")
    option = focused.locator("..")
    span = option.locator("span").first
    indicator = span.evaluate("""element => {
      const style = getComputedStyle(element);
      const box = element.getBoundingClientRect();
      return {style: style.outlineStyle, width: parseFloat(style.outlineWidth),
        offset: parseFloat(style.outlineOffset), opacity: parseFloat(style.opacity),
        visibility: style.visibility, size: box.width * box.height,
        color: style.outlineColor, textColor: style.color};
    }""")
    assert indicator["style"] not in ("none", "hidden"), (route, indicator)
    assert indicator["width"] >= 2 and indicator["offset"] >= 0, (route, indicator)
    assert indicator["opacity"] > 0 and indicator["visibility"] == "visible", (
        route, indicator)
    assert indicator["size"] > 0, (route, indicator)
    # The repaired outline uses the same high-contrast ink as the option text.
    assert indicator["color"] == indicator["textColor"], (route, indicator)
    assert_contrast(page, ".opt input:focus-visible + span", route, minimum=3)
    option.scroll_into_view_if_needed()
    # An element-only crop would cut off the outline outside the option box.
    page.screenshot(path=str(screenshot))


def main():
    OUTPUT.mkdir(exist_ok=True)
    forbidden_requests = []
    minimum_ratios = {"legal": [], "faq": [], "caption": [], "offer": []}
    checks = 0
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM,
                                              args=["--no-sandbox"])
        context = browser.new_context(ignore_https_errors=True,
                                       reduced_motion="reduce")
        context.add_init_script("localStorage.setItem('cookieConsent','rejected')")

        def block_lead_request(request):
            forbidden_requests.append(request.request.url)
            request.abort()

        context.route("**/lead.php", block_lead_request)
        page = context.new_page()
        for viewport, width, height in (
            ("desktop", 1440, 900),
            ("mobile", 360, 800),
        ):
            page.set_viewport_size({"width": width, "height": height})
            for locale, prefix in (("el", ""), ("en", "/en")):
                for path in ROUTES:
                    route = prefix + path
                    response = page.goto(BASE + route, wait_until="domcontentloaded",
                                         timeout=60000)
                    assert response.status == 200, (route, response.status)
                    page.wait_for_function(
                        "getComputedStyle(document.body).getPropertyValue('--sans')"
                        ".includes('Noto Sans')"
                    )
                    page.evaluate("document.fonts.ready")
                    assert_logos(page, route)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth + 1"
                    ), (route, width, "horizontal overflow")
                    name = f"{viewport}-{locale}-{path.strip('/')}"
                    if path == "/aporrito/":
                        minimum_ratios["legal"].append(assert_contrast(
                            page, ".legal p, .legal li, .legal strong, .legal a", route))
                        page.locator(".legal").screenshot(
                            path=str(OUTPUT / f"{name}-legal.png"))
                    elif path == "/prosfora/":
                        minimum_ratios["offer"].append(assert_contrast(
                            page, ".pf-lead, .pf-terms li, .pf-terms strong", route))
                        assert_option_focus(page, route, OUTPUT / f"{name}-focus.png")
                    if path == "/dorean-istoselida/":
                        minimum_ratios["faq"].append(assert_contrast(
                            page, ".df-faq summary", route))
                        first = page.locator(".df-faq details").first
                        first.locator("summary").click()
                        minimum_ratios["faq"].append(assert_contrast(
                            page, ".df-faq details[open] p", route))
                        first.screenshot(path=str(OUTPUT / f"{name}-faq.png"))
                    if path in ("/dorean-istoselida/", "/seo/", "/dimioyrgia-site/"):
                        selector = (".df-visual-label" if path == "/dorean-istoselida/"
                                    else ".lp-visual-label")
                        minimum_ratios["caption"].append(assert_contrast(
                            page, selector, route))
                        page.locator(selector).screenshot(
                            path=str(OUTPUT / f"{name}-caption.png"))
                    checks += 1
                    print(f"PASS: {route} {width}px: contrast, applicable focus, "
                          "current logos, no overflow", flush=True)
        assert not forbidden_requests, ("Unexpected lead requests", forbidden_requests)
        browser.close()
    print(f"PASS: {checks} targeted route/viewport checks; no form submissions.")
    print("Minimum contrast ratios: " + ", ".join(
        f"{name} {min(ratios):.2f}:1" for name, ratios in minimum_ratios.items()))
    print(f"Screenshots: {OUTPUT}")


if __name__ == "__main__":
    main()