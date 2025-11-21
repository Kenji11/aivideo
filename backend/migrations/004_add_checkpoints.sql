-- Add checkpoint support for video generation pipeline
-- Migration: 004_add_checkpoints
-- Date: 2025-11-20

-- Add new video status values for checkpoint pausing
DO $$ BEGIN
    ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE1';
    ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE2';
    ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE3';
    ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE4';
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Add auto_continue flag to video_generations
DO $$ BEGIN
    ALTER TABLE video_generations
    ADD COLUMN auto_continue BOOLEAN DEFAULT FALSE;
EXCEPTION
    WHEN duplicate_column THEN null;
END $$;

-- Create video_checkpoints table
CREATE TABLE IF NOT EXISTS video_checkpoints (
    id VARCHAR PRIMARY KEY,
    video_id VARCHAR NOT NULL,
    branch_name VARCHAR NOT NULL,
    phase_number INTEGER NOT NULL CHECK (phase_number IN (1, 2, 3, 4)),
    version INTEGER NOT NULL CHECK (version > 0),

    -- Lineage
    parent_checkpoint_id VARCHAR REFERENCES video_checkpoints(id) ON DELETE SET NULL,

    -- State
    status VARCHAR NOT NULL CHECK (status IN ('pending', 'approved', 'abandoned')),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Phase output
    phase_output JSONB NOT NULL,
    cost_usd DECIMAL(10, 4) NOT NULL DEFAULT 0,

    -- User context
    user_id VARCHAR NOT NULL,
    edit_description TEXT,

    -- Constraints
    UNIQUE(video_id, branch_name, phase_number, version),
    FOREIGN KEY (video_id) REFERENCES video_generations(id) ON DELETE CASCADE
);

-- Create checkpoint_artifacts table
CREATE TABLE IF NOT EXISTS checkpoint_artifacts (
    id VARCHAR PRIMARY KEY,
    checkpoint_id VARCHAR NOT NULL,

    -- Artifact identity
    artifact_type VARCHAR NOT NULL,
    artifact_key VARCHAR NOT NULL,

    -- Storage
    s3_url VARCHAR NOT NULL,
    s3_key VARCHAR NOT NULL,

    -- Versioning
    version INTEGER NOT NULL CHECK (version > 0),
    parent_artifact_id VARCHAR REFERENCES checkpoint_artifacts(id) ON DELETE SET NULL,

    -- Metadata
    metadata JSONB,
    file_size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Constraints
    UNIQUE(checkpoint_id, artifact_type, artifact_key),
    FOREIGN KEY (checkpoint_id) REFERENCES video_checkpoints(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_checkpoints_video ON video_checkpoints(video_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_branch ON video_checkpoints(video_id, branch_name);
CREATE INDEX IF NOT EXISTS idx_checkpoints_parent ON video_checkpoints(parent_checkpoint_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON video_checkpoints(status);

CREATE INDEX IF NOT EXISTS idx_artifacts_checkpoint ON checkpoint_artifacts(checkpoint_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON checkpoint_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_artifacts_parent ON checkpoint_artifacts(parent_artifact_id);
