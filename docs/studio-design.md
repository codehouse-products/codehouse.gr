# Codehouse studio redesign

## Visual direction

Editorial event / portfolio rail composition with a monochrome, art-directed digital studio mood. Large restrained Inter headings (the user’s chosen lawful Neue Haas alternative), tiny Chivo Mono labels, square markers, thin rules and small corner details. Palette: white paper `#fff`, near-black ink `#171715`, muted greys; color is confined to authentic website captures. The immediate hero keeps the supplied Codehouse screen only as a low-opacity, greyscale, blurred texture, with the original wordmark and corner-bracket frame above it. Service rail images are square; service sibling blur stays on images, never captions or links. Keyboard focus activates that same local behavior. Native touch is single-tap plus swipe. Reduced-motion preferences disable smooth transitions.

The supplied reference was inspected at the supplied desktop/mobile captures. Those observations informed the fixed header, centered immediate hero mark, bottom metadata, editorial two-column introduction, horizontal event-size service cards, smaller portfolio cards, mobile inset menu panel and local hover treatment. Reference transition timing was not measurable, so the site uses a considered approximation rather than claiming pixel-perfect recreation. The reference cursor-arrow change is approximated with animated inline arrows and native pointer; keyboard focus and touch remain first-class.

## Font substitution

No licensed Neue Haas Grotesk Text Pro files were supplied. Headings use Inter as the agreed lawful close sans alternative. Labels use Google Fonts Chivo Mono, with a system monospace fallback for Greek glyphs (`"Courier New", monospace`). The import is in `assets/studio/studio.css`.

## Files and routes

- `assets/studio/data.json`: central editable bilingual service, project, translation, image and contact manifest. The generator merges its defaults only to add missing schema keys, then reads the saved manifest for every regeneration; saved content edits are retained.
- `assets/studio/studio.css`, `refinements.css`, `studio.js`: self-contained new studio visual and interaction assets.
- `assets/studio/logo-*.svg`, `favicon.svg`: original text-independent outlined custom vector marks, black and white.
- `scripts/generate-studio.py`: generates 28 bilingual static routes (home, services index + six details, studio, contact, projects index + three case studies, English equivalents).
- Run `python3 scripts/generate-studio.py` from repository root after editing templates/data.

Every generated route includes self canonical, reciprocal `el`/`en` hreflang and x-default, Open Graph metadata, a descriptive title and description. The language links preserve the equivalent route. Existing legacy destinations remain linked; old routes/assets and the existing lead handler are not modified.

## Image integrity

All temporary portfolio visuals come from the provided local official desktop/mobile captures. There are no synthetic photographs, fake clients, altered site screenshots, placeholder-image services or fabricated performance claims. See `docs/studio-assets-needed.md` for exact photography handoff and replacement guidance. `assets/studio/data.json` keeps the six service objects independently addressable for the planned per-service imagery.

## Contact

The existing `/lead.php` supports `_form: "studio"`, required `name`, `email`, `service`, `description`, optional `company`, `budget`, and empty `website` honeypot. Its service allowlist matches the form. It returns mail success as `{ok:true,saved:true,mail:true}` and persisted-only as `{ok:true,saved:true,mail:false}` (HTTP 202). The client announces sent only for `mail:true`; persisted-only and failure are distinct, localized and do not clear entered details. No browser-side PII persistence or debug/analytics payload is used.