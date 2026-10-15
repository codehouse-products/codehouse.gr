# One-time activation: reviewed Codehouse daily articles

The implementation and seven reviewed articles are prepared and checked.
The new scheduled workflow is **not installed or active yet**.

The GitHub connection can publish ordinary source files and dispatch the
existing controlled release. Its attempt to add a new workflow file was
rejected; the default branch and existing release workflow were not changed.
Do not put credentials in chat or add them to a repository file.

## First try refreshing GitHub authorization

Use the GitHub reconnect card. After reconnection, the agent can retry the
workflow write once and check whether the new authorization permits it.
Do not assume that a healthy ordinary repository connection proves workflow
write access. If refreshing does not resolve the rejection, use the owner step
below. These are alternatives, not steps to repeat for every article.

## Owner's fallback one-time step

1. Open `deployment/daily-editorial-workflow.yml` from this immutable setup
   snapshot and copy the complete file, without changing the pinned references.
2. In `codehouse-products/codehouse.gr`, create
   `.github/workflows/daily-editorial.yml` on **main** and save the copied file.
   Leave `.github/workflows/deploy.yml` unchanged.
3. Tell the agent the file is saved. The agent can then verify the installed
   bytes and dispatch the new workflow in **inspect** mode, without a real
   article/server write. A subsequent authorized apply checks the complete
   publication path. The first actual scheduled run still needs observation.

No new server secret is required. The existing `SERVER_HOST`, `SERVER_USER`
and `SERVER_SSH_KEY` Actions secrets are reused without exposing their values.
The explicit workflow `contents: write` permission is required only for
advancing the reviewed source and confirming a successful server publication.
If repository/organization policy forbids that permission, the owner must
adjust the existing Actions policy; the agent must not work around it with a
token in source code.

## What happens afterwards

- Target: 10:00 Europe/Athens, including daylight-saving changes.
- A 10:30 retry cannot publish a second article after today's successful apply.
- GitHub may delay or occasionally drop a scheduled run. This is not an
  exact-minute execution guarantee.
- A failed public apply leaves the article pending. It is retried before the
  next queue entry, including on a later day.
- Blog cards, actual descriptive URLs, canonical metadata and the sitemap are
  updated together. Each page includes the existing studio lead form.
- When seven confirmed articles have exhausted the series, publication stops.
  Warnings appear in Actions when two or fewer articles remain.
- Next content batches only change reviewed source documents and the queue;
  ordinary source updates do not require another workflow copy.
- The existing production admin, private lead history and trusted server
  release/rollback logic remain outside editorial changes.

## Fixed trust boundaries

Publisher/renderer: `0e241f00e9ddc757f2049d19d74a5fbfbd36c149`

Existing public release tools: `decbc1d46f76f56463f6c101b919edc04177c72e`

Current website input: the verified `releases/reviewed-public` reference,
resolved on each run; not historical website files on `main`.

The scheduled job shares `codehouse-server-maintenance` with normal releases,
does not force-push, does not write admin or workflows, and verifies the exact
allowed article diff before advancing the source reference.
