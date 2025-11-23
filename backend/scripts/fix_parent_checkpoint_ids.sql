-- Fix parent_checkpoint_id for existing checkpoints
-- This updates null parent_checkpoint_id values based on phase progression and timestamps

-- Update Phase 2 checkpoints to point to their Phase 1 parent
UPDATE video_checkpoints AS cp2
SET parent_checkpoint_id = (
    SELECT cp1.id
    FROM video_checkpoints AS cp1
    WHERE cp1.video_id = cp2.video_id
    AND cp1.phase_number = 1
    AND cp1.created_at < cp2.created_at
    AND cp1.branch_name = cp2.branch_name
    ORDER BY cp1.created_at DESC
    LIMIT 1
)
WHERE cp2.phase_number = 2
AND cp2.parent_checkpoint_id IS NULL;

-- Update Phase 3 checkpoints to point to their Phase 2 parent
UPDATE video_checkpoints AS cp3
SET parent_checkpoint_id = (
    SELECT cp2.id
    FROM video_checkpoints AS cp2
    WHERE cp2.video_id = cp3.video_id
    AND cp2.phase_number = 2
    AND cp2.created_at < cp3.created_at
    AND cp2.branch_name = cp3.branch_name
    ORDER BY cp2.created_at DESC
    LIMIT 1
)
WHERE cp3.phase_number = 3
AND cp3.parent_checkpoint_id IS NULL;

-- Update Phase 4 checkpoints to point to their Phase 3 parent (if any exist)
UPDATE video_checkpoints AS cp4
SET parent_checkpoint_id = (
    SELECT cp3.id
    FROM video_checkpoints AS cp3
    WHERE cp3.video_id = cp4.video_id
    AND cp3.phase_number = 3
    AND cp3.created_at < cp4.created_at
    AND cp3.branch_name = cp4.branch_name
    ORDER BY cp3.created_at DESC
    LIMIT 1
)
WHERE cp4.phase_number = 4
AND cp4.parent_checkpoint_id IS NULL;
