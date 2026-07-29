# Social posting access — setup and status

Context for any agent or developer wiring up Stage 3 autoposting (see
`PLAN.md`). This explains how MacFire grants the agent permission to post on
each platform, who owns what, and which secrets the publish pipeline expects.

## Who owns what (important)

- **MacFire Ltd** (Dougie) owns the social accounts (Facebook page, LinkedIn,
  X). MacFire is the client.
- **McCrimmond** (Jonathan) is a **separate business** running this pipeline on
  MacFire's behalf. The agent posts *as MacFire* using access MacFire grants,
  not because the accounts belong to McCrimmond.
- Access is always **scoped and revocable**: MacFire keeps full control of each
  account and can switch the agent's access off at any time. Never ask for or
  store full-admin credentials.

## Status per platform (as of 2026-06)

| Platform | State | Blocker |
|---|---|---|
| Facebook | Ready, pending access grant | Dougie to grant partial page access |
| LinkedIn | Blocked on prerequisite | MacFire is a personal profile; needs a Company Page before API posting is possible |
| X (Twitter) | Paused | Write API costs ~$100/month; not worth it yet |

## Facebook

### Access model

Posting via the Graph API needs the `pages_manage_posts` permission, which is
tied to the page's **content/posting task, not the admin role**. So MacFire
grants **partial access**, never full admin:

- Dougie: Meta Business Suite → Settings → Page access → "People with Facebook
  access" → Add `j@mccrimmond.org.uk` → leave the **full-control toggle OFF** →
  save.
- Partial access allows creating/managing posts but not changing settings,
  managing people, billing, or deleting the page. Revocable in one click.

A tighter alternative (for a cleaner client boundary) is **Business portfolio
partner access** granting only the single "Content" task via Business Manager.
It is more setup (both sides on Business Manager) and not needed for one page.

### Generating the token (McCrimmond side, once access is granted)

1. Create a Meta app at developers.facebook.com → My Apps → Create App →
   type **Business**. Note the **App ID** and **App Secret** (Settings → Basic).
2. Graph API Explorer (developers.facebook.com/tools/explorer): select the app,
   add permissions `pages_show_list`, `pages_read_engagement`,
   `pages_manage_posts`, generate a user token and approve.
3. In the token dropdown pick the MacFire Ltd page under "Page Access Tokens".
   The Debug button reveals the **Page ID**.
4. Make the token non-expiring (the Explorer token lasts ~1 hour):

   ```bash
   # short-lived user token -> 60-day user token
   curl -s "https://graph.facebook.com/v20.0/oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_USER_TOKEN"

   # 60-day user token -> non-expiring page token (token next to the MacFire page)
   curl -s "https://graph.facebook.com/v20.0/me/accounts?access_token=LONG_LIVED_USER_TOKEN"
   ```

   The page `access_token` here does not expire while the role is held.
5. Test:

   ```bash
   curl -s -X POST "https://graph.facebook.com/v20.0/PAGE_ID/feed" \
     -d "message=MacFire test post" -d "access_token=PAGE_ACCESS_TOKEN"
   ```

### Secrets (GitHub Actions, never in git)

- `FACEBOOK_PAGE_ACCESS_TOKEN` — non-expiring page token from step 4
- `FACEBOOK_PAGE_ID` — page ID from step 3

## LinkedIn

Auto-posting requires a **Company Page** plus the LinkedIn marketing/community
API (`w_organization_social`). The MacFire account is currently a personal
profile, so the prerequisite is creating the Company Page first.

Dougie creates the page: LinkedIn → "For Business" grid icon → "Create a Company
Page" → Company → fill name (MacFire Ltd), public URL, website, industry (Fire
Protection), size and type → upload logo/tagline → confirm authorisation →
Create page. Then he grants McCrimmond a scoped page admin role (content level),
same principle as Facebook: enough to post, nothing more.

### Secret (Stage 3)

- `LINKEDIN_ACCESS_TOKEN`

## X (Twitter)

Paused. Posting requires the paid X API tier (~$100/month). Revisit only if X
becomes a priority channel. If enabled, the publish pipeline expects the X API
credentials documented in `PLAN.md`.

## Guardrail

These tokens let the agent post as MacFire. The agent must only ever publish
posts that are **approved** in the review calendar (`post_status` table), never
straight from generated drafts. See `PLAN.md` guardrails.
