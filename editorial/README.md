# Reviewed daily Codehouse articles

This is a finite reviewed Greek content queue, not an AI generation service.
The publication target is 10:00 Europe/Athens. GitHub schedules are best effort;
a second 10:30 run retries missed/failed publication without consuming another
article on an already confirmed day.

## Add the next series

1. Add original, checked JSON documents under `editorial/articles/`, matching the
   existing schema. Give each article a distinct informational intent and a new
   descriptive ASCII slug. Preserve the existing commercial keyword ownership.
2. Check every claim and primary source. Do not invent reviews, credentials,
   statistics, customer outcomes or ranking guarantees.
3. Add the new slugs to `editorial/queue.json` in publication order. Keep historical
   documents referenced by the ledger. Do not clear or manually mark the ledger
   published to make a failed deployment appear successful.
4. Run `python3 scripts/test_editorial_queue.py` and
   `python3 scripts/test_editorial_commit.py`, then promote the verified immutable
   source to `releases/reviewed-public` through the existing reviewed-release
   process. Content replenishment does not require replacing the scheduled
   workflow or its pinned renderer.

## State and safety

Preparation creates one pending article, its Blog card and sitemap entry.
The server's verified public apply must succeed before the separate, non-public
ledger acknowledgment marks the entry published. Retries reuse a pending entry,
including after a missed day; they cannot silently skip it.

The workflow updates only the reviewed release branch, never `main` or admin.
It packages the public allowlist through the existing separately pinned release
tools, with the shared maintenance lock and existing server rollback checks.
Drafts, the queue, ledger and implementation scripts are not public release
payloads. No daily API billing or extra secret is required for this model.

## Preview without consuming the queue

Run `python3 scripts/preview_editorial.py`, then open
`/generated-artifacts/editorial-preview/index.html` in the development preview.
This page is noindex and excluded from Git and release packaging. Run
`python3 scripts/test_editorial_browser.py` to check five screen widths and
synthetic intercepted lead responses; it never sends a real lead.

## Activation

The scheduled workflow must be installed as
`.github/workflows/daily-editorial.yml` on the repository's default branch.
The complete pinned candidate and one-time setup notes are in `deployment/`.
Until installation and a successful Actions check, preparation is not evidence
that unattended daily publication is active.
