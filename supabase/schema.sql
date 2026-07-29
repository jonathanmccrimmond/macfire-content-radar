create table if not exists public.post_status (
  slug text primary key,
  status text not null check (status in ('draft', 'approved', 'declined', 'published')),
  decided_at timestamptz,
  decided_by text,
  notes text
);

alter table public.post_status enable row level security;

grant usage on schema public to anon, authenticated;
grant select, insert, update on public.post_status to anon, authenticated;

drop policy if exists "Allow anonymous review reads" on public.post_status;
create policy "Allow anonymous review reads"
  on public.post_status
  for select
  to anon
  using (true);

drop policy if exists "Allow anonymous review writes" on public.post_status;
create policy "Allow anonymous review writes"
  on public.post_status
  for insert
  to anon
  with check (status in ('draft', 'approved', 'declined', 'published'));

drop policy if exists "Allow anonymous review updates" on public.post_status;
create policy "Allow anonymous review updates"
  on public.post_status
  for update
  to anon
  using (true)
  with check (status in ('draft', 'approved', 'declined', 'published'));

-- Chosen image override per post. When a reviewer regenerates an image on the
-- approval page, the last one is saved here and restored on every visit, so the
-- choice persists without committing a new file to the repo.
create table if not exists public.post_image (
  slug text primary key,
  image_url text not null,
  updated_at timestamptz default now()
);

alter table public.post_image enable row level security;

grant select, insert, update on public.post_image to anon, authenticated;

drop policy if exists "Allow anonymous image reads" on public.post_image;
create policy "Allow anonymous image reads"
  on public.post_image
  for select
  to anon
  using (true);

drop policy if exists "Allow anonymous image writes" on public.post_image;
create policy "Allow anonymous image writes"
  on public.post_image
  for insert
  to anon
  with check (true);

drop policy if exists "Allow anonymous image updates" on public.post_image;
create policy "Allow anonymous image updates"
  on public.post_image
  for update
  to anon
  using (true)
  with check (true);

notify pgrst, 'reload schema';
