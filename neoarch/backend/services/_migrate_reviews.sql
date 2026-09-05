-- Reviews for the NeoArch website (my-Website).
-- Public read; write/update/delete only by the review owner via Clerk JWT.
-- Requires the native Supabase + Clerk third-party auth integration
-- (auth.jwt() ->> 'sub'  =  Clerk user id).

create table if not exists public.reviews (
  id          uuid primary key default gen_random_uuid(),
  user_id     text not null,
  name        text not null,
  rating      integer not null check (rating between 1 and 5),
  message     text not null,
  created_at  timestamptz not null default now()
);

alter table public.reviews enable row level security;

drop policy if exists reviews_select on public.reviews;
create policy reviews_select on public.reviews
  for select using (true);

drop policy if exists reviews_insert on public.reviews;
create policy reviews_insert on public.reviews
  for insert with check (auth.jwt() ->> 'sub' = user_id);

drop policy if exists reviews_update on public.reviews;
create policy reviews_update on public.reviews
  for update using (auth.jwt() ->> 'sub' = user_id)
  with check (auth.jwt() ->> 'sub' = user_id);

drop policy if exists reviews_delete on public.reviews;
create policy reviews_delete on public.reviews
  for delete using (auth.jwt() ->> 'sub' = user_id);