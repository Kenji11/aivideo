-- Add reference asset fields to assets table
-- Migration: 004_add_reference_asset_fields
-- Date: 2025-01-XX

-- Install pgvector extension (required for embedding column)
DO $$ 
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION
    WHEN OTHERS THEN
        -- Extension might already exist or might not be available
        -- Log warning but continue
        RAISE NOTICE 'pgvector extension: %', SQLERRM;
END $$;

-- Create new enum for reference asset types
DO $$ 
BEGIN
    CREATE TYPE reference_asset_type AS ENUM ('product', 'logo', 'person', 'environment', 'texture', 'prop');
EXCEPTION
    WHEN duplicate_object THEN 
        NULL;
END $$;

-- Add new columns to assets table
DO $$ 
BEGIN
    -- User-defined metadata
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'name'
    ) THEN
        ALTER TABLE assets ADD COLUMN name VARCHAR;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'description'
    ) THEN
        ALTER TABLE assets ADD COLUMN description TEXT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'reference_asset_type'
    ) THEN
        ALTER TABLE assets ADD COLUMN reference_asset_type reference_asset_type;
    END IF;

    -- Storage
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'thumbnail_url'
    ) THEN
        ALTER TABLE assets ADD COLUMN thumbnail_url VARCHAR;
    END IF;

    -- Image properties
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'width'
    ) THEN
        ALTER TABLE assets ADD COLUMN width INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'height'
    ) THEN
        ALTER TABLE assets ADD COLUMN height INTEGER;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'has_transparency'
    ) THEN
        ALTER TABLE assets ADD COLUMN has_transparency BOOLEAN DEFAULT false;
    END IF;

    -- AI Analysis
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'analysis'
    ) THEN
        ALTER TABLE assets ADD COLUMN analysis JSONB;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'primary_object'
    ) THEN
        ALTER TABLE assets ADD COLUMN primary_object VARCHAR;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'colors'
    ) THEN
        ALTER TABLE assets ADD COLUMN colors VARCHAR[];
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'dominant_colors_rgb'
    ) THEN
        ALTER TABLE assets ADD COLUMN dominant_colors_rgb JSONB;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'style_tags'
    ) THEN
        ALTER TABLE assets ADD COLUMN style_tags VARCHAR[];
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'recommended_shot_types'
    ) THEN
        ALTER TABLE assets ADD COLUMN recommended_shot_types VARCHAR[];
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'usage_contexts'
    ) THEN
        ALTER TABLE assets ADD COLUMN usage_contexts VARCHAR[];
    END IF;

    -- Logo-specific
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'is_logo'
    ) THEN
        ALTER TABLE assets ADD COLUMN is_logo BOOLEAN DEFAULT false;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'logo_position_preference'
    ) THEN
        ALTER TABLE assets ADD COLUMN logo_position_preference VARCHAR;
    END IF;

    -- Semantic Search (pgvector)
    -- Note: This requires pgvector extension to be installed
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'embedding'
    ) THEN
        BEGIN
            ALTER TABLE assets ADD COLUMN embedding vector(768);
        EXCEPTION
            WHEN OTHERS THEN
                -- If vector type is not available, log warning
                RAISE NOTICE 'Could not add embedding column (pgvector may not be installed): %', SQLERRM;
        END;
    END IF;

    -- Metadata
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE assets ADD COLUMN updated_at TIMESTAMPTZ;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'usage_count'
    ) THEN
        ALTER TABLE assets ADD COLUMN usage_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- Create indexes
DO $$ 
BEGIN
    -- Index on reference_asset_type
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'assets' AND indexname = 'idx_assets_reference_asset_type'
    ) THEN
        CREATE INDEX idx_assets_reference_asset_type ON assets(reference_asset_type);
    END IF;

    -- Index on primary_object (for text search)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'assets' AND indexname = 'idx_assets_primary_object'
    ) THEN
        CREATE INDEX idx_assets_primary_object ON assets(primary_object);
    END IF;

    -- Index on is_logo
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'assets' AND indexname = 'idx_assets_is_logo'
    ) THEN
        CREATE INDEX idx_assets_is_logo ON assets(is_logo);
    END IF;

    -- GIN index on style_tags array (for array queries)
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'assets' AND indexname = 'idx_assets_style_tags'
    ) THEN
        CREATE INDEX idx_assets_style_tags ON assets USING GIN(style_tags);
    END IF;

    -- IVFFlat index on embedding for vector search (requires pgvector)
    -- This index is created only if embedding column exists and pgvector is available
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'assets' AND column_name = 'embedding'
    ) THEN
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'assets' AND indexname = 'idx_assets_embedding'
            ) THEN
                -- IVFFlat index with 100 lists (adjust based on data size)
                -- Note: This index should be created after some data exists for better performance
                CREATE INDEX idx_assets_embedding ON assets 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100);
            END IF;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Could not create embedding index: %', SQLERRM;
        END;
    END IF;
END $$;

