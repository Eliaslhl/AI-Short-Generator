-- prod_fix.sql
-- Idempotent fixes to bring the DB schema in line with the app models.
-- Run this from a shell that can reach the target database (Railway shell, or
-- use docker run with network access). Review before executing.

-- 1) Create enum type 'plan' if missing
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'plan') THEN
        CREATE TYPE plan AS ENUM ('free','standard','pro','proplus');
    END IF;
END$$;

-- 2) Ensure alembic_version table exists and version_num is wide enough
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'alembic_version'
    ) THEN
        CREATE TABLE alembic_version (version_num varchar(255) NOT NULL);
    ELSE
        BEGIN
            ALTER TABLE alembic_version ALTER COLUMN version_num TYPE varchar(255);
        EXCEPTION WHEN undefined_column THEN
            ALTER TABLE alembic_version ADD COLUMN IF NOT EXISTS version_num varchar(255) NOT NULL;
        END;
    END IF;
END$$;

-- 3) Add missing columns to users table (idempotent)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;
ALTER TABLE users ALTER COLUMN is_active SET DEFAULT true;
UPDATE users SET is_active = true WHERE is_active IS NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified boolean DEFAULT false;
ALTER TABLE users ALTER COLUMN is_verified SET DEFAULT false;
UPDATE users SET is_verified = false WHERE is_verified IS NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS plan plan DEFAULT 'free';
ALTER TABLE users ALTER COLUMN plan SET DEFAULT 'free';

ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_youtube plan DEFAULT 'free';
ALTER TABLE users ALTER COLUMN plan_youtube SET DEFAULT 'free';

ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_twitch plan DEFAULT 'free';
ALTER TABLE users ALTER COLUMN plan_twitch SET DEFAULT 'free';

ALTER TABLE users ADD COLUMN IF NOT EXISTS subscription_type varchar(50) DEFAULT 'none';
ALTER TABLE users ALTER COLUMN subscription_type SET DEFAULT 'none';
UPDATE users SET subscription_type = 'none' WHERE subscription_type IS NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS generations_this_month integer DEFAULT 0;
ALTER TABLE users ALTER COLUMN generations_this_month SET DEFAULT 0;
UPDATE users SET generations_this_month = 0 WHERE generations_this_month IS NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_reset_date timestamptz DEFAULT now();
ALTER TABLE users ALTER COLUMN plan_reset_date SET DEFAULT now();

ALTER TABLE users ADD COLUMN IF NOT EXISTS youtube_generations_month integer DEFAULT 0;
ALTER TABLE users ALTER COLUMN youtube_generations_month SET DEFAULT 0;
UPDATE users SET youtube_generations_month = 0 WHERE youtube_generations_month IS NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS youtube_plan_reset_date timestamptz DEFAULT now();
ALTER TABLE users ALTER COLUMN youtube_plan_reset_date SET DEFAULT now();

ALTER TABLE users ADD COLUMN IF NOT EXISTS twitch_generations_month integer DEFAULT 0;
ALTER TABLE users ALTER COLUMN twitch_generations_month SET DEFAULT 0;
UPDATE users SET twitch_generations_month = 0 WHERE twitch_generations_month IS NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS twitch_plan_reset_date timestamptz DEFAULT now();
ALTER TABLE users ALTER COLUMN twitch_plan_reset_date SET DEFAULT now();

ALTER TABLE users ADD COLUMN IF NOT EXISTS youtube_limit_override integer;
ALTER TABLE users ADD COLUMN IF NOT EXISTS twitch_limit_override integer;

ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id varchar(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id varchar(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id_twitch varchar(255);

-- Ensure id column length
ALTER TABLE users ALTER COLUMN id TYPE varchar(36);

-- 4) Minimal create for jobs and password_reset_tokens if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'jobs'
    ) THEN
        CREATE TABLE jobs (
            id varchar(36) PRIMARY KEY,
            user_id varchar(36) NOT NULL,
            youtube_url varchar(512) NOT NULL,
            video_title varchar(512),
            status varchar(50) DEFAULT 'pending',
            progress integer DEFAULT 0,
            message varchar(255),
            error text,
            clips_json text,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        );
    END IF;
END$$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'password_reset_tokens'
    ) THEN
        CREATE TABLE password_reset_tokens (
            id varchar(36) PRIMARY KEY,
            user_id varchar(36) NOT NULL,
            token varchar(64) UNIQUE,
            expires_at timestamptz NOT NULL,
            used boolean DEFAULT false,
            created_at timestamptz DEFAULT now()
        );
    END IF;
END$$;

-- Final safety updates
UPDATE users SET is_active = true WHERE is_active IS NULL;
UPDATE users SET is_verified = false WHERE is_verified IS NULL;

-- End of prod_fix.sql
