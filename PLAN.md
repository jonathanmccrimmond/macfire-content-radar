# MacFire Content Radar — Build Plan

Context document for AI agents and developers picking up this project.

## What this project does

Automated social content pipeline for MacFire Ltd (Scottish fire safety consultancy).
Monitors public regulation sources, drafts LinkedIn, Facebook and X posts, and (eventually)
hands approved posts to a Social Media Agent for scheduled autoposting. Human review
stays in the loop: the agent can only publish posts that have been approved in the
review calendar, and automatic posting is not enabled until Stage 3 is explicitly
switched on.

## Current state (as of 2026-06-26)

### Built

| File | What it does |
|---|---|
| `content/posts/*.md` | Hand-written and AI-generated draft posts in markdown with YAML frontmatter |
| `scripts/build_preview.py` | Builds `preview/index.html` — a live-reload preview of all drafts as social media cards |
| `scripts/validate_links.py` | Checks that all source URLs in posts are reachable |
| `scripts/generate_draft.py` | **Stage 1** — fetches source URLs, calls Gemini 2.5 Flash, classifies `intent` (sell/awareness), writes a new draft post (incl. a `card:` block) and renders the sell card image |
| `scripts/build_post_image.py` + `scripts/templates/post_card.html` | **Stage 1** — renders the minimal premium sell card (`content/images/<slug>.png`) from a post's `card:` photo + headline, screenshotted with headless Chromium. Real text, so spelling/branding are always correct. Awareness posts skip this and use the plain photo |
| `scripts/generate_card_photo.py` | **Stage 1** — generates a relevant, text-free background photo from the card's `image_idea`, records it as `card.photo`, and re-renders the card. Defaults to Pollinations with no API key; Gemini remains available via `CARD_IMAGE_PROVIDER=gemini` |
| `scripts/monitor_sources.py` | **Stage 2** — checks Scottish regulation sources for new items, triggers draft generation |
| `.github/workflows/generate-draft.yml` | **Stage 1** — manual `workflow_dispatch`; takes URL + notes, generates draft, commits back |
| `.github/workflows/monitor-sources.yml` | **Stage 2** — Monday cron; runs the monitor, auto-triggers drafts for anything new |
| `preview/index.html` (generated) | **Stage 2.5** — review calendar: rolling month grid, "Next approval" panel, Facebook/LinkedIn/X tabbed previews, Copy text, Approve/Decline |
| `preview/supabase.js` + `supabase-config.js` | **Stage 2.5** — Supabase wrapper that reads/writes post status from the static page |
| `supabase/schema.sql` | **Stage 2.5** — `post_status` table keyed by slug |
| `docs/seasonal-content-calendar.md` | 12-month seasonal plan, now fully drafted as evergreen posts |
| `scripts/requirements.txt` | Python deps: `google-genai`, `requests` |
| `prompts/social-draft-prompt.md` | Original prompt spec (superseded by the inline prompt in `generate_draft.py`) |

### Not yet built

- Publish pipeline (Stage 3 — starts as copy-paste, see below)

---

## Post format

Every file in `content/posts/` must follow this structure for `build_preview.py` to render it:

```markdown
---
title: "Post title"
date: YYYY-MM-DD
status: draft          # or: approved, published, declined
evergreen: true        # optional, mark seasonal posts that are reused annually
platforms:
  - linkedin
  - facebook
  - x
sources:               # omit for evergreen posts that have no live source
  - title: "Source name"
    published: YYYY-MM-DD
    url: "https://..."
---

## Angle

One sentence — why this matters for MacFire's audience.

## LinkedIn

Full post copy, ending with hashtags on their own line.

## Facebook

Shorter, slightly more conversational version.

## X

Short version within character limits.

## Notes

Review guidance for the human editor.
```

Filenames follow the pattern `YYYY-MM-DD-NN-slug.md` (NN = sequence number for the day).

`sources[].published` is required when the source page provides a publication date.
The preview uses it to flag stale material before approval. If the source is older
than six months, treat the post as needing an explicit freshness check or a rewrite
into evergreen context before publishing.

Posts marked `evergreen: true` are seasonal reminders (BBQs, fireworks, Christmas
shutdown, winter heaters, hospitality readiness, student lets / HMOs) written so
they can run every year with a light review. The 12-month plan and refresh rules
are in [docs/seasonal-content-calendar.md](docs/seasonal-content-calendar.md).
When reusing an evergreen post next year, copy it to a new filename with the new
date, re-read the copy, and approve as normal. Stage 3 autoposting will treat
`evergreen: true` as an explicit signal that an older approved post is still safe
to schedule, provided the reviewer has re-approved it for the current cycle.

---

## Post images (intent-based, premium)

Posts carry an `intent` and the image differs by it:

- `intent: awareness` (public-safety / goodwill: fireworks, BBQ, candles) — the
  image is the clean, text-free photo alone. The post's `image:` points straight
  at `content/images/<slug>-bg.jpg`; the caption carries the message.
- `intent: sell` (genuine B2B openings: care homes, HMOs, premises checks) — the
  same photo gets a minimal premium overlay: one short headline (with `*words*`
  in red), a red rule, the MacFire mark and the phone number. Rendered to
  `content/images/<slug>.png`.

Key rule: the image model is only ever asked for a text-free photo. No words are
baked into the picture (an earlier attempt did that and produced misspellings and
watermarks). All on-image text is real HTML rendered by headless Chromium, so
spelling and branding are always correct. The look is deliberately minimal, not
the older busy poster (kicker, bullets, service pills, CTA band).

`generate_draft.py` classifies each new post's `intent` (defaulting to
`awareness` when unsure), writes a `card` object into the frontmatter, and for
sell posts renders `content/images/<slug>.png`. `generate_card_photo.py` then
adds the free background photo and, for awareness posts, points `image:` straight
at it (no card). Example frontmatter:

```yaml
intent: sell
card:
  photo: "content/images/<slug>-bg.jpg"
  headline: "Summer comfort and *fire safety* can work together"   # *words* = red
  image_idea: "a bright, calm care home corridor with a fire door"
image: "content/images/<slug>.png"     # sell: rendered card; awareness: the -bg.jpg
```

Only `card.photo` and `card.headline` are used by the minimal renderer; the logo
and phone are template defaults. Older busy-poster fields (kicker, bullets,
services, cta) are ignored if present.

Render or re-render manually:

```bash
python3 scripts/build_post_image.py --all                      # all sell cards
python3 scripts/build_post_image.py --post content/posts/<file>.md
python3 scripts/build_post_image.py --demo                     # layout check
```

`render_png(card, out)` keeps its (card, out_path) signature, so
`generate_draft.py` and `generate_card_photo.py` call it unchanged.

### Relevant photography (the `image_idea` field)

Each card captures an `image_idea` (e.g. "a garden barbecue on a patio on a calm
summer evening"). `generate_card_photo.py` turns that into a photorealistic,
text-free background. The default provider is **Pollinations** because it is
free and does not need an API key; set `CARD_IMAGE_PROVIDER=gemini` to use
Gemini image generation instead. It stores the photo as `card.photo` and
re-renders the card. The photo is decoupled from copy generation so it can be
retried/tuned without regenerating the text. For sell cards a soft bottom
gradient (`.scrim` in the template) keeps the headline legible; awareness posts
use the photo with no overlay at all.

Both workflows install Chromium (`browser-actions/setup-chrome`), run
`generate_card_photo.py --all` after drafting, and commit `content/images/`.
Pollinations uses the public `image.pollinations.ai` endpoint and sends the
card's `image_idea` prompt to that service. To fill/refresh locally:

```bash
python3 scripts/generate_card_photo.py --all   # fill any card missing a photo
```

### Backfill status

All existing posts have been given a hand-authored `card:` block and a rendered
branded image. The first manual backfill run on 2026-06-26 failed before the API
call because the scanner included `content/posts/README.md`, which has no YAML
frontmatter. `generate_card_photo.py` now skips markdown files without
frontmatter, defaults to Pollinations for image generation, and keeps the Gemini
path available with explicit image output via `GenerateContentConfig`.

The prompt is tuned for calm, photorealistic, text-free subject photos with
empty centre space for the branded card overlay. The 2026-06-26 Pollinations
backfill generated `content/images/<slug>-bg.jpg` for all 18 existing cards,
updated each post's `card.photo`, and re-rendered the final branded PNGs. The
renderer now writes encoded local file URIs, so photos load correctly even when
the repo path contains spaces. Before scheduling any backfilled post through
Stage 3, check it is approved via the `post_status` table.

---

## Review sync (approvals persistence) — IMPORTANT

Approve/Decline in the review calendar persists to the Supabase `post_status`
table via `preview/supabase.js`, keyed by post slug (the filename stem). For this
to work, **`preview/supabase-config.js` must contain the real Supabase URL and
anon key**. The file ships empty in the repo (the anon key is public-safe behind
RLS, so the populated file is safe to commit / inject at deploy).

If it is left empty, the page runs unconfigured: a decision shows a visible red
"Review sync is not connected" banner and an explicit "Not saved" message, and on
reload every post falls back to its frontmatter `status: draft`. Previously the
page falsely reported "saved" in this state and silently lost the decision; that
is fixed (`decidePost` now only confirms a save when the write reached Supabase).
The fix makes the missing config visible — it does not replace it. Populate
`supabase-config.js` to actually persist approvals.

**Active debug note (2026-06-28):** the live/static preview was reported as
showing the old generic sync warning even though the local
`preview/supabase-config.js` contains a URL and anon/publishable key. Commit
`427ed03` now makes the warning report whether config is missing, the Supabase
SDK failed to load, or the database rejected the request. If the old exact text
still appears, check for a stale deployed preview before changing keys. See
[docs/claude-debug-handoff-2026-06-28.md](docs/claude-debug-handoff-2026-06-28.md)
before changing keys or rewriting the review sync.

**Known database setup error (2026-06-28):** if the warning says Supabase could
not find `public.post_status` in the schema cache, the browser reached the right
project but the review table has not been created there yet. Run
`supabase/schema.sql` in the Supabase SQL Editor. The schema is idempotent,
grants the anon role select/insert/update access, and reloads the PostgREST
schema cache. See
[docs/review-sync-supabase-setup.md](docs/review-sync-supabase-setup.md).

---

## Build stages

### Stage 1 — AI draft generator ✅ COMPLETE

One-click GitHub Action: takes a source URL plus notes, calls Gemini 2.5 Flash,
writes LinkedIn, Facebook and X drafts, rebuilds the preview, commits to `main`.

**How to trigger (production):**
1. Go to GitHub → Actions → "Generate social draft" → Run workflow
2. Fill in: primary source URL, topic notes, optional second URL
3. The workflow generates a draft, rebuilds the preview, and commits to the branch

**How to run locally:**
```bash
pip install -r scripts/requirements.txt
GEMINI_API_KEY=... python3 scripts/generate_draft.py \
  --url https://... \
  --notes "why this matters for fire safety contractors"
```

**Secrets required:**
- `GEMINI_API_KEY` — from Google AI Studio (aistudio.google.com), free tier (500 req/day)

### Stage 2 — Source monitor ✅ COMPLETE (shipped 2026-06-09)

Weekly cron (`monitor-sources.yml`, Mondays) checks the Scottish Building Standards
blog, gov.scot building standards updates, and new Scottish statutory instruments
for fire and building, then auto-triggers draft generation for anything new.
Sources are configured in `monitor/sources.json`. First fully automatic draft
(the 20m Single Open Call funding post) was committed by the bot on 2026-06-09.

**Still to do within Stage 2:** widen the source list (SFRS news, more gov.scot
policy feeds) and tune per-source notes templates.

### Stage 2.5 — Review page redesign ✅ BUILT (2026-06-10)

The calendar landing view, single-card-per-post previews, Facebook/LinkedIn/X
detail toggle, Approve/Decline, Copy text, source freshness, and the rolling
12-month-each-way calendar are all live in the generated `preview/index.html`.
Status reads and writes go to Supabase via `preview/supabase.js`. The "Next
approval" panel surfaces the **soonest upcoming pending draft** (chronological),
falling back to the most overdue draft if everything pending is in the past, so
the reviewer always lands on the post that matters next.

**Goal (original):** make reviewing and approving drafts effortless for a
non-technical user (Dougie) on any device.

**Agreed design (2026-06-10):**
- **Calendar landing view** — month grid, posts on their dates, colour-coded by
  status (draft / approved / published / declined)
- **One card per post** in list and calendar — title, date, source, status, and a
  single platform preview. **Facebook is the canonical collapsed preview**
  (Dougie's preferred platform); fall back to LinkedIn if a post has no Facebook
  version
- **Detail view** — the three platform versions as a toggle (Facebook / LinkedIn / X)
  using the existing platform-native card styling, with the Angle and review Notes
  shown clearly alongside, plus source links
- **Approve / Decline buttons** on the detail view, one tap each
- **Copy text button** per platform version, for copy-paste publishing until
  Stage 3 exists
- **Source freshness visible in review** — show when each source was published and
  flag old source material before approval
- **Rolling calendar** — show the previous 12 months, current month, and next 12
  months even when some months have no posts yet

**Approval-card layout update (2026-06-26):** the platform selector and Copy text
control now share one toolbar row, with the platform tabs left and a compact Copy
text button aligned right. Angle and Notes now sit at the bottom of the approval
card, below the platform previews and Approve/Decline controls, so the review
flow starts with the publishable copy and keeps context available afterwards.
The approval card also has a "Try another image" button beside the branded card
preview. It uses Pollinations in the browser to show an alternate text-free
background candidate when the current image is not quite right.

**Active image-button note (2026-06-28):** the button currently previews a new
Pollinations background only; it does not persist the alternate image to the
repo, update frontmatter, or re-render the final branded PNG. If Dougie expects
the button to replace the approved card image, that still needs a workflow or
backend-backed implementation. See the same Claude handoff note for the current
diagnostic state and suggested next steps.

**Status storage decision:** post status (approved / declined / published) is held
in **Supabase** — the same instance used by the Lead Scout — so the static preview
page can read and write status instantly with no GitHub involvement. Markdown
frontmatter `status` is the initial state only; **Supabase is the source of truth
for status once a post has been reviewed**. Document any schema in
`supabase/` within this repo when built.

**Implementation notes for the agent picking this up:**

1. **Supabase schema** — create `supabase/schema.sql` with a `post_status` table
   keyed by post slug (the markdown filename without extension). Suggested columns:
   `slug` (primary key), `status` (enum: draft / approved / declined / published),
   `decided_at`, `decided_by`, `notes`. Add a small JS wrapper (`preview/supabase.js`
   or similar) that the static preview page calls to read and write status. Reuse
   the Lead Scout's Supabase instance: get the project URL and anon key from
   Jonathan and put the var names in `.env.example` (do not commit real keys).

2. **Static-site constraint** — the preview is auto-refreshing static HTML today.
   Add Supabase via the official JS client loaded in the page (CDN or npm + bundle).
   Do NOT introduce a server, build step, or framework. The whole point of this
   stage is to stay static and cheap.

3. **Auth for approve / decline** — decide before building, because it shapes the
   UI. Two options:
   - **Long unguessable URL** (recommended for Stage 2.5): the preview lives at a
     hard-to-guess path, Supabase Row Level Security is permissive for the anon
     key, and Dougie just bookmarks the link. Simplest, ships fastest.
   - **Magic-link login** via Supabase Auth: more secure, but adds an email step
     before Dougie can approve anything. Only worth it if the preview URL leaks
     or stakes rise.
   Pick the unguessable-URL approach unless Jonathan says otherwise.

### Stage 3 — Social Media Agent / publish pipeline (AFTER 2.5)

**Goal:** push approved posts to LinkedIn, Facebook, and any other agreed channel
automatically, without giving the agent permission to invent or publish unreviewed
content.

**Agreed approach:** start with copy-paste publishing via the Stage 2.5 copy
buttons. Automatic posting comes later, only after confirming with Dougie which
platforms matter most and what schedule feels right. The default operating model is:
Content Radar drafts, Dougie approves or declines, then the Social Media Agent
autoposts only approved posts.

**Planned mechanics when built:**
- `scripts/publish.py` — reads approved posts from Supabase, chooses posts due for
  each platform, posts through the platform APIs, stores returned post IDs / URLs,
  and marks them published
- `.github/workflows/publish.yml` — scheduled cron plus manual trigger
- Optional per-platform switches so Facebook can launch before LinkedIn or X if
  API access lands at different times
- Failure handling that leaves the post approved but unpublished if an API call
  fails, so it can be retried without losing the review decision
- A freshness block that refuses to autopost stale approved posts unless the post
  has been explicitly marked evergreen or re-approved after review

**Secrets required (Stage 3 only):**
- `LINKEDIN_ACCESS_TOKEN`
- `FACEBOOK_PAGE_ACCESS_TOKEN` + `FACEBOOK_PAGE_ID`
- X API credentials if X autoposting is enabled

How MacFire grants the agent posting access per platform (partial access, who
owns what, how to mint the tokens) is documented in
[`docs/social-access-setup.md`](docs/social-access-setup.md).

---

## Guardrails (never remove these)

- Public sources only — no confidential lead data in any post
- No legal advice claims
- Human review before publishing; Stage 3 autoposting must read from approved status,
  never straight from generated drafts
- Source URL included in every post

---

## Cross-repo rule

After meaningful work here, update `data/projects.js` in
`jonathanmccrimmond/macfire-projects-dashboard` (plain-English wins and next
steps — see that repo's CLAUDE.md for the writing style rules), and keep this
PLAN.md's "Current state" section accurate.

---

## Local dev

```bash
# Preview all drafts as social cards
python3 scripts/build_preview.py --watch
# Then open preview/index.html in your browser (auto-refreshes every 30s)

# Validate all source links
python3 scripts/validate_links.py
```
