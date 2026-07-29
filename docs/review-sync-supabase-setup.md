# Review sync Supabase setup

The approval calendar stores Approve/Decline decisions in Supabase table
`public.post_status`. If the preview shows this message:

```text
Review sync is not connected, so Approve and Decline will not be saved. The review database rejected the request (Could not find the table 'public.post_status' in the schema cache). The post_status table and its access rules may not be set up yet.
```

then the browser can reach the Supabase project, but the `post_status` table has
not been created in that project, or Supabase's API schema cache has not reloaded
after creation.

## Immediate fix

1. Open the Supabase dashboard for project:

   ```text
   https://vruphucsmzpehybtijja.supabase.co
   ```

2. Go to **SQL Editor**.

3. Paste and run the full contents of:

   ```text
   supabase/schema.sql
   ```

4. Refresh the Content Radar preview page.

The schema file is safe to run more than once. It uses `create table if not
exists`, recreates the RLS policies idempotently, grants the browser role access,
and sends `notify pgrst, 'reload schema';` so PostgREST can see the new table.

## Impact on MacFire AI Lead Scout

This setup should not affect the MacFire AI Lead Scout leads database.

Content Radar reuses the same Supabase project and anon/publishable key, but it
creates and manages only one separate table:

```text
public.post_status
```

The SQL in `supabase/schema.sql` does not drop, rename, update, or change
permissions on any Lead Scout lead tables. The only broad statement is
`grant usage on schema public to anon, authenticated;`, which allows those roles
to see that the `public` schema exists. It does not grant access to any table by
itself. Table-level access is granted only for `public.post_status`.

## Expected table

`public.post_status` is keyed by markdown filename stem:

```sql
slug text primary key,
status text not null check (status in ('draft', 'approved', 'declined', 'published')),
decided_at timestamptz,
decided_by text,
notes text
```

The static review page writes with the public anon/publishable key. This is
intentional for Stage 2.5: the approval page is public-static, and Row Level
Security is deliberately permissive for this one review table. If stronger auth
is needed later, replace this with Supabase Auth or a backend endpoint before
changing the current frontend assumptions.

## Quick browser check

After running the SQL, open the live preview and run:

```js
await window.ContentRadarStatus.loadStatuses(window.CONTENT_RADAR_POSTS.map((p) => p.slug))
```

Expected result:

```js
{ ok: true, connected: true, statuses: { ... } }
```

If it still says the table is missing, wait a few seconds and refresh. If it
continues, confirm the SQL was run in the same Supabase project used by
`preview/supabase-config.js`.
