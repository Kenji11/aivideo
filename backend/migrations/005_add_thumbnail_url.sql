-- Add thumbnail_url column to video_generations table
-- Migration: 005_add_thumbnail_url
-- Date: 2025-01-XX

-- Add thumbnail_url column if it doesn't exist
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'video_generations' AND column_name = 'thumbnail_url'
    ) THEN
        ALTER TABLE video_generations ADD COLUMN thumbnail_url VARCHAR;
    END IF;
END $$;

