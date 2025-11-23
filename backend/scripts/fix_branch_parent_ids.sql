-- Fix incorrectly set parent_checkpoint_id values for branched Phase 1 checkpoints
--
-- Problem: When editing an approved Phase 1 checkpoint to create a new branch,
-- the new Phase 1 checkpoint was incorrectly getting parent_checkpoint_id set to
-- the checkpoint it branched from, instead of inheriting that checkpoint's parent_checkpoint_id.
--
-- Example:
--   main (Phase 1, parent=null) was edited to create:
--   main-1 (Phase 1, parent=main) <-- WRONG! Should be parent=null
--
-- Fix: Set parent_checkpoint_id to null for Phase 1 checkpoints that have another
-- Phase 1 checkpoint as their parent (these are branches, not children)

-- First, let's see what needs to be fixed
SELECT
    cp1.id as checkpoint_id,
    cp1.branch_name,
    cp1.phase_number,
    cp1.parent_checkpoint_id,
    cp2.branch_name as parent_branch,
    cp2.phase_number as parent_phase
FROM video_checkpoints cp1
LEFT JOIN video_checkpoints cp2 ON cp1.parent_checkpoint_id = cp2.id
WHERE cp1.phase_number = 1
  AND cp2.phase_number = 1;

-- Now fix them: Phase 1 checkpoints should inherit their parent's parent_checkpoint_id
UPDATE video_checkpoints cp1
SET parent_checkpoint_id = cp2.parent_checkpoint_id
FROM video_checkpoints cp2
WHERE cp1.parent_checkpoint_id = cp2.id
  AND cp1.phase_number = 1
  AND cp2.phase_number = 1;

-- Verify the fix
SELECT
    cp1.id as checkpoint_id,
    cp1.branch_name,
    cp1.phase_number,
    cp1.parent_checkpoint_id
FROM video_checkpoints cp1
WHERE cp1.phase_number = 1
ORDER BY cp1.created_at;
