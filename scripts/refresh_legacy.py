#!/usr/bin/env python3
"""Apply the monochrome editorial shell to paired archival public pages.

The script is intentionally idempotent and limited to the Greek and English
archive roots below. It does not rewrite article copy, SEO metadata, schema,
or in-page links. Visible shell language links point to real paired routes.
"""

from html.parser import HTMLParser
from hashlib import sha256
from pathlib import Path
import json
import re


ROOT = Path(__file__).resolve().parents[1]
# Whitespace-normalized fingerprints of the archived standalone SDK bootstraps.
# Unknown/mixed scripts require review rather than risking deletion of app code.
LEGACY_TRACKER_BOOTSTRAPS = {
    "e95acfe8ef2deb2c51c64746eed08cdf5f04a3e0360a154d7c3261bb930a1405",
    "cce64b55570422259ba6c2433d893a0591e6ac4d5e7d7c0d43156a712a5a6765",
    "d9ead7824b81044ff23f50aa89bf6c1c1a0dcf5e553028d92b42fdf16e90c3e9",
    "1f6e1e4470bb9c92f683923de3d041e34359daf2e79c21448096a20369c19ca4",
    "a067572d27cb2b4df7beb9198336eea884afd3f393e77028248e5c43dd9d2a2d",
    "d4d9bdb9d75655bfac8b7e63060c09d6e4d6c183bd7834e13b8d36ba97b94b13",
    "b576a79542268151bac6ca8153ee941d1c377b61f707989f144e8d7ecd3ac33f",
}
LEGACY_ROOTS = (
    "blog",
    "douleies",
    "qr-menu",
    "dimioyrgia-site",
    "seo",
    "dorean-istoselida",
    "aporrito",
    "prosfora",
)
NAV_LABELS = {
    "el": (
        ("services", "Υπηρεσίες"),
        ("projects", "Έργα"),
        ("studio", "Studio"),
        ("contact", "Επικοινωνία"),
        ("blog", "Blog"),
        ("prosfora", "Προσφορά"),
    ),
    "en": (
        ("services", "Services"),
        ("projects", "Projects"),
        ("studio", "Studio"),
        ("contact", "Contact"),
        ("blog", "Blog"),
        ("prosfora", "Offer"),
    ),
}


class ElementFinder(HTMLParser):
    """Locate complete matching top-level header/footer elements by source span."""

    def __init__(self, source, target):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.target = target
        self.offsets = [0]
        self.offsets.extend(i + 1 for i, char in enumerate(source) if char == "\n")
        self.active = None
        self.matches = []
        self.feed(source)

    def source_offset(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        wanted = (
            tag == "header" and self.target == "header"
            and bool(classes.intersection({"nav", "bnav", "legacy-editorial-nav"}))
        ) or (
            tag == "footer" and self.target == "footer"
            and bool(classes.intersection({"footer", "bfooter", "legacy-editorial-footer"}))
        )
        if self.active:
            if tag == self.target:
                self.active["depth"] += 1
        elif wanted:
            self.active = {"start": self.source_offset(), "depth": 1}

    def handle_endtag(self, tag):
        if not self.active or tag != self.target:
            return
        self.active["depth"] -= 1
        if self.active["depth"] == 0:
            start = self.active["start"]
            close = self.source_offset()
            end = self.source.find(">", close) + 1
            if end > close:
                self.matches.append((start, end))
            self.active = None


class TableFinder(HTMLParser):
    """Find unwrapped table source spans without rewriting table contents."""

    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0]
        self.offsets.extend(i + 1 for i, char in enumerate(source) if char == "\n")
        self.stack = []
        self.tables = []
        self.matches = []
        self.feed(source)

    def source_offset(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "table":
            wrapped = any(
                parent_tag == "div" and "legacy-table-scroll" in parent_classes
                for parent_tag, parent_classes in self.stack
            )
            self.tables.append({"start": self.source_offset(), "wrapped": wrapped})
        if tag not in self.VOID_ELEMENTS:
            self.stack.append((tag, classes))

    def handle_endtag(self, tag):
        if tag == "table" and self.tables:
            table = self.tables.pop()
            if not table["wrapped"]:
                close = self.source_offset()
                end = self.source.find(">", close) + 1
                if end > close:
                    self.matches.append((table["start"], end))
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def element_spans(source, target):
    return ElementFinder(source, target).matches


def page_locale(path):
    return "en" if path.relative_to(ROOT).as_posix().startswith("en/") else "el"


def wrap_tables(source, path):
    spans = TableFinder(source).matches
    if not spans:
        return source
    label = "Scrollable table" if page_locale(path) == "en" else "Πίνακας με οριζόντια κύλιση"
    opening = (
        f'<div class="legacy-table-scroll" role="region" tabindex="0" '
        f'aria-label="{label}">'
    )
    for start, end in reversed(spans):
        source = source[:end] + "</div>" + source[end:]
        source = source[:start] + opening + source[start:]
    return source


def page_routes(path):
    relative = path.relative_to(ROOT).parent.as_posix()
    if relative.startswith("en/"):
        english = "/" + relative + "/"
        greek = "/" + relative.removeprefix("en/") + "/"
    else:
        greek = "/" + relative + "/"
        english = "/en" + greek
    return greek, english


def active_section(path):
    route = path.relative_to(ROOT).parent.as_posix().removeprefix("en/")
    if route == "blog" or route.startswith("blog/"):
        return "blog"
    if route == "douleies" or route.startswith("douleies/"):
        return "projects"
    if route == "prosfora" or route.startswith("prosfora/"):
        return "prosfora"
    if route in {"qr-menu", "seo", "dimioyrgia-site", "dorean-istoselida"}:
        return "services"
    return None


def editorial_nav(path, main_target):
    locale = page_locale(path)
    labels = NAV_LABELS[locale]
    greek, english = page_routes(path)
    active = active_section(path)
    desktop_links = "".join(
        f'<a href="/{"en/" if locale == "en" else ""}{route}/"'
        + (' aria-current="page"' if route == active else "")
        + f">{label}</a>"
        for route, label in labels
    )
    mobile_links = "".join(
        f'<a href="/{"en/" if locale == "en" else ""}{route}/"'
        + (' aria-current="page"' if route == active else "")
        + f">{label}</a>"
        for route, label in labels
    )
    language_label = "Language" if locale == "en" else "Γλώσσα"
    language_nav = (
        f'<!-- locale-pair --><nav class="legacy-language" aria-label="{language_label}">'
        f'<a href="{greek}" lang="el"'
        + (' aria-current="page"' if locale == "el" else "")
        + '>GR</a><span aria-hidden="true"> / </span>'
        f'<a href="{english}" lang="en"'
        + (' aria-current="page"' if locale == "en" else "")
        + f">EN</a></nav><!-- /locale-pair -->"
    )
    return f"""<!-- Legacy editorial navigation -->
<a class="legacy-skip-link" href="#{main_target}">{"Skip to content" if locale == "en" else "Μετάβαση στο περιεχόμενο"}</a>
<header class="legacy-editorial-nav">
  <a class="legacy-editorial-brand" href="/{"en/" if locale == "en" else ""}" aria-label="{"Codehouse — Home" if locale == "en" else "Codehouse — Αρχική"}">
    <img src="/assets/studio/logo-user-black.png" alt="Codehouse" width="58" height="58">
  </a>
  <nav class="legacy-editorial-links" aria-label="{"Main navigation" if locale == "en" else "Κύρια πλοήγηση"}">{desktop_links}</nav>
  {language_nav}
  <details class="legacy-mobile-nav" data-legacy-mobile-menu>
    <summary aria-label="{"Open navigation" if locale == "en" else "Άνοιγμα πλοήγησης"}">{"Menu" if locale == "en" else "Μενού"}</summary>
    <nav aria-label="{"Mobile navigation" if locale == "en" else "Πλοήγηση για κινητά"}">{mobile_links}</nav>
  </details>
</header>"""


def editorial_footer_nav(path):
    locale = page_locale(path)
    prefix = "/en/" if locale == "en" else "/"
    links = "".join(
        f'<a href="{prefix}{route}/">{label}</a>'
        for route, label in NAV_LABELS[locale]
    )
    links += f'<a href="{prefix}aporrito/">{"Privacy policy" if locale == "en" else "Πολιτική απορρήτου"}</a>'
    label = "Footer navigation" if locale == "en" else "Πλοήγηση υποσέλιδου"
    return f'<nav class="legacy-footer-nav" aria-label="{label}">{links}</nav>'


def update_body_class(source):
    match = re.search(r"<body\b[^>]*>", source, flags=re.IGNORECASE)
    if not match:
        raise ValueError("Missing body element")
    opening = match.group(0)
    if "legacy-page" in opening:
        return source
    class_match = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', opening, re.I)
    if class_match:
        replacement = class_match.group(0).replace(
            class_match.group(2), f"{class_match.group(2)} legacy-page", 1
        )
        opening = opening[:class_match.start()] + replacement + opening[class_match.end():]
    else:
        opening = opening[:-1] + ' class="legacy-page">'
    return source[:match.start()] + opening + source[match.end():]


def update_main_target(source):
    match = re.search(r"<(?:main|article)\b[^>]*>", source, flags=re.IGNORECASE)
    if not match:
        return source, "top"
    opening = match.group(0)
    id_match = re.search(r'\bid\s*=\s*(["\'])(.*?)\1', opening, re.I)
    if id_match:
        target = id_match.group(2)
        updated = opening
        if not re.search(r'\btabindex\s*=', opening, re.I):
            updated = opening[:-1] + ' tabindex="-1">'
    else:
        target = "legacy-main-content"
        updated = opening[:-1] + f' id="{target}" tabindex="-1">'
    return source[:match.start()] + updated + source[match.end():], target


def rewrite_shell_hrefs(fragment):
    replacements = {
        "/#services": "/services/",
        "/en/#services": "/en/services/",
        "/#process": "/services/#services",
        "/en/#process": "/en/services/#services",
        "/#faq": "/qr-menu/#faq",
        "/en/#faq": "/en/qr-menu/#faq",
        "/#quiz": "/contact/",
        "/en/#quiz": "/en/contact/",
        "/douleies/": "/projects/",
        "/en/douleies/": "/en/projects/",
    }
    for old, new in replacements.items():
        fragment = fragment.replace(f'href="{old}"', f'href="{new}"')
        fragment = fragment.replace(f"href='{old}'", f"href='{new}'")
    return fragment


def rewrite_existing_shell_links(source):
    containers = (
        r'<div\b(?=[^>]*\bclass=["\'][^"\']*legacy-compat-chrome[^"\']*["\'])[^>]*>.*?</div>',
        r'<div\b(?=[^>]*\bclass=["\'][^"\']*mobile-menu[^"\']*["\'])[^>]*>.*?</div>',
        r'<footer\b[^>]*>.*?</footer>',
    )
    for pattern in containers:
        source = re.sub(
            pattern,
            lambda match: rewrite_shell_hrefs(match.group(0)),
            source,
            flags=re.I | re.S,
        )
    return source


def update_header(source, path, main_target):
    source = re.sub(
        r'<a\b(?=[^>]*\bclass=["\'][^"\']*\blegacy-skip-link\b[^"\']*["\'])[^>]*>.*?</a>\s*',
        "",
        source,
        flags=re.I | re.S,
    )
    source = re.sub(
        r'<!--\s*(?:Legacy|English) editorial navigation\s*-->\s*',
        "",
        source,
        flags=re.I,
    )
    spans = element_spans(source, "header")
    if not spans:
        raise ValueError("Missing legacy top-level navigation header")
    start, end = spans[0]
    old_header = source[start:end]
    if "legacy-editorial-nav" in old_header:
        replacement = editorial_nav(path, main_target)
    else:
        old_header = rewrite_shell_hrefs(old_header)
        replacement = (
            editorial_nav(path, main_target)
            + '\n<div class="legacy-compat-chrome" aria-hidden="true" inert hidden>\n'
            + old_header
            + "\n</div>"
        )
    return source[:start] + replacement + source[end:]


def update_footer(source, path):
    spans = element_spans(source, "footer")
    if not spans:
        raise ValueError("Missing legacy top-level footer")
    start, end = spans[0]
    footer = source[start:end]
    opening_end = footer.find(">") + 1
    opening = footer[:opening_end]
    class_match = re.search(r'\bclass\s*=\s*(["\'])(.*?)\1', opening, re.I)
    if class_match:
        classes = class_match.group(2).split()
        if "legacy-editorial-footer" not in classes:
            classes.append("legacy-editorial-footer")
        updated_class = " ".join(classes)
        opening = (
            opening[:class_match.start()]
            + f'class="{updated_class}"'
            + opening[class_match.end():]
        )
    else:
        opening = opening[:-1] + ' class="legacy-editorial-footer">'
    if 'data-legacy-editorial-footer="true"' not in opening:
        opening = opening[:-1] + ' data-legacy-editorial-footer="true">'
    footer = opening + footer[opening_end:]
    # Keep archival content and links, but use the current studio identity.
    def current_logo(match):
        image = match.group(0)
        if not re.search(r'src=["\'][^"\']*(?:logo-ch-|logo-wordmark-|logo-user-)', image):
            return image
        image = re.sub(r'\bsrc=["\'][^"\']*["\']', 'src="/assets/studio/logo-user-white.png"', image)
        image = re.sub(r'\s+(?:width|height)=["\'][^"\']*["\']', '', image)
        return re.sub(r'\s*/?>$', ' width="160" height="160">', image)
    footer = re.sub(r'<img\b[^>]*>', current_logo, footer, flags=re.I)
    if 'logo-user-white.png' not in footer:
        prefix = "/en/" if page_locale(path) == "en" else "/"
        brand = f'<a class="legacy-footer-brand" href="{prefix}" aria-label="Codehouse"><img class="footer-logo" src="/assets/studio/logo-user-white.png" alt="Codehouse" width="160" height="160"></a>'
        footer = footer[:len(opening)] + brand + footer[len(opening):]
    nav = editorial_footer_nav(path)
    existing_nav = re.search(
        r'<nav\b(?=[^>]*\bclass=["\'][^"\']*\blegacy-footer-nav\b[^"\']*["\'])[^>]*>.*?</nav>',
        footer,
        flags=re.I | re.S,
    )
    if existing_nav:
        footer = footer[:existing_nav.start()] + nav + footer[existing_nav.end():]
    else:
        closing_start = footer.lower().rfind("</footer>")
        footer = footer[:closing_start] + nav + footer[closing_start:]
    label = "Privacy settings" if page_locale(path) == "en" else "Ρυθμίσεις απορρήτου"
    if 'data-privacy-settings' not in footer:
        button = f'<button class="privacy-settings" data-privacy-settings type="button">{label}</button>'
        closing_start = footer.lower().rfind("</footer>")
        footer = footer[:closing_start] + button + footer[closing_start:]
    else:
        footer = re.sub(
            r'(<button\b(?=[^>]*\bdata-privacy-settings\b)[^>]*>).*?(</button>)',
            lambda match: match[1] + label + match[2], footer, flags=re.I | re.S,
        )
    return source[:start] + footer + source[end:]


def add_assets(source):
    if "/assets/studio/legacy.css" not in source:
        source = re.sub(
            r"</head\s*>",
            '  <link rel="stylesheet" href="/assets/studio/legacy.css">\n</head>',
            source,
            count=1,
            flags=re.IGNORECASE,
        )
    if "/assets/studio/legacy.js" not in source:
        source = re.sub(
            r"</body\s*>",
            '  <script src="/assets/studio/legacy.js" defer></script>\n</body>',
            source,
            count=1,
            flags=re.IGNORECASE,
        )
    return source


def unify_privacy(source):
    """Replace only legacy tracker bootstraps, never form/application scripts."""
    def keep_script(match):
        script = match.group(0)
        opening, body = script.split(">", 1)
        if re.search(r'\btype=["\']application/(?:ld\+)?json["\']', opening, re.I):
            return script
        if re.search(r'\bsrc=["\'][^"\']*(?:googletagmanager\.com/gtag/|cookie_banner(?:\.min)?\.js)', opening):
            return ""
        candidate = "https://www.clarity.ms/tag/" in body or re.search(r'window\.dataLayer\s*=\s*window\.dataLayer\s*\|\|', body)
        if candidate:
            content = re.sub(r'</script\s*>$', '', body, flags=re.I)
            digest = sha256(re.sub(r'\s+', '', content).encode()).hexdigest()
            if digest not in LEGACY_TRACKER_BOOTSTRAPS:
                raise ValueError("Unrecognized analytics block: review and separate application code before migration")
            return ""
        return script
    source = re.sub(r'<script\b[^>]*>.*?</script\s*>', keep_script, source, flags=re.I | re.S)
    if "/assets/studio/privacy.css" not in source:
        source = source.replace("</head>", '<link rel="stylesheet" href="/assets/studio/privacy.css">\n</head>', 1)
    if "/assets/studio/privacy.js" not in source:
        source = source.replace("</body>", '<script src="/assets/studio/privacy.js" defer></script>\n</body>', 1)
    return source


def refresh_legacy_portfolio(path, source):
    """Keep the bilingual legacy portfolio on the same four visible clients."""
    if path.relative_to(ROOT).as_posix() not in {"douleies/index.html", "en/douleies/index.html"}:
        return source
    manifest = json.loads((ROOT / "assets/studio/data.json").read_text(encoding="utf-8"))
    lang = page_locale(path)
    projects = [item for item in manifest.get("projects", []) if item.get("visible", True)]
    if [item["slug"] for item in projects] != ["high-hope", "gerakos", "kc-travel", "akri"]:
        raise ValueError("Legacy portfolio requires High Hope, Gerakos, KC Travel and Akri in order")

    all_label = "Όλα" if lang == "el" else "All"
    hospitality_label = "Εστίαση" if lang == "el" else "Hospitality"
    tourism_label = "Τουρισμός" if lang == "el" else "Tourism"
    filter_aria = "Φίλτρο κατηγορίας" if lang == "el" else "Filter by category"
    section_kicker = "// Τα projects μας" if lang == "el" else "// Our projects"
    heading = (
        'Τέσσερα projects, <span class="accent">τέσσερις διαφορετικές ταυτότητες</span>'
        if lang == "el" else
        'Four projects, <span class="accent">four distinct identities</span>'
    )
    section_sub = (
        "Επιλεγμένες ψηφιακές παρουσίες για επιχειρήσεις στην Αθήνα και τη Σαντορίνη."
        if lang == "el" else
        "Selected digital presences for businesses in Athens and Santorini."
    )
    cards = []
    for index, project in enumerate(projects):
        slug = project["slug"]
        hospitality = slug != "kc-travel"
        category = "estiasi" if hospitality else "tourismos"
        reverse = ' rev' if index % 2 else ''
        loading = 'fetchpriority="high"' if index == 0 else 'loading="lazy"'
        cover = "/" + project.get("cover", project["desktop"])
        cover_alt = project.get("coverAlt", {}).get(lang, project["name"] + (" — εξώφυλλο έργου" if lang == "el" else " — project cover"))
        kicker = project["category"][lang].upper()
        description = project["description"][lang]
        deliverable = project["deliverable"][lang]
        name = project["name"]
        case_path = project.get("caseStudyPath", "/projects/" + slug + "/")
        if case_path and lang == "en" and not case_path.startswith("/en/"):
            case_path = "/en" + case_path
        website_label = "Δες το site" if lang == "el" else "View website"
        view_case = "Δες το project" if lang == "el" else "View project"
        cards.append(f'''    <article class="wk-case{reverse} reveal" data-cat="{category}">
      <div class="wk-case-media">
        <span class="wk-flag">LIVE</span>
        <img src="{cover}" width="{project.get('coverWidth', 819)}" height="{project.get('coverHeight', 1024)}" alt="{html_escape(cover_alt)}" {loading} decoding="async">
      </div>
      <div class="wk-case-body">
        <p class="wk-kicker">{html_escape(kicker)}</p>
        <h2>{html_escape(name)}</h2>
        <p>{html_escape(description)}</p>
        <div class="wk-tags"><span>{html_escape(deliverable)}</span><span>{html_escape(project['domain'])}</span></div>
        <div class="wk-case-actions">
          <a href="{html_escape(project['url'])}" class="btn btn-primary" target="_blank" rel="noopener">{website_label} <span class="btn-arrow">↗</span></a>
          <a href="{html_escape(case_path)}" class="btn btn-ghost">{view_case} ↗</a>
        </div>
      </div>
    </article>''')
    section = f'''  <section class="wk-cases" id="projects">
    <header class="section-head reveal">
      <p class="section-kicker">{section_kicker}</p>
      <h2>{heading}</h2>
      <p class="section-sub">{section_sub}</p>
    </header>
    <div class="wk-filter" role="group" aria-label="{filter_aria}">
      <button class="wk-filter-btn active" data-filter="all">{all_label}</button>
      <button class="wk-filter-btn" data-filter="estiasi">🍽 {hospitality_label}</button>
      <button class="wk-filter-btn" data-filter="tourismos">✈️ {tourism_label}</button>
    </div>
{chr(10).join(cards)}
  </section>'''
    pattern = r'  <section class="wk-cases" id="projects">.*?  </section>(?=\s*<!-- (?:WHAT WE BUILD|ΤΙ ΦΤΙΑΧΝΟΥΜΕ) -->)'
    source, count = re.subn(pattern, lambda _: section, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError("Could not locate the archived portfolio section")

    # Keep the legacy collection metadata consistent with the visible project list.
    def update_schema(match):
        try:
            graph = json.loads(match.group(1))
        except json.JSONDecodeError:
            return match.group(0)
        nodes = graph.get("@graph", [])
        item_list = next((node for node in nodes if node.get("@type") == "ItemList"), None)
        if not item_list:
            return match.group(0)
        item_list["numberOfItems"] = len(projects)
        item_list["itemListElement"] = [
            {
                "@type": "ListItem",
                "position": index,
                "item": {
                    "@type": "CreativeWork",
                    "name": project["name"] + " — " + project["domain"],
                    "url": project["url"],
                    "image": "https://codehouse.gr/" + project.get("cover", project["desktop"]),
                    "description": project["description"][lang],
                    "creator": {"@id": "https://codehouse.gr/#business"},
                    "genre": project["deliverable"][lang],
                },
            }
            for index, project in enumerate(projects, 1)
        ]
        return '<script type="application/ld+json">\n' + json.dumps(graph, ensure_ascii=False, indent=2) + '\n</script>'

    source = re.sub(
        r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>',
        update_schema, source, count=1, flags=re.S,
    )
    first_cover = "/" + projects[0].get("cover", projects[0]["desktop"])
    source = re.sub(
        r'(<meta property="og:image" content=")[^"]+(")',
        rf'\g<1>https://codehouse.gr{first_cover}\2', source, count=1,
    )
    source = re.sub(
        r'(<meta name="twitter:image" content=")[^"]+(")',
        rf'\g<1>https://codehouse.gr{first_cover}\2', source, count=1,
    )
    source = re.sub(
        r'(<link rel="preload" as="image" href=")[^"]+(" fetchpriority="high")',
        rf'\g<1>{first_cover}\2', source, count=1,
    )
    return source


def html_escape(value):
    return (
        str(value).replace("&", "&amp;").replace("<", "&lt;")
        .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")
    )


def refresh(path):
    original = path.read_text(encoding="utf-8")
    source = original
    source = refresh_legacy_portfolio(path, source)
    updated = wrap_tables(source, path)
    updated = update_body_class(updated)
    updated, main_target = update_main_target(updated)
    updated = update_header(updated, path, main_target)
    updated = update_footer(updated, path)
    updated = rewrite_existing_shell_links(updated)
    updated = add_assets(updated)
    updated = unify_privacy(updated)
    if updated != original:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main():
    paths = sorted(
        path
        for root in LEGACY_ROOTS
        for route in (root, f"en/{root}")
        for path in (ROOT / route).rglob("*.html")
        if path.is_file()
    )
    changed = []
    for path in paths:
        try:
            if refresh(path):
                changed.append(path.relative_to(ROOT).as_posix())
        except (OSError, ValueError) as error:
            raise SystemExit(f"Could not refresh {path.relative_to(ROOT)}: {error}")
    print(f"Scanned {len(paths)} legacy HTML files; refreshed {len(changed)}.")
    for path in changed:
        print(path)


if __name__ == "__main__":
    main()