-- Migration: Supabase Auth UUID user_id -> Clerk sub TEXT
-- Run this ONCE on an existing database that used the old schema
-- (user_bundles.user_id UUID REFERENCES auth.users, shared_bundles.creator_id UUID).
-- For a fresh database, just run supabase_schema.sql instead.

-- 1. Drop old RLS policies (they compare uuid, will break after type change)
DROP POLICY IF EXISTS "Users read own bundles"    ON user_bundles;
DROP POLICY IF EXISTS "Users insert own bundles"  ON user_bundles;
DROP POLICY IF EXISTS "Users update own bundles"  ON user_bundles;
DROP POLICY IF EXISTS "Users delete own bundles"  ON user_bundles;
DROP POLICY IF EXISTS "Anyone can read shared bundles"                   ON shared_bundles;
DROP POLICY IF EXISTS "Authenticated users can create shared bundles"    ON shared_bundles;
DROP POLICY IF EXISTS "Creators can delete their shared bundles"         ON shared_bundles;

-- 2. Drop FK constraints that force uuid, so the column type can change
ALTER TABLE user_bundles   DROP CONSTRAINT IF EXISTS user_bundles_user_id_fkey;
ALTER TABLE shared_bundles DROP CONSTRAINT IF EXISTS shared_bundles_creator_id_fkey;

-- 3. Convert columns to TEXT (does not touch existing row values)
ALTER TABLE user_bundles   ALTER COLUMN user_id       TYPE TEXT;
ALTER TABLE shared_bundles ALTER COLUMN creator_id    TYPE TEXT;

-- 4. Recreate RLS policies matching the Clerk JWT `sub` claim
ALTER TABLE user_bundles ENABLE ROW LEVEL SECURITY;
ALTER TABLE shared_bundles ENABLE ROW LEVEL SECURITY;

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

CREATE POLICY "Anyone can read shared bundles"
    ON shared_bundles FOR SELECT
    USING (true);

CREATE POLICY "Authenticated users can create shared bundles"
    ON shared_bundles FOR INSERT
    WITH CHECK (auth.jwt() ->> 'sub' = creator_id);

CREATE POLICY "Creators can delete their shared bundles"
    ON shared_bundles FOR DELETE
    USING (auth.jwt() ->> 'sub' = creator_id);