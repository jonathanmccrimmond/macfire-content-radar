# Claude debug handoff - 2026-06-28

This note captures the current state of the Content Radar approval-page debugging
session so another agent can continue without re-discovering the same context.

## User-reported issues

Two separate browser-side issues were reported in the live/static Content Radar
preview:

1. The approval page shows:

   ```text
   Review sync is not connected, so Approve and Decline will not be saved. Set the Supabase URL and anon key in supabase-config.js.
   ```

   Follow-up from the live page later narrowed this down to the database setup:

   ```text
   The review database rejected the request (Could not find the table 'public.post_status' in the schema cache).
   ```

   That means the browser reached Supabase, but `public.post_status` is missing
   from the project or the API schema cache has not reloaded. Run
   `supabase/schema.sql` in the Supabase SQL Editor; see
   `docs/review-sync-supabase-setup.md`.

2. The image change button ("Try another image") is not working.

## Current repo state

- Repo: `Kinact-AI/macfire-content-radar`
- Local path: `/Users/jonathanmccrimmond/Documents/MacFire Projects/macfire-content-radar`
- Branch: `main`
- Working tree was clean before this handoff note was added.
- Relevant commits already on `main` before this handoff note was finalized:
  - `821502c` - `Backfill card background photos`
  - `20882e5` - `Premium minimal post images: photo-led, intent-based`
  - `cea769c` - `Auto-detect intent for new posts in the drafting pipeline`
  - `427ed03` - `Review sync: show the real reason it is not connected`

## What is confirmed locally

### Supabase config is present

`preview/supabase-config.js` currently defines `window.CONTENT_RADAR_SUPABASE`
with both a URL and an anon/publishable key:

```js
window.CONTENT_RADAR_SUPABASE = {
  url: "https://vruphucsmzpehybtijja.supabase.co",
  anonKey: "sb_publishable_2ZisTv6fjNDMXzPbLH1RzA_t2g-FlpT",
};
```

So the warning should not be treated as proof that the config file is empty.
The warning copy is currently too generic/misleading.

### Supabase client path

The generated preview loads scripts in this order from
`scripts/build_preview.py`:

```html
<script src="supabase-config.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script src="supabase.js"></script>
```

As of commit `427ed03`, `preview/supabase.js` returns an
unconfigured/local-only result with a `reason` when any of these is missing:

- `config.url`
- `config.anonKey`
- `window.supabase`

As of commit `427ed03`, the review page tries to show a more specific reason
for sync failure:

- `config-missing`: "Set the review database address and key in
  supabase-config.js."
- `sdk-missing`: "The review sync library did not load..."
- Supabase error: "The review database rejected the request (...)."

If the user still sees the old exact text ending with `Set the Supabase URL and
anon key in supabase-config.js.`, assume the browser may be seeing an older
deployed `preview/index.html` / `preview/supabase.js` until proven otherwise.

The banner can still ultimately mean any of:

- config missing on the deployed page
- Supabase CDN did not load, so `window.supabase` is undefined (`sdk-missing`)
- `preview/supabase.js` did not load
- `post_status` table missing or wrong in the Supabase project
- RLS/policy/key problem
- network/ad-block/content blocker issue in the browser

Do not assume the URL/key are missing without checking the deployed file,
browser console/network panel, and whether GitHub Pages has the newer `427ed03`
preview files.

### Image button path

The "Try another image" button is generated in `scripts/build_preview.py` and
appears in `preview/index.html` as:

```html
<button class="image-regen-btn" type="button" data-regenerate-image data-post-slug="...">
  Try another image
</button>
```

Click handling is in `scripts/build_preview.py`:

- `document.addEventListener("click", ...)`
- click target `[data-regenerate-image]`
- calls `regenerateImage(slug)`
- looks up `post.imageIdea` from `window.CONTENT_RADAR_POSTS`
- builds `https://image.pollinations.ai/prompt/...`
- writes it to `[data-image-candidate-img].src`
- shows status text: "New background preview loading.", "ready.", or
  "Image preview failed. Try again."

`posts_json` includes `imageIdea` from each post's `card.image_idea`, so the
data should be present for the existing cards.

Important: the current button only previews an alternate Pollinations background
in the browser. It does **not** persist that alternate to `content/images/`,
update markdown frontmatter, or re-render the branded final card PNG. If the user
expects the button to permanently swap the approved image, that capability is not
built yet.

## What could not be verified from this environment

The local Codex/Claude environment may be unable to reach external hosts such as:

- `https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2`
- `https://vruphucsmzpehybtijja.supabase.co`
- `https://image.pollinations.ai`

If a local command fails because those hosts are blocked by the sandbox/proxy, do
not treat that as proof the user's browser cannot reach them. Use the live
browser's console/network panel or a real network environment.

## Recommended next debugging steps

### 1. Inspect the deployed files first

In the browser or with curl from a real network, check:

- `https://kinact-ai.github.io/macfire-content-radar/preview/supabase-config.js`
- `https://kinact-ai.github.io/macfire-content-radar/preview/supabase.js`
- `https://kinact-ai.github.io/macfire-content-radar/preview/index.html`

Confirm the deployed `supabase-config.js` contains the same URL/key as local.
If GitHub Pages is serving an older build, rebuild/push the preview.

### 2. Use browser console diagnostics

On the live preview page, run:

```js
window.CONTENT_RADAR_SUPABASE
Boolean(window.supabase)
Boolean(window.ContentRadarStatus)
await window.ContentRadarStatus?.loadStatuses(window.CONTENT_RADAR_POSTS.map((p) => p.slug))
```

Interpretation:

- `CONTENT_RADAR_SUPABASE` empty: deployed config issue.
- `window.supabase === false`: CDN/load/ad-block issue.
- `ContentRadarStatus === false`: `preview/supabase.js` load/order issue.
- `loadStatuses()` returns `{ ok: false, connected: true, error: ... }`: real
  Supabase table/RLS/key problem. Commit `427ed03` should now surface this as a
  database rejection instead of blaming the URL/key.

### 3. Check image button in browser console/network

Click "Try another image" and inspect:

- Does the status text change to "New background preview loading."?
- Does a request to `image.pollinations.ai/prompt/...` appear in Network?
- Does it fail due to DNS, blocked content, CORS, unsafe content, or HTTP error?
- Does the page log any JavaScript exception before the click handler reaches
  `regenerateImage()`?

Also run:

```js
window.CONTENT_RADAR_POSTS.find((p) => p.slug === "2026-10-29-01-fireworks-bonfire-night-safety")?.imageIdea
```

If it returns an empty string for the affected post, rebuild the preview from the
latest markdown:

```bash
python3 scripts/build_preview.py --skip-link-check
```

## Likely code improvements

### Supabase diagnostics status

Commit `427ed03` already changed `preview/supabase.js`,
`scripts/build_preview.py`, and the generated `preview/index.html` so the UI
distinguishes missing config, missing SDK, and Supabase query/write errors.
Next work should verify the deployed GitHub Pages version and the live browser
console/network output rather than re-implementing that same diagnostic split.

### Make image regeneration more honest/useful

At minimum, improve button feedback:

- show "No image idea available" when `post.imageIdea` is empty
- show the generated Pollinations URL in the console on failure
- show a clearer failure when the image host is blocked

If the desired behaviour is "replace the approved card image", then build a real
server/workflow-backed action. A static GitHub Pages page cannot write a new JPG
to the repo or re-render the final card PNG by itself. The persistent path would
need one of:

- a GitHub Actions `workflow_dispatch` endpoint triggered through a backend
- a Supabase Edge Function that calls Pollinations/Gemini and stores a candidate
- a local/script workflow: run `python3 scripts/generate_card_photo.py --force`
  for the chosen post, rebuild, commit, and push

## Files most likely to edit next

- `scripts/build_preview.py` - owns generated UI, warning copy, click handler,
  Pollinations candidate preview, and `preview/index.html` generation.
- `preview/supabase.js` - owns Supabase client construction, status loading, and
  status saving.
- `preview/supabase-config.js` - check deployed values, but do not blindly rotate
  keys unless Supabase confirms the current key is invalid.
- `supabase/schema.sql` - verify table and RLS policies match the project.
- `PLAN.md` and `README.md` - update once the diagnosis/fix is complete.
