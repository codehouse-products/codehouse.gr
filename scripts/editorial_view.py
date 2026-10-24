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


def _rich_text(value: object) -> str:
    """Escape prose while supporting explicit, safe [[label|/internal-path]] links."""
    raw = str(value or "")
    token = re.compile(r"\[\[([^\]|]+)\|([^\]]+)\]\]")
    pieces: list[str] = []
    cursor = 0
    for match in token.finditer(raw):
        pieces.append(_text(raw[cursor:match.start()]))
        pieces.append(
            f'<a href="{_safe_link(match.group(2))}">{_text(match.group(1))}</a>'
        )
        cursor = match.end()
    pieces.append(_text(raw[cursor:]))
    return "".join(pieces)


def _json_ld(data: dict) -> str:
    # Script elements terminate on a literal '<', including inside JSON strings.
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("<", r"\u003c").replace(">", r"\u003e").replace("&", r"\u0026")
    return f'<script type="application/ld+json">{encoded}</script>'


def _contact_form(locale: str = "el", *, include_budget: bool = True) -> str:
    # Keep field names and data attributes aligned with studio.js and lead.php.
    english = locale == "en"
    labels = {
        "name": "Name" if english else "Όνομα",
        "company": "Company" if english else "Εταιρεία",
        "service": "Service" if english else "Είδος υπηρεσίας",
        "choose": "Choose a service" if english else "Επίλεξε υπηρεσία",
        "description": "Project description" if english else "Περιγραφή project",
        "budget": "Budget range (optional)" if english else "Εύρος budget (προαιρετικό)",
        "not_set": "Not decided yet" if english else "Δεν έχω ορίσει ακόμη",
        "submit": "SEND MESSAGE ↗" if english else "ΑΠΟΣΤΟΛΗ ΜΗΝΥΜΑΤΟΣ ↗",
    }
    service_options = (
        '<option value="web">Website design &amp; development</option>'
        '<option value="ecommerce">E-commerce</option>'
        '<option value="apps">Custom apps &amp; software</option>'
        '<option value="seo">SEO / GEO · ongoing website growth</option>'
        '<option value="ai">AI &amp; automation</option>'
        '<option value="booking">Booking systems</option>'
        '<option value="branding">Branding &amp; digital marketing</option>'
        if english else
        '<option value="web">Σχεδιασμός &amp; ανάπτυξη ιστοσελίδων</option>'
        '<option value="ecommerce">E-commerce</option>'
        '<option value="apps">Custom εφαρμογές &amp; software</option>'
        '<option value="seo">SEO / GEO · μηνιαία ανάπτυξη ιστοσελίδας</option>'
        '<option value="ai">AI &amp; αυτοματισμοί</option>'
        '<option value="booking">Συστήματα κρατήσεων</option>'
        '<option value="branding">Branding &amp; digital marketing</option>'
    )
    budget = ""
    if include_budget:
        budget_options = (
            '<option>Not decided yet</option><option>Up to €2,500</option>'
            '<option>€2,500–€5,000</option><option>€5,000–€10,000</option><option>€10,000+</option>'
            if english else
            '<option>Έως €2.500</option><option>€2.500–€5.000</option>'
            '<option>€5.000–€10.000</option><option>€10.000+</option>'
        )
        budget = (
            f'<div class="field full"><label for="editorial-budget">{labels["budget"]}</label>'
            f'<select id="editorial-budget" name="budget"><option value=""></option>'
            f'<option>{labels["not_set"]}</option>{budget_options}</select></div>'
        )
    return f"""
      <form class="contact-form editorial-contact-form" action="/lead.php" method="post" data-contact-form data-locale="{locale}">
        <input type="hidden" name="_form" value="studio">
        <input class="visually-hidden" tabindex="-1" autocomplete="off" name="website" aria-hidden="true">
        <div class="field"><label for="editorial-name">{labels["name"]} *</label><input id="editorial-name" name="name" autocomplete="name" required></div>
        <div class="field"><label for="editorial-company">{labels["company"]}</label><input id="editorial-company" name="company" autocomplete="organization"></div>
        <div class="field full"><label for="editorial-email">Email *</label><input id="editorial-email" name="email" type="email" autocomplete="email" required></div>
        <div class="field full"><label for="editorial-service">{labels["service"]} *</label>
          <select id="editorial-service" name="service" required>
            <option value="">{labels["choose"]}</option>{service_options}
          </select>
        </div>
        <div class="field full"><label for="editorial-description">{labels["description"]} *</label><textarea id="editorial-description" name="description" minlength="10" required></textarea></div>
        {budget}
        <button class="form-submit" type="submit">{labels["submit"]}</button>
        <p class="form-status" aria-live="polite"></p>
      </form>
    """


_UI = {
    "el": {
        "home": "Αρχική", "blog": "Blog", "crumb": "Διαδρομή",
        "toc": "Περιεχόμενα άρθρου", "in_article": "ΣΕ ΑΥΤΟ ΤΟ ΑΡΘΡΟ",
        "answer_label": "Η ΣΥΝΤΟΜΗ ΑΠΑΝΤΗΣΗ", "answer": "Με μια ματιά",
        "faq_label": "ΣΥΧΝΕΣ ΕΡΩΤΗΣΕΙΣ", "faq": "Συχνές ερωτήσεις",
        "faq_title": "Όσα αξίζει να γνωρίζεις", "sources_label": "ΤΕΚΜΗΡΙΩΣΗ",
        "sources": "Πηγές", "new_tab": "(ανοίγει σε νέα καρτέλα)",
        "related_label": "ΣΥΝΕΧΙΣΕ ΤΗΝ ΑΝΑΓΝΩΣΗ", "related": "Σχετικά άρθρα",
        "service_label": "ΣΧΕΤΙΚΗ ΥΠΗΡΕΣΙΑ",
        "idea": "ΜΙΑ ΙΔΕΑ ΣΕ ΕΞΕΛΙΞΗ?", "contact_title": "Ας συζητήσουμε το επόμενο βήμα.",
        "contact_body": "Πες μας τι θέλεις να φτιάξεις. Θα επιστρέψουμε με μια καθαρή πρόταση για το πώς μπορούμε να βοηθήσουμε.",
        "email": "hello@codehouse.gr", "form_title": "Στείλε μας λίγες λεπτομέρειες",
        "privacy": "Με την αποστολή συμφωνείς με την", "privacy_link": "πολιτική απορρήτου",
    },
    "en": {
        "home": "Home", "blog": "Blog", "crumb": "Breadcrumb",
        "toc": "Article contents", "in_article": "IN THIS ARTICLE",
        "answer_label": "THE SHORT ANSWER", "answer": "In short",
        "faq_label": "FREQUENTLY ASKED QUESTIONS", "faq": "FAQs",
        "faq_title": "What you need to know", "sources_label": "SOURCES",
        "sources": "Sources", "new_tab": "(opens in a new tab)",
        "related_label": "KEEP READING", "related": "Related articles",
        "service_label": "RELATED SERVICE",
        "idea": "HAVE A PROJECT IN MIND?", "contact_title": "Let’s discuss the next step.",
        "contact_body": "Tell us what you want to build. We’ll come back with a clear proposal for how we can help.",
        "email": "hello@codehouse.gr", "form_title": "Share a few details",
        "privacy": "By submitting, you agree to our", "privacy_link": "privacy policy",
    },
}


def _article_main(document: dict, published: datetime, canonical: str, locale: str = "el") -> str:
    title = _text(document["title"])
    description = _text(document["description"])
    category = _text(document.get("category", ""))
    answer = _text(document["answer"])
    ui = _UI[locale]
    if locale == "en":
        month = published.strftime("%B")
        date_label = f"{published.day} {month} {published.year}"
    else:
        month = _MONTHS_EL[published.month - 1]
        date_label = f"{published.day} {month} {published.year}"
    author_name = _text(document.get("author_name", "Codehouse editorial team"))

    sections = document.get("sections") or []
    toc = [
        f'<li><a href="#section-{index}">{_text(section["heading"])}</a></li>'
        for index, section in enumerate(sections, start=1)
    ]
    section_markup: list[str] = []
    for index, section in enumerate(sections, start=1):
        paragraphs = "".join(f"<p>{_rich_text(paragraph)}</p>" for paragraph in section.get("paragraphs", []))
        bullets = section.get("bullets") or []
        list_markup = ""
        if bullets:
            list_markup = "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in bullets) + "</ul>"
        steps = section.get("steps") or []
        if steps:
            list_markup += '<ol class="editorial-steps">' + "".join(
                f"<li>{_text(item)}</li>" for item in steps
            ) + "</ol>"
        section_markup.append(
            f'<section class="editorial-section" id="section-{index}" aria-labelledby="section-heading-{index}">'
            f'<h2 id="section-heading-{index}">{_text(section["heading"])}</h2>{paragraphs}{list_markup}</section>'
        )

    faq = document.get("faq") or []
    faq_markup = ""
    if faq:
        toc.append(f'<li><a href="#article-faq">{_text(ui["faq"])}</a></li>')
        faq_markup = (
            '<section class="editorial-section editorial-faq" id="article-faq" aria-labelledby="faq-heading">'
            f'<p class="eyebrow">{_text(ui["faq_label"])}</p><h2 id="faq-heading">{_text(ui["faq_title"])}</h2>'
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
        toc.append(f'<li><a href="#article-sources">{_text(ui["sources"])}</a></li>')
        sources_markup = (
            '<section class="editorial-section editorial-sources" id="article-sources" aria-labelledby="sources-heading">'
            f'<p class="eyebrow">{_text(ui["sources_label"])}</p><h2 id="sources-heading">{_text(ui["sources"])}</h2><ol>'
            + "".join(
                f'<li><a href="{_safe_link(item["url"])}" target="_blank" rel="noopener noreferrer">'
                f'{_text(item["name"])}<span class="editorial-external" aria-hidden="true"> ↗</span>'
                f'<span class="visually-hidden"> {_text(ui["new_tab"])}</span></a></li>'
                for item in sources
            )
            + "</ol></section>"
        )

    related = document.get("related") or []
    related_markup = ""
    if related:
        related_markup = (
            f'<section class="editorial-related" aria-labelledby="related-heading"><p class="eyebrow">{_text(ui["related_label"])}</p>'
            f'<h2 id="related-heading">{_text(ui["related"])}</h2><ul>'
            + "".join(
                f'<li><a href="{_safe_link(item["url"])}">{_text(item["title"])}<span aria-hidden="true"> ↗</span></a></li>'
                for item in related
            )
            + "</ul></section>"
        )

    service_target = document.get("service_target")
    service_markup = ""
    if service_target:
        service_markup = (
            f'<aside class="editorial-service-target"><p class="eyebrow">{_text(ui["service_label"])}</p>'
            f'<a href="{_safe_link(service_target["url"])}">{_text(service_target["label"])}'
            '<span aria-hidden="true"> ↗</span></a></aside>'
        )
    contact_cta = document.get("contact_cta")
    contact_cta_markup = ""
    if contact_cta:
        contact_cta_markup = (
            f'<a class="editorial-contact-cta" href="{_safe_link(contact_cta["url"])}">'
            f'{_text(contact_cta["label"])}<span aria-hidden="true"> ↗</span></a>'
        )
    prefix = "/en" if locale == "en" else ""

    return f"""
      <div class="editorial-wrap">
        <nav class="editorial-breadcrumbs" aria-label="{_text(ui["crumb"])}">
          <a href="{prefix}/">{_text(ui["home"])}</a><span aria-hidden="true">/</span><a href="{prefix}/blog/">{_text(ui["blog"])}</a><span aria-hidden="true">/</span><span aria-current="page">{title}</span>
        </nav>
        <article class="editorial-article" itemscope itemtype="https://schema.org/BlogPosting">
          <header class="editorial-header">
            <p class="eyebrow editorial-category">{category}</p>
            <h1 itemprop="headline">{title}</h1>
            <p class="editorial-deck" itemprop="description">{description}</p>
            <div class="editorial-byline">
              <span>{author_name}</span><span aria-hidden="true">·</span>
              <time itemprop="datePublished" datetime="{_text(published.isoformat())}">{date_label}</time>
            </div>
          </header>
          <div class="editorial-grid">
            <aside class="editorial-aside">
              <nav class="editorial-toc" aria-label="{_text(ui["toc"])}">
                <p class="eyebrow">{_text(ui["in_article"])}</p><ol>{"".join(toc)}</ol>
              </nav>
            </aside>
            <div class="editorial-body" itemprop="articleBody">
              <section class="editorial-answer" aria-labelledby="answer-heading">
                <p class="eyebrow">{_text(ui["answer_label"])}</p><h2 id="answer-heading">{_text(ui["answer"])}</h2><p>{answer}</p>
              </section>
              {service_markup}
              {"".join(section_markup)}
              {faq_markup}
              {sources_markup}
              {related_markup}
            </div>
          </div>
        </article>
        <section class="editorial-contact" aria-labelledby="editorial-contact-heading">
          <div class="editorial-contact-intro"><p class="eyebrow">{_text(ui["idea"])}</p>
            <h2 id="editorial-contact-heading">{_text(ui["contact_title"])}</h2>
            <p>{_text(ui["contact_body"])}</p>
            {contact_cta_markup}
            <a href="mailto:hello@codehouse.gr">{_text(ui["email"])}</a>
          </div>
          <div class="editorial-form-wrap"><h3>{_text(ui["form_title"])}</h3>{_contact_form(locale, include_budget=bool(document.get("include_budget", True)))}
            <p class="editorial-privacy-note">{_text(ui["privacy"])} <a href="{prefix}/aporrito/">{_text(ui["privacy_link"])}</a>.</p>
          </div>
        </section>
      </div>
    """


def render_article(
    document: dict,
    published_at: str,
    root: Path,
    *,
    locale: str | None = None,
    alternate_url: str | None = None,
) -> str:
    """Render one editorial article within the matching Codehouse contact shell."""
    parsed = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("published_at must include a timezone")

    slug = str(document["slug"]).strip("/")
    if not slug or "/" in slug or slug in {".", ".."}:
        raise ValueError("slug must be a single non-empty URL segment")
    locale = locale or document.get("locale", "el")
    if locale not in {"el", "en"}:
        raise ValueError("locale must be el or en")
    prefix = "/en" if locale == "en" else ""
    canonical = f"{_SITE}{prefix}/blog/{slug}/"
    description = _text(document["description"])
    title = _text(document["title"])

    shell_path = Path(root) / prefix.lstrip("/") / "contact" / "index.html"
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
    head = re.sub(r"(?:\.\./)+assets/", "/assets/", head)
    head = re.sub(r'<script type="application/ld\+json">\{"@context":"https://schema.org","@type":"ProfessionalService".*?</script>', "", head, flags=re.DOTALL)

    published_iso = parsed.isoformat()
    modified = str(document.get("dateModified") or parsed.date().isoformat())
    try:
        datetime.fromisoformat(modified.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("dateModified must be an ISO date or datetime") from exc
    publisher_logo = f"{_SITE}/assets/studio/logo-wordmark-black.svg"
    author_name = str(document.get("author_name") or "Codehouse editorial team")
    schema_type = str(document.get("schema_type") or "BlogPosting")
    if schema_type not in {"Article", "BlogPosting"}:
        raise ValueError("schema_type must be Article or BlogPosting")
    author = (
        {"@type": "Person", "name": author_name}
        if document.get("author_name")
        else {"@type": "Organization", "name": author_name, "url": f"{_SITE}/"}
    )
    blog_posting = {
        "@context": "https://schema.org",
        "@type": schema_type,
        "mainEntityOfPage": {"@type": "WebPage", "@id": canonical},
        "headline": str(document["title"]),
        "description": str(document["description"]),
        "inLanguage": "en" if locale == "en" else "el-GR",
        "datePublished": published_iso,
        "dateModified": modified,
        "author": author,
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
            {"@type": "ListItem", "position": 1, "name": "Home" if locale == "en" else "Αρχική", "item": f"{_SITE}{prefix}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{_SITE}{prefix}/blog/"},
            {"@type": "ListItem", "position": 3, "name": str(document["title"]), "item": canonical},
        ],
    }
    faq = document.get("faq") or []
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": str(item["question"]),
                "acceptedAnswer": {"@type": "Answer", "text": str(item["answer"])},
            }
            for item in faq
        ],
    }
    alternates = ""
    if alternate_url:
        greek_url = canonical if locale == "el" else alternate_url
        english_url = canonical if locale == "en" else alternate_url
        alternates = (
            f'<link rel="alternate" hreflang="el" href="{_text(greek_url)}">'
            f'<link rel="alternate" hreflang="en" href="{_text(english_url)}">'
            f'<link rel="alternate" hreflang="x-default" href="{_text(greek_url)}">'
        )
    locale_tag = "en_US" if locale == "en" else "el_GR"
    metadata = (
        f"<title>{title} · Codehouse</title><meta name=\"description\" content=\"{description}\">"
        f'<link rel="canonical" href="{_text(canonical)}">'
        '<meta property="og:type" content="article">'
        f'<meta property="og:locale" content="{locale_tag}">'
        f'<meta property="og:title" content="{title} · Codehouse"><meta property="og:description" content="{description}">'
        f'<meta property="og:url" content="{_text(canonical)}"><meta property="og:image" content="{_SITE}/assets/studio/images/codehouse-desktop.webp">'
        f'<meta property="og:site_name" content="Codehouse"><meta property="article:published_time" content="{_text(published_iso)}">'
        f'<meta property="article:modified_time" content="{_text(modified)}">{alternates}'
        f'<link rel="stylesheet" href="/assets/studio/editorial.css">'
        f"{_json_ld(blog_posting)}{_json_ld(breadcrumb)}{_json_ld(faq_schema) if faq else ''}"
    )
    head = metadata + head
    shell = shell[: head_match.start(1)] + head + shell[head_match.end(1) :]

    shell = re.sub(r"(?:\.\./)+assets/", "/assets/", shell)
    if alternate_url:
        greek_path = f"/blog/{_text(slug)}/"
        english_path = f"/en/blog/{_text(slug)}/"
        greek_link = f'<a href="{greek_path}"' + (' class="active" aria-current="page"' if locale == "el" else "") + '>GR</a>'
        english_link = f'<a href="{english_path}"' + (' class="active" aria-current="page"' if locale == "en" else "") + '>EN</a>'
    else:
        # Preserve the existing queue's language switch until it has a
        # translated counterpart; bilingual batches pass alternate_url.
        greek_link = f'<a class="active" href="/blog/{_text(slug)}/" aria-current="page">GR</a>'
        english_link = '<a href="/en/blog/">EN</a>'
    for class_name in ("language", "menu-lang"):
        shell = re.sub(
            rf'(<span class="{class_name}">).*?</span>',
            lambda match: match.group(1) + greek_link + english_link + "</span>",
            shell,
            count=1,
            flags=re.DOTALL,
        )
    main = _article_main(document, parsed, canonical, locale)
    shell = re.sub(
        r"<main id=\"main-content\">.*?</main>",
        lambda _match: f'<main id="main-content">{main}</main>',
        shell,
        count=1,
        flags=re.DOTALL,
    )
    return shell
