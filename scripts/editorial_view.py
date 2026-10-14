"""Server-side HTML rendering for Codehouse's Greek editorial articles."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


_SITE = "https://codehouse.gr"
_MONTHS_EL = (
    "Ιανουαρίου",
    "Φεβρουαρίου",
    "Μαρτίου",
    "Απριλίου",
    "Μαΐου",
    "Ιουνίου",
    "Ιουλίου",
    "Αυγούστου",
    "Σεπτεμβρίου",
    "Οκτωβρίου",
    "Νοεμβρίου",
    "Δεκεμβρίου",
)


def _text(value: object) -> str:
    """Escape content destined for an HTML text or attribute context."""
    return html.escape(str(value or ""), quote=True)


def _safe_link(value: object) -> str:
    """Allow site-root paths and web URLs; never emit executable URL schemes."""
    raw = str(value or "").strip()
    parts = urlsplit(raw)
    if raw.startswith("/") and not raw.startswith("//"):
        return _text(raw)
    if parts.scheme.lower() in {"http", "https"} and parts.netloc:
        return _text(raw)
    return "#"


def _json_ld(data: dict) -> str:
    # Script elements terminate on a literal '<', including inside JSON strings.
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    return f'<script type="application/ld+json">{encoded}</script>'


def _contact_form() -> str:
    # Keep field names and data attributes aligned with studio.js and lead.php.
    return """
      <form class="contact-form editorial-contact-form" action="/lead.php" method="post" data-contact-form data-locale="el">
        <input type="hidden" name="_form" value="studio">
        <input class="visually-hidden" tabindex="-1" autocomplete="off" name="website" aria-hidden="true">
        <div class="field"><label for="editorial-name">Όνομα *</label><input id="editorial-name" name="name" autocomplete="name" required></div>
        <div class="field"><label for="editorial-company">Εταιρεία</label><input id="editorial-company" name="company" autocomplete="organization"></div>
        <div class="field full"><label for="editorial-email">Email *</label><input id="editorial-email" name="email" type="email" autocomplete="email" required></div>
        <div class="field full"><label for="editorial-service">Είδος υπηρεσίας *</label>
          <select id="editorial-service" name="service" required>
            <option value="">Επίλεξε υπηρεσία</option><option value="web">Σχεδιασμός &amp; ανάπτυξη ιστοσελίδων</option>
            <option value="ecommerce">E-commerce</option><option value="apps">Custom εφαρμογές &amp; software</option>
            <option value="seo">SEO / GEO · μηνιαία ανάπτυξη ιστοσελίδας</option>
            <option value="ai">AI &amp; αυτοματισμοί</option><option value="booking">Συστήματα κρατήσεων</option>
            <option value="branding">Branding &amp; digital marketing</option>
          </select>
        </div>
        <div class="field full"><label for="editorial-description">Περιγραφή project *</label><textarea id="editorial-description" name="description" minlength="10" required></textarea></div>
        <div class="field full"><label for="editorial-budget">Εύρος budget (προαιρετικό)</label>
          <select id="editorial-budget" name="budget"><option value=""></option><option>Δεν έχω ορίσει ακόμη</option>
            <option>Έως €2.500</option><option>€2.500–€5.000</option><option>€5.000–€10.000</option><option>€10.000+</option>
          </select>
        </div>
        <button class="form-submit" type="submit">ΑΠΟΣΤΟΛΗ ΜΗΝΥΜΑΤΟΣ ↗</button>
        <p class="form-status" aria-live="polite"></p>
      </form>
    """


def _article_main(document: dict, published: datetime, canonical: str) -> str:
    title = _text(document["title"])
    description = _text(document["description"])
    category = _text(document.get("category", ""))
    answer = _text(document["answer"])
    month = _MONTHS_EL[published.month - 1]
    date_label = f"{published.day} {month} {published.year}"

    sections = document.get("sections") or []
    toc = [
        f'<li><a href="#section-{index}">{_text(section["heading"])}</a></li>'
        for index, section in enumerate(sections, start=1)
    ]
    section_markup: list[str] = []
    for index, section in enumerate(sections, start=1):
        paragraphs = "".join(f"<p>{_text(paragraph)}</p>" for paragraph in section.get("paragraphs", []))
        bullets = section.get("bullets") or []
        list_markup = ""
        if bullets:
            list_markup = "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in bullets) + "</ul>"
        section_markup.append(
            f'<section class="editorial-section" id="section-{index}" aria-labelledby="section-heading-{index}">'
            f'<h2 id="section-heading-{index}">{_text(section["heading"])}</h2>{paragraphs}{list_markup}</section>'
        )

    faq = document.get("faq") or []
    faq_markup = ""
    if faq:
        toc.append('<li><a href="#article-faq">Συχνές ερωτήσεις</a></li>')
        faq_markup = (
            '<section class="editorial-section editorial-faq" id="article-faq" aria-labelledby="faq-heading">'
            '<p class="eyebrow">ΣΥΧΝΕΣ ΕΡΩΤΗΣΕΙΣ</p><h2 id="faq-heading">Όσα αξίζει να γνωρίζεις</h2>'
            '<div class="faq-list">'
            + "".join(
                f'<details><summary>{_text(item["question"])}</summary><p>{_text(item["answer"])}</p></details>'
                for item in faq
            )
            + "</div></section>"
        )

    sources = document.get("sources") or []
    sources_markup = ""
    if sources:
        toc.append('<li><a href="#article-sources">Πηγές</a></li>')
        sources_markup = (
            '<section class="editorial-section editorial-sources" id="article-sources" aria-labelledby="sources-heading">'
            '<p class="eyebrow">ΤΕΚΜΗΡΙΩΣΗ</p><h2 id="sources-heading">Πηγές</h2><ol>'
            + "".join(
                f'<li><a href="{_safe_link(item["url"])}" target="_blank" rel="noopener noreferrer">'
                f'{_text(item["name"])}<span class="editorial-external" aria-hidden="true"> ↗</span>'
                f'<span class="visually-hidden"> (ανοίγει σε νέα καρτέλα)</span></a></li>'
                for item in sources
            )
            + "</ol></section>"
        )

    related = document.get("related") or []
    related_markup = ""
    if related:
        related_markup = (
            '<section class="editorial-related" aria-labelledby="related-heading"><p class="eyebrow">ΣΥΝΕΧΙΣΕ ΤΗΝ ΑΝΑΓΝΩΣΗ</p>'
            '<h2 id="related-heading">Σχετικά άρθρα</h2><ul>'
            + "".join(
                f'<li><a href="{_safe_link(item["url"])}">{_text(item["title"])}<span aria-hidden="true"> ↗</span></a></li>'
                for item in related
            )
            + "</ul></section>"
        )

    return f"""
      <div class="editorial-wrap">
        <nav class="editorial-breadcrumbs" aria-label="Διαδρομή">
          <a href="/">Αρχική</a><span aria-hidden="true">/</span><a href="/blog/">Blog</a><span aria-hidden="true">/</span><span aria-current="page">{title}</span>
        </nav>
        <article class="editorial-article" itemscope itemtype="https://schema.org/BlogPosting">
          <header class="editorial-header">
            <p class="eyebrow editorial-category">{category}</p>
            <h1 itemprop="headline">{title}</h1>
            <p class="editorial-deck" itemprop="description">{description}</p>
            <div class="editorial-byline">
              <span>CODEHOUSE EDITORIAL TEAM</span><span aria-hidden="true">·</span>
              <time itemprop="datePublished" datetime="{_text(published.isoformat())}">{date_label}</time>
            </div>
          </header>
          <div class="editorial-grid">
            <aside class="editorial-aside">
              <nav class="editorial-toc" aria-label="Περιεχόμενα άρθρου">
                <p class="eyebrow">ΣΕ ΑΥΤΟ ΤΟ ΑΡΘΡΟ</p><ol>{"".join(toc)}</ol>
              </nav>
            </aside>
            <div class="editorial-body" itemprop="articleBody">
              <section class="editorial-answer" aria-labelledby="answer-heading">
                <p class="eyebrow">Η ΣΥΝΤΟΜΗ ΑΠΑΝΤΗΣΗ</p><h2 id="answer-heading">Με μια ματιά</h2><p>{answer}</p>
              </section>
              {"".join(section_markup)}
              {faq_markup}
              {sources_markup}
              {related_markup}
            </div>
          </div>
        </article>
        <section class="editorial-contact" aria-labelledby="editorial-contact-heading">
          <div class="editorial-contact-intro"><p class="eyebrow">ΜΙΑ ΙΔΕΑ ΣΕ ΕΞΕΛΙΞΗ;</p>
            <h2 id="editorial-contact-heading">Ας συζητήσουμε το επόμενο βήμα.</h2>
            <p>Πες μας τι θέλεις να φτιάξεις. Θα επιστρέψουμε με μια καθαρή πρόταση για το πώς μπορούμε να βοηθήσουμε.</p>
            <a href="mailto:hello@codehouse.gr">hello@codehouse.gr</a>
          </div>
          <div class="editorial-form-wrap"><h3>Στείλε μας λίγες λεπτομέρειες</h3>{_contact_form()}
            <p class="editorial-privacy-note">Με την αποστολή συμφωνείς με την <a href="/aporrito/">πολιτική απορρήτου</a>.</p>
          </div>
        </section>
      </div>
    """


def render_article(document: dict, published_at: str, root: Path) -> str:
    """Render one Greek article within the real Codehouse contact-page shell."""
    parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("published_at must include a timezone")

    slug = str(document["slug"]).strip("/")
    if not slug or "/" in slug or slug in {".", ".."}:
        raise ValueError("slug must be a single non-empty URL segment")
    canonical = f"{_SITE}/blog/{slug}/"
    description = _text(document["description"])
    title = _text(document["title"])

    shell_path = Path(root) / "contact" / "index.html"
    shell = shell_path.read_text(encoding="utf-8")
    head_match = re.search(r"<head>(.*?)</head>", shell, flags=re.DOTALL | re.IGNORECASE)
    if not head_match:
        raise ValueError(f"Contact shell has no head element: {shell_path}")
    head = head_match.group(1)
    # Preserve the real shell's styles, scripts, icon, and business identity data.
    head = re.sub(r"<title>.*?</title>", "", head, flags=re.DOTALL | re.IGNORECASE)
    head = re.sub(r'<meta\s+name="description"[^>]*>', "", head, flags=re.IGNORECASE)
    head = re.sub(r'<link\s+rel="canonical"[^>]*>', "", head, flags=re.IGNORECASE)
    head = re.sub(r'<meta\s+property="og:[^"]+"[^>]*>', "", head, flags=re.IGNORECASE)
    head = re.sub(r'<link\s+rel="alternate"\s+hreflang="[^"]+"\s+href="[^"]+"\s*>', "", head, flags=re.IGNORECASE)
    head = head.replace("../assets/", "/assets/")
    head = re.sub(r'<script type="application/ld\+json">\{"@context":"https://schema.org","@type":"ProfessionalService".*?</script>', "", head, flags=re.DOTALL)

    published_iso = parsed.isoformat()
    publisher_logo = f"{_SITE}/assets/studio/logo-wordmark-black.svg"
    blog_posting = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "headline": str(document["title"]),
        "description": str(document["description"]),
        "inLanguage": "el-GR",
        "datePublished": published_iso,
        "author": {"@type": "Organization", "name": "Codehouse editorial team", "url": f"{_SITE}/"},
        "publisher": {
            "@type": "Organization",
            "name": "Codehouse",
            "url": f"{_SITE}/",
            "logo": {"@type": "ImageObject", "url": publisher_logo},
        },
        "articleSection": str(document.get("category", "")),
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Αρχική", "item": f"{_SITE}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{_SITE}/blog/"},
            {"@type": "ListItem", "position": 3, "name": str(document["title"]), "item": canonical},
        ],
    }
    metadata = (
        f"<title>{title} · Codehouse</title><meta name=\"description\" content=\"{description}\">"
        f'<link rel="canonical" href="{_text(canonical)}">'
        '<meta property="og:type" content="article"><meta property="og:locale" content="el_GR">'
        f'<meta property="og:title" content="{title} · Codehouse"><meta property="og:description" content="{description}">'
        f'<meta property="og:url" content="{_text(canonical)}"><meta property="og:image" content="{_SITE}/assets/studio/images/codehouse-desktop.webp">'
        f'<meta property="og:site_name" content="Codehouse"><meta property="article:published_time" content="{_text(published_iso)}">'
        f'<link rel="stylesheet" href="/assets/studio/editorial.css">'
        f"{_json_ld(blog_posting)}{_json_ld(breadcrumb)}"
    )
    head = metadata + head
    shell = shell[: head_match.start(1)] + head + shell[head_match.end(1) :]

    shell = shell.replace("../assets/", "/assets/")
    shell = re.sub(
        r'(<span class="language">)\s*<a class="active" href="[^"]*">GR</a>\s*<a class="" href="[^"]*">EN</a>\s*</span>',
        rf'\1<a class="active" href="/blog/{_text(slug)}/" aria-current="page">GR</a><a href="/en/blog/">EN</a></span>',
        shell,
        count=1,
    )
    shell = re.sub(
        r'(<span class="menu-lang">)\s*<a href="[^"]*">GR</a>\s*<a href="[^"]*">EN</a>\s*</span>',
        rf'\1<a href="/blog/{_text(slug)}/" aria-current="page">GR</a><a href="/en/blog/">EN</a></span>',
        shell,
        count=1,
    )
    main = _article_main(document, parsed, canonical)
    shell = re.sub(
        r"<main id=\"main-content\">.*?</main>",
        lambda _match: f'<main id="main-content">{main}</main>',
        shell,
        count=1,
        flags=re.DOTALL,
    )
    return shell
