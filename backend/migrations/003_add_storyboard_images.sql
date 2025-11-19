-- Add storyboard_images column to video_generations
-- Migration: 003_add_storyboard_images
-- Date: 2025-11-16
-- Note: This column was later deprecated in favor of storing 
-- storyboard images in phase_outputs['phase2_storyboard']

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'video_generations' 
        AND column_name = 'storyboard_images'
    ) THEN
        ALTER TABLE video_generations 
        ADD COLUMN storyboard_images JSONB;
    END IF;
END $$;

