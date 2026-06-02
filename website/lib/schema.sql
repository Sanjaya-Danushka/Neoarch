-- Run this SQL in your Supabase SQL Editor (https://fdzeqeobabojnhqiokky.supabase.co)

-- Create favorites table
create table if not exists public.user_favorites (
  id uuid primary key default gen_random_uuid(),
  user_id text not null,
  bundle_name text not null,
  bundle_data jsonb not null default '[]'::jsonb,
  item_count int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Index for fast user lookups
create index if not exists idx_user_favorites_user_id on public.user_favorites(user_id);

-- Enable RLS
alter table public.user_favorites enable row level security;

-- RLS: users can only see their own favorites
create policy "Users can view own favorites"
  on public.user_favorites for select
  using (auth.uid()::text = user_id);

-- RLS: users can insert their own favorites
create policy "Users can insert own favorites"
  on public.user_favorites for insert
  with check (auth.uid()::text = user_id);

-- RLS: users can update their own favorites
create policy "Users can update own favorites"
  on public.user_favorites for update
  using (auth.uid()::text = user_id);

-- RLS: users can delete their own favorites
create policy "Users can delete own favorites"
  on public.user_favorites for delete
  using (auth.uid()::text = user_id);
