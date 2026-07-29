# MacFire Content Radar

Standalone repo for MacFire's public-source social content pipeline.

Repository: https://github.com/Kinact-AI/macfire-content-radar

This is the source of truth for the Content Radar project. It is separate from the
MacFire AI Scout lead-generation repo.

## POC Scope

- Track official public updates relevant to fire safety, building standards, and compliance.
- Draft LinkedIn, Facebook, and X copy from those public sources.
- Keep source links with every post.
- Keep human review in the loop before anything is published.
- Prepare the path to a Social Media Agent that can auto-post approved content on schedule.

## Current Seed Posts

Official update drafts:

1. Section 2 Fire updates and new technical handbooks from 6 April 2026.
2. Section 2 Fire call for evidence in Scotland.
3. Traditional buildings conversion guidance in Scotland.
4. Cladding remediation warrant verification in Scotland.
5. 20m Single Open Call funding update.

Evergreen seasonal drafts (reusable each year with a light review pass):

- Summer hospitality readiness (June).
- BBQ and outdoor cooking safety (July).
- Student lets and HMOs (September).
- Fireworks and Bonfire Night (October / November).
- Christmas trading and shutdown checks (December).
- Winter electrical load and portable heaters (January).

The 12-month plan and the rules for refreshing evergreen posts are in
[docs/seasonal-content-calendar.md](docs/seasonal-content-calendar.md).

### Evergreen frontmatter

Seasonal posts that are not tied to a specific public source carry `evergreen: true`
in their YAML frontmatter and omit the `sources:` block. The freshness pill in the
review calendar shows as neutral for these posts, which is intentional: the
reviewer should re-read the copy, bump the date, and re-approve before it runs
again next year.

## Preview

Open [preview/index.html](preview/index.html) directly in your browser to review drafts in the Content Radar calendar.

The preview landing screen shows one month at a time beside the next draft awaiting approval. It includes the previous 12 months, the current month, and the next 12 months, even when some months are empty. Use the month arrows to move through the calendar, switch the active post between Facebook, LinkedIn, and X, copy platform text, and approve or decline the draft. After approval or decline, the next newest draft appears automatically.

Each source should include its publication date when available. The preview flags source freshness so old updates are not accidentally approved as if they were new.

This is the review layer for the future Social Media Agent: Content Radar finds public updates and prepares the posts, Dougie approves what is safe to publish, and the publishing layer will later push approved posts to the selected social channels automatically.

To regenerate the preview from the markdown drafts:

```bash
python3 scripts/build_preview.py
python3 scripts/build_preview.py --watch
```

Watch mode keeps rebuilding the preview whenever a file in `content/posts/` changes.

Approve and decline buttons use Supabase when configured. Copy `preview/supabase-config.js` values from the Lead Scout Supabase project URL and anon key, or use the variable names in `.env.example` for deployment automation. Real keys should not be committed.

If the preview says Supabase cannot find `public.post_status`, the database
schema has not been applied to the Supabase project yet. Run
[supabase/schema.sql](supabase/schema.sql) in the Supabase SQL Editor; the exact
steps are in
[docs/review-sync-supabase-setup.md](docs/review-sync-supabase-setup.md).

### Current approval-page debug handoff

As of 2026-06-28, two live preview issues are under investigation: the review
sync warning appears even though local Supabase config is present, and the "Try
another image" button is not behaving as expected. The precise handoff for Claude
or the next agent is in
[docs/claude-debug-handoff-2026-06-28.md](docs/claude-debug-handoff-2026-06-28.md).
Start there before changing the Supabase config or image-generation flow.

## Guardrails

- Public sources only.
- No confidential lead data.
- No automatic publishing until the Social Media Agent is explicitly enabled.
- Auto-post only approved posts, with platform credentials kept out of git.
- No legal advice claims.

## Next Step

Build the Social Media Agent publish layer: read approved posts from Supabase, publish them to the agreed social channels on schedule, and mark each post as published once the platform confirms success.
