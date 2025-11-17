-- Initial schema: assets and video_generations tables
-- Migration: 001_initial_schema
-- Date: 2024-11-16

-- Create enum types (only if they don't exist)
DO $$ BEGIN
    CREATE TYPE assettype AS ENUM ('IMAGE', 'VIDEO', 'AUDIO');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE assetsource AS ENUM ('USER_UPLOAD', 'SYSTEM_GENERATED');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE videostatus AS ENUM (
        'QUEUED',
        'VALIDATING',
        'GENERATING_ANIMATIC',
        'GENERATING_REFERENCES',
        'GENERATING_CHUNKS',
        'REFINING',
        'EXPORTING',
        'COMPLETE',
        'FAILED'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create assets table (only if it doesn't exist)
CREATE TABLE IF NOT EXISTS assets (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR,
    s3_key VARCHAR NOT NULL,
    s3_url VARCHAR,
    asset_type assettype NOT NULL,
    source assetsource NOT NULL,
    file_name VARCHAR,
    file_size_bytes INTEGER,
    mime_type VARCHAR,
    asset_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create video_generations table (only if it doesn't exist)
CREATE TABLE IF NOT EXISTS video_generations (
    id VARCHAR NOT NULL PRIMARY KEY,
    user_id VARCHAR,
    title VARCHAR NOT NULL,
    description VARCHAR,
    prompt VARCHAR NOT NULL,
    prompt_validated VARCHAR,
    reference_assets JSONB DEFAULT '[]',
    spec JSONB,
    template VARCHAR,
    status videostatus DEFAULT 'QUEUED',
    progress FLOAT DEFAULT 0.0,
    current_phase VARCHAR,
    error_message VARCHAR,
    animatic_urls JSONB DEFAULT '[]',
    chunk_urls JSONB DEFAULT '[]',
    stitched_url VARCHAR,
    refined_url VARCHAR,
    final_video_url VARCHAR,
    final_music_url VARCHAR,
    phase_outputs JSONB DEFAULT '{}',
    cost_usd FLOAT DEFAULT 0.0,
    cost_breakdown JSONB DEFAULT '{}',
    generation_time_seconds FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Create indexes for common queries (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_video_generations_user_id ON video_generations(user_id);
CREATE INDEX IF NOT EXISTS idx_video_generations_status ON video_generations(status);
CREATE INDEX IF NOT EXISTS idx_video_generations_created_at ON video_generations(created_at);
CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets(user_id);
CREATE INDEX IF NOT EXISTS idx_assets_asset_type ON assets(asset_type);

