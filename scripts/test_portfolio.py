#!/usr/bin/env python3
"""Regression checks for the four-client portfolio across generated and legacy pages."""
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
SLUGS = ["high-hope", "gerakos", "kc-travel", "akri"]
NAMES = ["HIGH HOPE", "GERAKOS", "KC TRAVEL", "AKRI"]
DOMAINS = [
    "highhopeathens.gr",
    "gerakos.gr",
    "kctravel.gr",
    "akriprojects.gr",
]
REMOVED = ("AMMO", "ELITE", "ANTHOS")


def read(route):
    return (ROOT / route).read_text(encoding="utf-8")


def assert_visible_cards(page, expected=NAMES):
    cards = re.findall(
        r'(<article class="project-card">.*?<h3>(.*?)</h3>.*?</article>)',
        page,
        flags=re.S,
    )
    assert [name for _, name in cards] == expected, f"Unexpected visible project cards: {[name for _, name in cards]}"
    for name in REMOVED:
        assert all(name not in card for card, _ in cards), f"Archived project {name} appears on a portfolio surface"
    assert all('/projects/codehouse/' not in card for card, _ in cards)


def main():
    data = json.loads(read("assets/studio/data.json"))
    visible = [project for project in data["projects"] if project.get("visible")]
    assert [project["slug"] for project in visible] == SLUGS
    assert data["homeProjects"] == [{"slug": slug} for slug in SLUGS]
    assert len(visible) == 4
    archived = {project["slug"]: project for project in data["projects"] if not project.get("visible")}
    assert "codehouse" in archived, "Old project details should remain explicitly archived"
    projects = {project["slug"]: project for project in visible}
    for slug, domain in zip(SLUGS, DOMAINS):
        project = projects[slug]
        assert project["domain"] == domain
        assert project["description"]["el"] and project["description"]["en"]
        assert project["goal"]["el"] and project["goal"]["en"]
        assert project["solution"]["el"] and project["solution"]["en"]
    assert projects["high-hope"]["cover"] == "assets/studio/images/project-highhope-live.webp"
    assert projects["high-hope"]["gallery"], "High Hope gallery must remain available"
    assert projects["gerakos"]["cover"] == "assets/studio/images/project-gerakos.webp"
    assert projects["akri"]["cover"] == "assets/studio/images/project-akri.webp"
    assert all(projects[slug]["mobileWidth"] == 390 for slug in ("gerakos", "akri"))
    assert all(projects[slug]["mobileHeight"] == 740 for slug in ("gerakos", "akri"))
    assert all(projects[slug]["desktop"] == f"assets/studio/images/{slug}-desktop.webp"
               for slug in ("gerakos", "akri"))

    for route in (
        "index.html",
        "en/index.html",
        "projects/index.html",
        "en/projects/index.html",
        "studio/index.html",
        "en/studio/index.html",
        "services/web-design/index.html",
        "en/services/web-design/index.html",
    ):
        assert_visible_cards(read(route))

    for route in ("douleies/index.html", "en/douleies/index.html"):
        page = read(route)
        assert [page.count(f'data-cat="{category}"') for category in ("estiasi", "tourismos")] == (
            [3, 1] if route.startswith("douleies/") else [3, 1]
        )
        assert len(re.findall(r'<article class="wk-case', page)) == 4
        case_cards = re.findall(r'<article class="wk-case.*?</article>', page, flags=re.S)
        for name in REMOVED:
            assert all(name not in card for card in case_cards)
        for domain in DOMAINS:
            assert domain in page

    for slug in SLUGS:
        for prefix in ("projects", "en/projects"):
            assert (ROOT / prefix / slug / "index.html").is_file()
    assert (ROOT / "projects/codehouse/index.html").is_file()
    assert (ROOT / "en/projects/codehouse/index.html").is_file()
    print("PASS: four visible clients, bilingual portfolio surfaces, legacy listings, metadata and routes")


if __name__ == "__main__":
    main()