# Codehouse studio photo handoff

Missing photography slots remain intentionally blank, with their layout dimensions preserved and no fallback images or placeholder copy. HIGH HOPE now uses the supplied portrait in its separate cover field; its authentic desktop/mobile captures remain untouched. The central logo illustration uses a separate transparent artwork asset, not the background-photo field. Do not overwrite, crop over, rename, or replace any existing `*-desktop.webp` or `*-mobile.webp` project capture.

## Ten requested photographs

Original, cleared photography can be supplied as high-resolution JPG or PNG; convert to optimized sRGB WebP later. Keep the person, screen contents, proportions, and perspective authentic. Do not composite fabricated UI or present an editorial photo as a project screenshot. Recommended final WebP quality: 82–88.

| New file in `assets/studio/images/` | Count | Composition | Manifest mapping |
| --- | ---: | --- | --- |
| `hero-editorial.webp` | 1 | Wide 16:9 editorial studio photograph. Leave a quiet center area behind the wordmark and keep the important subject clear of the bottom captions. | `images.hero`; set `images.heroMode` to `photo` only after the file is present. |
| `services-web.webp` | 1 | Square 1:1 | `services[slug=web-design].image` |
| `services-ecommerce.webp` | 1 | Square 1:1 | `services[slug=e-commerce].image` |
| `services-apps.webp` | 1 | Square 1:1 | `services[slug=custom-apps].image` |
| `services-automation.webp` | 1 | Square 1:1 | `services[slug=ai-automations].image` |
| `services-booking.webp` | 1 | Square 1:1 | `services[slug=booking-systems].image` |
| `services-branding.webp` | 1 | Square 1:1 | `services[slug=branding].image` |
| `project-highhope.webp` | 1 | Portrait 2:3 cover | `projects[slug=high-hope].cover` |
| `project-kc-travel.webp` | 1 | Portrait 2:3 cover | `projects[slug=kc-travel].cover` |
| `project-codehouse.webp` | 1 | Portrait 2:3 cover | `projects[slug=codehouse].cover` |

The optional `studio-editorial.webp` can be supplied as an additional wide 16:9 image for future studio-page use; it is not part of the ten-image request or required by the current site.

## Current capture paths — preserve these

`highhope-desktop.webp`, `highhope-mobile.webp`, `kc-travel-desktop.webp`, `kc-travel-mobile.webp`, `codehouse-desktop.webp`, and `codehouse-mobile.webp` remain the authentic project screens. Unsupplied cover paths are explicitly empty; project detail desktop/mobile visuals continue to use the original captures even after a separate portrait cover is added.

Until each new image is present, keep its manifest path as an empty string (`""`). Do not point the manifest at planned-but-missing files or replace blank paths with screenshot fallbacks. Empty paths render a blank frame rather than a broken image. For the hero, set the image path and `heroMode` to `photo` together; photo mode switches to a clear, full-colour image treatment and white wordmark/captions.

After updating the appropriate `images.hero`, `images.heroMode`, `services[].image`, or `projects[].cover` values in `assets/studio/data.json`, rerun `python3 scripts/generate-studio.py`. The generator merges defaults without discarding saved manifest edits. Image conversion is a separate handoff step; the generator does not transform images.