-- Add final_music_url column to video_generations
-- Migration: 002_add_final_music_url
-- Date: 2025-11-16

-- Note: This column was actually included in 001_initial_schema.sql
-- This migration is kept for historical tracking but is a no-op
-- if the column already exists (which it should from 001)

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'video_generations' 
        AND column_name = 'final_music_url'
    ) THEN
        ALTER TABLE video_generations 
        ADD COLUMN final_music_url VARCHAR;
    END IF;
END $$;

