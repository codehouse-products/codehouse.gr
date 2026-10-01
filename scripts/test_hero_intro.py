#!/usr/bin/env python3
"""Check loading/player continuity, progress, keyboard entry and failure paths."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright
from test_hero_video import BASE, CHROMIUM

OUTPUT = Path("/tmp/codehouse-loading-qa")


def entered(page):
    page.wait_for_function(
        "document.querySelector('[data-hero-videos]').dataset.introState === 'entered'"
    )
    page.wait_for_function("!document.documentElement.classList.contains('intro-pending')")
    assert not page.locator("main").evaluate("element => element.inert")
    assert page.evaluate("document.documentElement.getAttribute('aria-busy') !== 'true'")


def main():
    OUTPUT.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM,
                                              args=["--no-sandbox"])
        normal_cases = [
            ("desktop-el", 1440, 900, "/"),
            ("mobile-el", 360, 800, "/"),
            ("desktop-en", 1440, 900, "/en/"),
            ("mobile-en", 360, 800, "/en/"),
        ]
        if "--english-only" in sys.argv:
            normal_cases = [case for case in normal_cases if case[3] == "/en/"]
        for name, width, height, path in ([] if "--failure-paths" in sys.argv else normal_cases):
            context = browser.new_context(ignore_https_errors=True,
                                           viewport={"width": width, "height": height})
            context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE + path, wait_until="domcontentloaded")
            page.wait_for_function(
                "document.querySelector('.hero-video.is-active').currentTime > .15"
            )
            assert page.locator(".hero-loading-screen").is_visible()
            assert page.locator("main").evaluate("element => element.inert")
            assert page.locator("[data-intro-skip]").evaluate("e=>e===document.activeElement")
            page.evaluate("""() => {
              const video = document.querySelector('.hero-video.is-active');
              window.introVideo = video;
              window.introStartTime = video.currentTime;
              window.introEvents = [];
              for (const event of ['pause','seeking','loadstart','emptied']) {
                video.addEventListener(event, () => window.introEvents.push(event));
              }
              window.introRect = video.getBoundingClientRect().toJSON();
            }""")
            before = int(page.locator('[role="progressbar"]').get_attribute("aria-valuenow"))
            page.wait_for_timeout(250)
            after = int(page.locator('[role="progressbar"]').get_attribute("aria-valuenow"))
            assert 0 <= before < after < 100, (before, after)
            page.screenshot(path=str(OUTPUT / (name + "-loading.png")))
            entered(page)
            result = page.evaluate("""() => {
              const video = document.querySelector('.hero-video.is-active');
              return {same:video===window.introVideo,time:video.currentTime,
                start:window.introStartTime,
                exit:Number(document.querySelector('[data-hero-videos]').dataset.introExitTime),
                paused:video.paused,events:window.introEvents,
                rect:video.getBoundingClientRect().toJSON(),before:window.introRect,
                reason:document.querySelector('[data-hero-videos]').dataset.introReason};
            }""")
            assert result["same"] and not result["paused"], result
            # The decoder's media clock can lag the intro's visible-wall-time
            # clock under load. Verify continuity, not a fixed media timestamp.
            assert result["exit"] > result["start"] and result["time"] >= result["exit"], result
            assert not result["events"] and result["rect"] == result["before"], result
            assert result["reason"] == "ready", result
            assert page.evaluate("document.activeElement.closest('.site-header') !== null")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            page.wait_for_timeout(500)
            assert page.locator(".hero-loading-screen").count() == 0
            page.screenshot(path=str(OUTPUT / (name + "-site.png")))
            print("PASS:", name, "same DOM player, unchanged frame/crop, advancing timeline, progress and unlock")
            context.close()

        for scenario in ["skip", "reduced", "blocked-video", "blocked-autoplay", "blocked-module", "no-js", "deep-link"]:
            context = browser.new_context(ignore_https_errors=True,
                reduced_motion="reduce" if scenario == "reduced" else "no-preference",
                java_script_enabled=scenario != "no-js")
            context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
            if scenario == "blocked-autoplay":
                context.add_init_script("HTMLMediaElement.prototype.play=function(){return Promise.reject(new DOMException('Playback blocked','NotAllowedError'))}")
            if scenario == "blocked-video":
                context.route("**/assets/studio/videos/**", lambda route: route.abort())
            if scenario == "blocked-module":
                context.route("**/assets/studio/hero-video.js", lambda route: route.abort())
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(BASE + ("/#service-rail" if scenario == "deep-link" else "/"),
                      wait_until="domcontentloaded")
            if scenario == "skip":
                page.wait_for_selector("[data-intro-skip]")
                page.keyboard.press("Tab")
                assert page.locator("[data-intro-skip]").evaluate("e=>e===document.activeElement")
                page.keyboard.press("Enter")
                entered(page)
            elif scenario == "blocked-module":
                page.wait_for_function(
                    "!document.documentElement.classList.contains('intro-pending')",
                    timeout=12000)
            elif scenario == "no-js":
                # With scripting disabled, DOMContentLoaded need not wait for
                # CSS imports. Assert the rendered state once styles arrive.
                page.wait_for_selector(".hero-loading-screen", state="hidden")
                assert not page.locator(".hero-loading-screen").is_visible()
            else:
                entered(page)
                if scenario == "reduced":
                    assert page.locator(".hero-video.is-active").evaluate("v=>v.paused && v.currentTime===0")
                if scenario == "blocked-video":
                    assert page.locator('[data-hero-videos]').get_attribute("data-intro-reason") == "video-unavailable"
                if scenario == "blocked-autoplay":
                    assert page.locator('[data-hero-videos]').get_attribute("data-intro-reason") == "autoplay-blocked"
            assert page.locator(".site-header").is_visible()
            context.close()
            print("PASS: accessible exit/fail-open:", scenario)
        browser.close()
    assert not errors, errors
    print("PASS: no page errors; captures:", OUTPUT)


if __name__ == "__main__":
    main()