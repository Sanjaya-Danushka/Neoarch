-- NeoArch Multi-Bundle Cloud Schema
-- Run this in Supabase SQL Editor to create the required tables.
--
-- NOTE: Identity is now Clerk (third-party auth). `user_id` stores the Clerk
-- subject (`sub`, e.g. `user_2xxx`), NOT a Supabase auth.users UUID. RLS reads
-- the Clerk JWT via auth.jwt() and matches on the `sub` claim.

-- ── user_bundles: per-user bundle storage (replaces user_favorites) ──
CREATE TABLE IF NOT EXISTS user_bundles (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id     TEXT NOT NULL,
    bundle_key  TEXT NOT NULL,
    bundle_name TEXT NOT NULL DEFAULT 'My Bundle',
    bundle_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    item_count  INT NOT NULL DEFAULT 0,
    share_code  TEXT UNIQUE,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, bundle_key)
);

-- RLS: users can only access their own bundles
ALTER TABLE user_bundles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users read own bundles"
    ON user_bundles FOR SELECT
    USING (auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users insert own bundles"
    ON user_bundles FOR INSERT
    WITH CHECK (auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users update own bundles"
    ON user_bundles FOR UPDATE
    USING (auth.jwt() ->> 'sub' = user_id);

CREATE POLICY "Users delete own bundles"
    ON user_bundles FOR DELETE
    USING (auth.jwt() ->> 'sub' = user_id);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_user_bundles_user_id ON user_bundles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_bundles_share_code ON user_bundles(share_code) WHERE share_code IS NOT NULL;

-- ── shared_bundles: public share codes ──
CREATE TABLE IF NOT EXISTS shared_bundles (
    share_code  TEXT PRIMARY KEY,
    creator_id  TEXT,
    bundle_name TEXT NOT NULL,
    bundle_data JSONB NOT NULL DEFAULT '[]'::jsonb,
    item_count  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now(),
    expires_at  TIMESTAMPTZ
);

-- RLS: anyone can read shared bundles, only creator can delete
ALTER TABLE shared_bundles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can read shared bundles"
    ON shared_bundles FOR SELECT
    USING (true);

CREATE POLICY "Authenticated users can create shared bundles"
    ON shared_bundles FOR INSERT
    WITH CHECK (auth.jwt() ->> 'sub' = creator_id);

CREATE POLICY "Creators can delete their shared bundles"
    ON shared_bundles FOR DELETE
    USING (auth.jwt() ->> 'sub' = creator_id);

-- Index for share code lookups
CREATE INDEX IF NOT EXISTS idx_shared_bundles_creator ON shared_bundles(creator_id);

-- ── Migration from Supabase-auth user_id (UUID) to Clerk sub (TEXT) ──
-- Only needed if the tables already exist from the old schema. Backs up the
-- old values into a separate column first so nothing is lost.
-- ALTER TABLE user_bundles  ADD COLUMN IF NOT EXISTS user_id_old UUID;
-- ALTER TABLE shared_bundles ADD COLUMN IF NOT EXISTS creator_id_old UUID;
-- UPDATE user_bundles  SET user_id_old = user_id::uuid  WHERE user_id_old IS NULL;
-- UPDATE shared_bundles SET creator_id_old = creator_id::uuid WHERE creator_id_old IS NULL;
-- ALTER TABLE user_bundles  ALTER COLUMN user_id  TYPE TEXT USING user_id::text;
-- ALTER TABLE shared_bundles ALTER COLUMN creator_id TYPE TEXT USING creator_id::text;

-- ── Migrate existing user_favorites data (optional) ──
-- INSERT INTO user_bundles (user_id, bundle_key, bundle_name, bundle_data, item_count)
-- SELECT user_id, 'default', bundle_name, bundle_data, item_count
-- FROM user_favorites
-- ON CONFLICT (user_id, bundle_key) DO NOTHING;
