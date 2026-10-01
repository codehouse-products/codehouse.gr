#!/usr/bin/env python3
"""Check hero playback and controls without interacting with any contact form."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "https://" + os.environ["REPLIT_DEV_DOMAIN"]
CHROMIUM = "/nix/store/5afrhwm7zqn1vb7p5z1mc2rkh2grsfgz-ungoogled-chromium-138.0.7204.100/bin/chromium"
OUTPUT = Path("/tmp/codehouse-video-qa")


def state(page):
    return page.locator(".hero-video.is-active").evaluate(
        "(v)=>({paused:v.paused,time:v.currentTime,error:v.error?.message,width:v.videoWidth,height:v.videoHeight,duration:v.duration})"
    )


def main():
    OUTPUT.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=CHROMIUM, args=["--no-sandbox"])
        context = browser.new_context(ignore_https_errors=True)
        context.add_init_script("localStorage.setItem('cookieConsent','rejected')")
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        for name, width, height, route in (
            ("desktop-el", 1440, 900, "/"),
            ("mobile-el", 360, 800, "/"),
            ("desktop-en", 1440, 900, "/en/"),
        ):
            page.set_viewport_size({"width": width, "height": height})
            page.goto(BASE + route, wait_until="domcontentloaded")
            page.wait_for_function("document.querySelector('.hero-video.is-active').currentTime > .2")
            clip_count = page.locator("[data-hero-videos]").evaluate("(h)=>JSON.parse(h.dataset.playlist).length")
            assert clip_count == 6, f"Expected six films, got {clip_count}"
            playlist = page.locator("[data-hero-videos]").evaluate("(h)=>JSON.parse(h.dataset.playlist)")
            assert any("visual-studio." in clip["src"] for clip in playlist)
            assert not any("photoshop-artist." in clip["src"] for clip in playlist)
            assert not any("eraser-paper." in clip["src"] or "ink-line." in clip["src"] for clip in playlist)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            assert page.locator(".hero-logo").evaluate("(i)=>i.complete && i.naturalWidth>0")
            assert page.locator(".hero-video").first.evaluate("(v)=>getComputedStyle(v).transitionDuration") == "0s"
            for index in range(clip_count):
                if index:
                    page.locator("[data-video-next]").click()
                    page.wait_for_function("(i)=>document.querySelector('[data-hero-videos]').dataset.videoIndex===String(i)", arg=index)
                    page.wait_for_function("document.querySelector('.hero-video.is-active').currentTime > .1")
                assert page.locator(".hero-video.is-active").count() == 1
                video = state(page)
                assert not video["error"], video
                assert video["width"] == 1920 and video["height"] == 1080, video
                assert abs(video["duration"] - 6) < .1, video
                assert page.locator(".hero-video-layer").evaluate("(h)=>getComputedStyle(h,'::after').backgroundImage") != "none"
                page.screenshot(path=str(OUTPUT / f"{name}-{index}.png"))
            page.locator("[data-video-toggle]").click()
            assert state(page)["paused"]
            assert page.locator(".hero-video-layer").evaluate("(h)=>getComputedStyle(h,'::after').animationPlayState") == "paused"
            before = state(page)["time"]
            page.wait_for_timeout(350)
            assert abs(state(page)["time"] - before) < .1
            page.locator("[data-video-toggle]").click()
            page.wait_for_function("!document.querySelector('.hero-video.is-active').paused")
            page.locator(".hero-video.is-active").evaluate("(v)=>v.currentTime=v.duration-.15")
            page.wait_for_function("document.querySelector('[data-hero-videos]').dataset.videoIndex==='0'")
            # Nearest-element scrolling may leave >15% of the hero visible.
            # Move the entire film outside the viewport before asserting pause.
            page.locator(".hero").evaluate("(hero)=>window.scrollTo(0,scrollY+hero.getBoundingClientRect().bottom+1)")
            page.wait_for_function("document.querySelector('.hero-video.is-active').paused")
            print(f"PASS: {name}: all scenes, direct cuts, pause/resume, looping and offscreen pause")
        reduced = browser.new_context(ignore_https_errors=True, reduced_motion="reduce")
        reduced.add_init_script("localStorage.setItem('cookieConsent','rejected')")
        reduced_page = reduced.new_page()
        reduced_page.goto(BASE + "/", wait_until="domcontentloaded")
        reduced_page.wait_for_selector(".hero-video-controls:not([hidden])")
        assert state(reduced_page)["paused"] and state(reduced_page)["time"] == 0
        assert reduced_page.locator(".hero-video-layer").evaluate("(h)=>getComputedStyle(h,'::after').animationName") == "none"
        reduced_page.locator("[data-video-toggle]").click()
        reduced_page.wait_for_function("document.querySelector('.hero-video.is-active').currentTime > .2")
        print("PASS: reduced motion starts still; explicit Play works")
        assert not errors, errors
        browser.close()
    print(json.dumps({"screenshots": str(OUTPUT), "pageErrors": errors}))


if __name__ == "__main__":
    main()