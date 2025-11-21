# Checkpoint Feature Implementation Plan

**Date**: 2025-11-20T23:46:55-06:00
**Author**: lousydropout
**Git Commit**: dc35ffbb8a886cf2e40f8faddca7f25e126de6e1
**Branch**: main
**Related Research**: `thoughts/shared/research/2025-11-20-checkpoint-feature-analysis.md`
**Feature Specification**: `feature.md`

## Overview

Implement checkpoint functionality for the AI Video generation pipeline to enable:
- Pausing after each of the 4 pipeline phases
- Storing intermediate artifacts in S3 with versioning
- Tracking checkpoint metadata in database
- User review and editing of artifacts at each checkpoint
- Branching support (tree structure for exploring different creative directions)
- "YOLO mode" for auto-continuing without pauses (backward compatible behavior)

## Current State Analysis

**Pipeline Architecture**:
- 4 sequential phases: Planning (Phase 1) → Storyboard (Phase 2) → Chunks (Phase 3) → Refinement (Phase 4)
- Celery chain executes continuously without pausing (`backend/app/orchestrator/pipeline.py:83-95`)
- All artifacts already stored in S3 with user-scoped paths
- Phase outputs tracked in `VideoGeneration.phase_outputs` JSON column
- Progress tracking via Redis + PostgreSQL

**Key Constraints**:
- Celery chains don't support mid-execution pausing
- Must maintain same code path for YOLO and manual modes
- Avoid copying unchanged artifacts when branching
- Support individual artifact regeneration (beats, chunks)

## Desired End State

**After implementation**:
- Pipeline pauses after each phase completion
- User reviews artifacts via frontend, makes edits if desired
- Explicit POST `/api/video/{id}/continue` required to proceed
- Editing artifacts creates new branch (tree of possibilities)
- All artifacts tracked individually in database with versioning
- S3 paths: `{user_id}/videos/{video_id}/beat_00_v1.png`, `beat_00_v2.png`, etc.
- Database tracks checkpoint tree with parent-child relationships
- YOLO mode (`auto_continue: true`) auto-approves and runs straight through

**Verification**:
1. Generate video with `auto_continue: false` → pauses at Phase 1
2. Edit spec → continue → new branch created (main-1)
3. Phase 2 runs on new branch, pauses
4. Regenerate beat 3 → creates beat_03_v2.png
5. Continue → new branch created (main-1-1)
6. Database shows tree structure with 3 branches
7. Generate video with `auto_continue: true` → runs to completion without pausing

## What We're NOT Doing

- ❌ Backward compatibility with existing videos (ignore pre-checkpoint videos)
- ❌ Rollback/undo to previous checkpoints (only forward branching)
- ❌ Migration down scripts (only up migrations)
- ❌ SQLAlchemy ORM (using raw SQL with psycopg2)
- ❌ S3 native versioning (application-level versioning instead)
- ❌ User-provided branch names (auto-generated: main, main-1, main-1-1)
- ❌ Concurrent branch processing (sequential execution only)
- ❌ Checkpoint garbage collection in Phase 1 (implement later if needed)

## Implementation Approach

**Core Strategy**:
1. Break Celery chain - dispatch only Phase 1, subsequent phases via API
2. Each phase creates checkpoint record and artifacts, then pauses
3. User approval via POST triggers next phase dispatch with branch context
4. Artifact-level tracking in database avoids S3 file copying
5. Branch naming: parent + counter (main → main-1, main-1 → main-1-1)
6. YOLO mode reuses same code path, just auto-approves checkpoints

**Design Decisions**:
- **Database**: Separate `video_checkpoints` and `checkpoint_artifacts` tables
- **S3 Paths**: Semantic + version (`beat_00_v1.png`, `beat_00_v2.png`)
- **Versioning**: Auto-increment (v1, v2, v3) with timestamps in database
- **Branching**: New branch created when continuing from edited checkpoint
- **Testing**: Mock AI services for unit tests, one real integration test for smoke testing

---

## Phase 1: Database Schema & Models

### Overview
Create database tables for checkpoint tracking and artifact versioning. Add raw SQL query functions for checkpoint operations.

### Changes Required

#### 1. Create Migration

**File**: `backend/migrations/004_add_checkpoints.sql` (new)

```sql
-- Add new video status values for checkpoint pausing
ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE1';
ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE2';
ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE3';
ALTER TYPE videostatus ADD VALUE IF NOT EXISTS 'PAUSED_AT_PHASE4';

-- Add auto_continue flag to video_generations
ALTER TABLE video_generations
ADD COLUMN auto_continue BOOLEAN DEFAULT FALSE;

-- Create video_checkpoints table
CREATE TABLE video_checkpoints (
    id VARCHAR PRIMARY KEY,
    video_id VARCHAR NOT NULL REFERENCES video_generations(id) ON DELETE CASCADE,
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
    UNIQUE(video_id, branch_name, phase_number, version)
);

-- Create checkpoint_artifacts table
CREATE TABLE checkpoint_artifacts (
    id VARCHAR PRIMARY KEY,
    checkpoint_id VARCHAR NOT NULL REFERENCES video_checkpoints(id) ON DELETE CASCADE,

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
    UNIQUE(checkpoint_id, artifact_type, artifact_key)
);

-- Indexes for performance
CREATE INDEX idx_checkpoints_video ON video_checkpoints(video_id);
CREATE INDEX idx_checkpoints_branch ON video_checkpoints(video_id, branch_name);
CREATE INDEX idx_checkpoints_parent ON video_checkpoints(parent_checkpoint_id);
CREATE INDEX idx_checkpoints_status ON video_checkpoints(status);

CREATE INDEX idx_artifacts_checkpoint ON checkpoint_artifacts(checkpoint_id);
CREATE INDEX idx_artifacts_type ON checkpoint_artifacts(artifact_type);
CREATE INDEX idx_artifacts_parent ON checkpoint_artifacts(parent_artifact_id);
```

#### 2. Create Checkpoint Query Functions

**File**: `backend/app/database/checkpoint_queries.py` (new)

Implement raw SQL query functions:
- `create_checkpoint()` - Create checkpoint record, returns checkpoint_id
- `get_checkpoint(checkpoint_id)` - Retrieve checkpoint by ID
- `list_checkpoints(video_id, branch_name)` - List checkpoints, optionally filtered
- `approve_checkpoint(checkpoint_id)` - Set approved_at timestamp
- `get_checkpoint_tree(video_id)` - Recursive query for tree structure
- `get_current_checkpoint(video_id)` - Most recent pending checkpoint
- `get_leaf_checkpoints(video_id)` - Checkpoints with no children (active branches)
- `create_artifact()` - Create artifact record, returns artifact_id
- `get_checkpoint_artifacts(checkpoint_id)` - All artifacts for checkpoint
- `get_latest_artifact_version()` - Latest version of specific artifact
- `get_latest_artifacts_for_checkpoint()` - Latest version of each artifact (handles mixed versions)
- `get_next_version_number()` - Calculate next version for phase/branch
- `generate_branch_name(parent_branch)` - Generate branch name (parent-1, parent-2)
- `has_checkpoint_been_edited()` - Check if any artifact version > 1
- `create_branch_from_checkpoint()` - Create new branch when continuing from edit
- `build_checkpoint_tree()` - Build tree structure from flat list
- `update_checkpoint_phase_output()` - Update checkpoint's phase_output field

**Connection Management**: Use SQLAlchemy engine from `app.database.SessionLocal()` for connection pooling, but execute raw SQL queries instead of ORM.

#### 3. Update Models Enum

**File**: `backend/app/common/models.py`

**Lines 6-16** (VideoStatus enum):
```python
class VideoStatus(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    PAUSED_AT_PHASE1 = "paused_at_phase1"  # NEW
    GENERATING_STORYBOARD = "generating_storyboard"
    PAUSED_AT_PHASE2 = "paused_at_phase2"  # NEW
    GENERATING_CHUNKS = "generating_chunks"
    PAUSED_AT_PHASE3 = "paused_at_phase3"  # NEW
    REFINING = "refining"
    PAUSED_AT_PHASE4 = "paused_at_phase4"  # NEW
    COMPLETE = "complete"
    FAILED = "failed"
```

#### 4. Create Tests

**File**: `backend/tests/test_checkpoints_db.py` (new)

Test cases:
- `test_migration_applies()` - Verify migration runs without errors
- `test_checkpoint_table_exists()` - Check table and columns created
- `test_artifact_table_exists()` - Check table and columns created
- `test_create_checkpoint()` - Test checkpoint creation
- `test_create_artifact()` - Test artifact creation
- `test_get_checkpoint()` - Test retrieval by ID
- `test_list_checkpoints_by_branch()` - Test filtering
- `test_checkpoint_tree_query()` - Test recursive CTE returns tree
- `test_approve_checkpoint()` - Test approved_at timestamp
- `test_next_version_number()` - Test v1, v2, v3 calculation
- `test_branch_name_generation()` - Test main → main-1 → main-1-1
- `test_foreign_key_constraints()` - Test cascading deletes
- `test_get_current_checkpoint()` - Test most recent pending query
- `test_get_leaf_checkpoints()` - Test finding checkpoints with no children
- `test_latest_artifacts_mixed_versions()` - Test DISTINCT ON query

### Success Criteria

#### Automated Verification (Required):
- [x] Migration runs successfully: `python migrate.py up`
- [x] Tables exist in database: Query `information_schema.tables WHERE table_name IN ('video_checkpoints', 'checkpoint_artifacts')`
- [x] All columns created correctly: Query `information_schema.columns` for both tables
- [x] Indexes created: Query `pg_indexes WHERE tablename IN ('video_checkpoints', 'checkpoint_artifacts')` returns 7 indexes
- [x] All unit tests pass: `pytest backend/tests/test_checkpoints_db.py -v`
- [x] Foreign keys enforced: Test inserting invalid checkpoint_id (should fail)
- [x] Check constraints enforced: Test inserting phase_number=5 (should fail)
- [x] Unique constraints work: Test duplicate (video_id, branch, phase, version) (should fail)

#### Manual Verification (Optional):
- [ ] Inspect database schema in psql matches design
- [ ] Run EXPLAIN ANALYZE on tree query to verify index usage

---

## Phase 2: Checkpoint Creation Logic

### Overview
Modify each phase task to create checkpoint records and artifacts. Remove Celery chain and implement pause mechanism. Upload artifacts to S3 with versioned paths.

### Changes Required

#### 1. Update Pipeline Orchestrator

**File**: `backend/app/orchestrator/pipeline.py`

**Lines 83-95** (remove chain):
```python
# OLD: Celery chain
workflow = chain(
    plan_video_intelligent.s(video_id, prompt),
    generate_storyboard.s(user_id),
    generate_chunks.s(user_id, model),
    refine_video.s(user_id)
)
result = workflow.apply_async()

# NEW: Dispatch only Phase 1
plan_video_intelligent.delay(video_id, prompt)
# Subsequent phases dispatched via POST /api/video/{id}/continue
```

**Add helper functions**:
```python
def get_auto_continue_flag(video_id: str) -> bool:
    """Check if video has auto_continue enabled (YOLO mode)."""
    video = get_video_from_db(video_id)
    return video.auto_continue

def dispatch_next_phase(video_id: str, checkpoint_id: str):
    """
    Dispatch the next phase based on current checkpoint.
    Used by both manual continue and YOLO auto-continue.
    """
    checkpoint = get_checkpoint(checkpoint_id)
    phase_output = checkpoint['phase_output']

    if checkpoint['phase_number'] == 1:
        generate_storyboard.delay(phase_output, checkpoint['user_id'])
    elif checkpoint['phase_number'] == 2:
        generate_chunks.delay(phase_output, checkpoint['user_id'], video_id)
    elif checkpoint['phase_number'] == 3:
        refine_video.delay(phase_output, checkpoint['user_id'])
    # Phase 4 is terminal (no next phase)
```

#### 2. Update PhaseOutput Schema

**File**: `backend/app/common/schemas.py`

**Lines 12-20** (add checkpoint_id field):
```python
class PhaseOutput(BaseModel):
    video_id: str
    phase: str
    status: str
    output_data: Dict
    cost_usd: float
    duration_seconds: float
    error_message: Optional[str] = None
    checkpoint_id: Optional[str] = None  # NEW: ID of checkpoint created by this phase
```

#### 3. Modify Phase 1 Task

**File**: `backend/app/phases/phase1_validate/task.py`

**Lines 118-126** (end of task - replace return with checkpoint creation):
```python
# Build PhaseOutput as before
output = PhaseOutput(
    video_id=video_id,
    phase="phase1_planning",
    status="success",
    output_data={"spec": spec},
    cost_usd=cost,
    duration_seconds=duration
)

# Create checkpoint
checkpoint_id = create_checkpoint(
    video_id=video_id,
    branch_name='main',  # Always start on main branch
    phase_number=1,
    version=1,  # First version
    phase_output=output.dict(),
    cost_usd=cost,
    user_id=user_id,
    parent_checkpoint_id=None  # Root checkpoint
)

# Create artifact for spec (stored in DB, not S3)
artifact_id = create_artifact(
    checkpoint_id=checkpoint_id,
    artifact_type='spec',
    artifact_key='spec',
    s3_url='',  # Spec stored in DB
    s3_key='',
    version=1,
    metadata={'spec': spec}
)

# Add checkpoint_id to output
output.checkpoint_id = checkpoint_id

# Update video status to paused
video = get_video_from_db(video_id)
video.status = VideoStatus.PAUSED_AT_PHASE1
video.current_phase = 'phase1'
video.phase_outputs['phase1_planning'] = output.dict()
db.commit()

# Update progress
update_progress(
    video_id,
    status='paused_at_phase1',
    current_phase='phase1',
    checkpoint_id=checkpoint_id,
    phase_outputs=video.phase_outputs
)

# Check YOLO mode
if get_auto_continue_flag(video_id):
    approve_checkpoint(checkpoint_id)
    dispatch_next_phase(video_id, checkpoint_id)

return output.dict()
```

#### 4. Modify Phase 2 Task

**File**: `backend/app/phases/phase2_storyboard/task.py`

**Add at beginning**:
```python
def generate_storyboard(phase1_output, user_id):
    # Extract branch context from Phase 1 output
    branch_name = phase1_output.get('_branch_name', 'main')
    parent_checkpoint_id = phase1_output.get('checkpoint_id')
    version = phase1_output.get('_version', 1)

    # ... existing storyboard generation logic ...
```

**Lines 121-126** (upload images with new S3 path):
```python
# Upload images to S3 with versioned paths
for i, beat_image in enumerate(storyboard_images):
    s3_key = f"{user_id}/videos/{video_id}/beat_{i:02d}_v{version}.png"
    s3_url = s3_client.upload_file(temp_path, s3_key)
    beat_image['image_url'] = s3_url
```

**Lines 147-168** (replace with checkpoint creation):
```python
# Create checkpoint
checkpoint_id = create_checkpoint(
    video_id=video_id,
    branch_name=branch_name,
    phase_number=2,
    version=version,
    phase_output=output.dict(),
    cost_usd=total_cost,
    user_id=user_id,
    parent_checkpoint_id=parent_checkpoint_id
)

# Create artifacts for each beat image
for i, beat_image in enumerate(storyboard_images):
    create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='beat_image',
        artifact_key=f'beat_{i}',
        s3_url=beat_image['image_url'],
        s3_key=f"{user_id}/videos/{video_id}/beat_{i:02d}_v{version}.png",
        version=version,
        metadata={
            'beat_id': beat_image['beat_id'],
            'prompt_used': beat_image['prompt_used'],
            'shot_type': beat_image['shot_type']
        }
    )

# Add checkpoint_id to output
output.checkpoint_id = checkpoint_id

# Update video status to paused
video.status = VideoStatus.PAUSED_AT_PHASE2
video.current_phase = 'phase2'
db.commit()

# Update progress
update_progress(video_id, status='paused_at_phase2', checkpoint_id=checkpoint_id)

# YOLO mode check
if get_auto_continue_flag(video_id):
    approve_checkpoint(checkpoint_id)
    dispatch_next_phase(video_id, checkpoint_id)

return output.dict()
```

#### 5. Modify Phase 3 Task

**File**: `backend/app/phases/phase3_chunks/task.py`

Similar pattern to Phase 2:
- Extract branch context from phase2_output
- Upload chunks to S3: `{user_id}/videos/{video_id}/chunk_{i:02d}_v{version}.mp4`
- Upload stitched video: `{user_id}/videos/{video_id}/stitched_v{version}.mp4`
- Create checkpoint for Phase 3
- Create artifacts for each chunk + stitched video
- Pause at PAUSED_AT_PHASE3
- YOLO mode auto-approval

#### 6. Modify Phase 4 Task

**File**: `backend/app/phases/phase4_refine/task.py`

Similar pattern:
- Extract branch context from phase3_output
- Upload final video: `{user_id}/videos/{video_id}/final_v{version}.mp4`
- Upload music: `{user_id}/videos/{video_id}/music_v{version}.mp3`
- Create checkpoint for Phase 4
- Create artifacts for final video + music
- Phase 4 is terminal - mark as COMPLETE instead of PAUSED
- Auto-approve final checkpoint (even in manual mode)

#### 7. Create Test Mocks

**File**: `backend/tests/mocks/ai_services.py` (new)

```python
"""Mock AI services for testing checkpoint creation."""

def mock_gpt4_response():
    """Return a valid spec structure."""
    return {
        "template": "luxury_showcase",
        "duration": 30,
        "beats": [
            {"beat_id": "hero_shot", "duration": 10},
            {"beat_id": "detail_showcase", "duration": 10},
            {"beat_id": "call_to_action", "duration": 10}
        ],
        "style": {"mood": "luxury"},
        "product": {"category": "watch"},
        "audio": {"music_style": "cinematic"}
    }

def mock_flux_image():
    """Return a dummy image URL."""
    return "https://replicate.delivery/mock-image.png"

def mock_hailuo_video():
    """Return a dummy video URL."""
    return "https://replicate.delivery/mock-video.mp4"
```

#### 8. Create Integration Tests

**File**: `backend/tests/test_checkpoint_creation.py` (new)

Test cases:
- `test_phase1_creates_checkpoint()` - Verify Phase 1 creates checkpoint and pauses
- `test_phase1_creates_spec_artifact()` - Verify spec artifact created
- `test_phase2_creates_checkpoint_with_images()` - Verify beat artifacts created
- `test_s3_paths_versioned()` - Verify S3 keys match `beat_00_v1.png` pattern
- `test_video_status_paused()` - Verify status updated correctly
- `test_yolo_mode_auto_continues()` - Verify auto-approval and dispatch
- `test_phase_chain_broken()` - Verify Phase 2 not auto-dispatched in manual mode
- `test_checkpoint_id_in_phase_output()` - Verify checkpoint_id passed to next phase

**Use mocks for AI services to avoid costs.**

### Success Criteria

#### Automated Verification (Required):
- [ ] Phase 1 task creates checkpoint: `test_phase1_creates_checkpoint` passes
- [ ] Phase 1 creates spec artifact: Query `checkpoint_artifacts` table
- [ ] Phase 2 creates checkpoint with beat artifacts: `test_phase2_creates_checkpoint_with_images` passes
- [ ] S3 artifacts uploaded with correct paths: Mock S3 upload, verify key matches `{user_id}/videos/{video_id}/beat_00_v1.png`
- [ ] Video status updated to PAUSED_AT_PHASE*: Query `video_generations.status`
- [ ] YOLO mode auto-approves: `test_yolo_mode_auto_continues` passes
- [ ] Phase tasks don't dispatch next phase in manual mode: `test_phase_chain_broken` passes
- [ ] checkpoint_id passed in PhaseOutput: `test_checkpoint_id_in_phase_output` passes
- [ ] All unit tests pass: `pytest backend/tests/test_checkpoint_creation.py -v`

#### Manual Verification (Prompt user to confirm):
```
Phase 2 automated tests passed. Before continuing to Phase 3:

Optional manual test:
1. Run a real video generation (not mocked):
   POST /api/generate {"prompt": "luxury watch", "auto_continue": false}

2. Verify in database:
   SELECT * FROM video_checkpoints WHERE video_id = '{video_id}';
   - Should see 1 checkpoint at phase 1, status 'pending'

   SELECT * FROM checkpoint_artifacts WHERE checkpoint_id = '{checkpoint_id}';
   - Should see 1 artifact (spec)

3. Verify video status:
   SELECT status FROM video_generations WHERE id = '{video_id}';
   - Should be 'paused_at_phase1'

Cost estimate: ~$0.02 (GPT-4 call only)

Should I continue to Phase 3 implementation, or would you like to:
a) Run this test yourself first?
b) Skip manual verification and proceed?
```

---

## Phase 3: Checkpoint API Endpoints

### Overview
Create REST API endpoints for listing checkpoints, getting checkpoint details, and continuing pipeline. Implement tree structure building and branch listing.

### Changes Required

#### 1. Create Checkpoint Router

**File**: `backend/app/api/checkpoints.py` (new)

Implement endpoints:

**GET `/api/video/{video_id}/checkpoints`**
- List all checkpoints for a video
- Optional query param: `?branch={name}` to filter
- Returns tree structure with parent-child relationships
- Auth: Verify user owns video

**GET `/api/video/{video_id}/checkpoints/{checkpoint_id}`**
- Get detailed checkpoint information
- Includes all artifacts with presigned S3 URLs
- Returns checkpoint + artifacts
- Auth: Verify user owns video

**GET `/api/video/{video_id}/checkpoints/current`**
- Get the current pending checkpoint (most recent unapproved)
- Returns checkpoint with artifacts
- Auth: Verify user owns video

**GET `/api/video/{video_id}/branches`**
- List all active branches (leaf checkpoints)
- Groups by branch name
- Returns list with latest checkpoint per branch
- Auth: Verify user owns video

**POST `/api/video/{video_id}/continue`**
- Approve checkpoint and continue to next phase
- Request body: `{"checkpoint_id": "cp-123"}`
- Checks if checkpoint has been edited (artifacts versioned)
- If edited: creates new branch name
- Approves checkpoint (sets approved_at)
- Dispatches next phase with branch context
- Returns: `{"next_phase": 2, "branch_name": "main-1", "created_new_branch": true}`
- Auth: Verify user owns video

#### 2. Create Request/Response Schemas

**File**: `backend/app/common/schemas.py` (add to existing)

```python
class CheckpointResponse(BaseModel):
    id: str
    video_id: str
    branch_name: str
    phase_number: int
    version: int
    status: str
    approved_at: Optional[datetime]
    created_at: datetime
    cost_usd: float
    parent_checkpoint_id: Optional[str]
    artifacts: List[ArtifactResponse]

class ArtifactResponse(BaseModel):
    id: str
    artifact_type: str
    artifact_key: str
    s3_url: str
    version: int
    metadata: Optional[Dict]
    created_at: datetime

class CheckpointTreeResponse(BaseModel):
    checkpoint: CheckpointResponse
    children: List['CheckpointTreeResponse']  # Recursive

class ContinueRequest(BaseModel):
    checkpoint_id: str

class BranchResponse(BaseModel):
    branch_name: str
    latest_checkpoint: CheckpointResponse
    phase_number: int
    can_continue: bool  # True if pending, False if approved
```

#### 3. Register Router

**File**: `backend/app/main.py`

```python
from app.api import checkpoints

app.include_router(checkpoints.router, prefix="/api", tags=["checkpoints"])
```

#### 4. Implement Continue Endpoint with Branching Logic

**File**: `backend/app/api/checkpoints.py`

```python
@router.post("/video/{video_id}/continue")
async def continue_pipeline(
    video_id: str,
    request: ContinueRequest,
    current_user: dict = Depends(get_current_user)
):
    checkpoint = get_checkpoint(request.checkpoint_id)

    # Verify ownership
    if checkpoint['user_id'] != current_user['uid']:
        raise HTTPException(403, "Not authorized")

    # Check if checkpoint has been edited
    has_edits = has_checkpoint_been_edited(request.checkpoint_id)

    # Determine branch for next phase
    if has_edits:
        # Create new branch: main → main-1, main-1 → main-1-1
        next_branch = create_branch_from_checkpoint(
            request.checkpoint_id,
            current_user['uid']
        )
    else:
        # Continue on same branch
        next_branch = checkpoint['branch_name']

    # Approve this checkpoint
    approve_checkpoint(request.checkpoint_id)

    # Get phase output to pass to next phase
    phase_output = checkpoint['phase_output']

    # Add branch context for next phase (passed via PhaseOutput)
    phase_output['_branch_name'] = next_branch
    phase_output['_parent_checkpoint_id'] = request.checkpoint_id
    phase_output['_version'] = 1  # First version on new/same branch

    # Dispatch appropriate phase
    next_phase_number = checkpoint['phase_number'] + 1

    if next_phase_number > 4:
        raise HTTPException(400, "Already at final phase")

    if next_phase_number == 2:
        generate_storyboard.delay(phase_output, current_user['uid'])
    elif next_phase_number == 3:
        generate_chunks.delay(phase_output, current_user['uid'], video_id)
    elif next_phase_number == 4:
        refine_video.delay(phase_output, current_user['uid'])

    # Update video status
    video = get_video_from_db(video_id)
    status_map = {
        2: VideoStatus.GENERATING_STORYBOARD,
        3: VideoStatus.GENERATING_CHUNKS,
        4: VideoStatus.REFINING
    }
    video.status = status_map[next_phase_number]
    db.commit()

    return {
        "message": "Pipeline continued",
        "next_phase": next_phase_number,
        "branch_name": next_branch,
        "created_new_branch": has_edits
    }
```

#### 5. Create API Tests

**File**: `backend/tests/test_checkpoint_api.py` (new)

Test cases:
- `test_list_checkpoints()` - Verify GET /checkpoints returns tree structure
- `test_get_checkpoint_details()` - Verify GET /checkpoints/{id} returns artifacts
- `test_continue_creates_next_checkpoint()` - Verify POST /continue dispatches next phase
- `test_continue_requires_auth()` - Verify 401 without auth
- `test_continue_wrong_user()` - Verify 403 for other user's video
- `test_get_current_checkpoint()` - Verify GET /current returns latest pending
- `test_list_active_branches()` - Verify GET /branches groups by branch
- `test_continue_with_edits_creates_branch()` - Verify new branch when edited
- `test_continue_without_edits_same_branch()` - Verify same branch when not edited

### Success Criteria

#### Automated Verification (Required):
- [ ] All endpoints return 200 for valid requests: API tests pass
- [ ] Tree structure correctly built: Create 3-level tree, verify structure
- [ ] Authentication enforced: Test without auth token returns 401
- [ ] User isolation enforced: User A can't access user B's checkpoints (403)
- [ ] Continue endpoint dispatches Celery task: Mock `.delay()`, verify called
- [ ] Current checkpoint query returns correct checkpoint: Create 2, verify latest returned
- [ ] Branch listing groups by branch name: Create multiple branches, verify grouping
- [ ] Continue with edits creates new branch: Edit artifact, continue, verify branch_name changed
- [ ] All API tests pass: `pytest backend/tests/test_checkpoint_api.py -v`

#### Manual Verification (Prompt user):
```
Phase 3 automated tests passed. Before continuing to Phase 4:

Optional manual test:
1. Generate video and pause at Phase 1
2. GET /api/video/{id}/checkpoints
   - Verify returns tree structure with 1 checkpoint
3. GET /api/video/{id}/checkpoints/current
   - Verify returns Phase 1 checkpoint
4. POST /api/video/{id}/continue {"checkpoint_id": "..."}
   - Verify returns {"next_phase": 2, "branch_name": "main", "created_new_branch": false}
5. Wait for Phase 2 to complete
6. Verify database:
   SELECT * FROM video_checkpoints WHERE video_id = '{id}' ORDER BY created_at;
   - Should see 2 checkpoints (Phase 1 approved, Phase 2 pending)
   - Phase 2 checkpoint has parent_checkpoint_id = Phase 1 checkpoint_id

Should I continue to Phase 4, or would you like to test this manually first?
```

---

## Phase 4: Artifact Editing & Branching

### Overview
Implement endpoints for editing artifacts at each checkpoint: edit spec (Phase 1), upload/regenerate images (Phase 2), regenerate chunks (Phase 3). Implement branch creation logic when continuing from edited checkpoints.

### Changes Required

#### 1. Add Edit Endpoints

**File**: `backend/app/api/checkpoints.py` (add to existing router)

**PATCH `/api/video/{video_id}/checkpoints/{checkpoint_id}/spec`**
- Edit Phase 1 spec (beats, style, product, audio)
- Request body: `{"beats": [...], "style": {...}}` (partial updates)
- Merges with existing spec
- Creates new artifact version (v2, v3, etc.)
- Updates checkpoint's phase_output
- Returns: `{"artifact_id": "...", "version": 2}`

**POST `/api/video/{video_id}/checkpoints/{checkpoint_id}/upload-image`**
- Upload replacement image for specific beat at Phase 2
- Request: multipart/form-data with `beat_index` and `image` file
- Uploads to S3: `beat_{index}_v{next_version}.png`
- Creates new artifact version pointing to parent
- Returns: `{"artifact_id": "...", "s3_url": "...", "version": 2}`

**POST `/api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-beat`**
- Regenerate specific beat image at Phase 2 using FLUX
- Request body: `{"beat_index": 3, "prompt_override": "optional new prompt"}`
- Calls FLUX to generate new image
- Uploads to S3 with next version number
- Creates new artifact version
- Returns: `{"artifact_id": "...", "s3_url": "...", "version": 2}`

**POST `/api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-chunk`**
- Regenerate specific video chunk at Phase 3
- Request body: `{"chunk_index": 5, "model_override": "kling"}`
- Calls video generation model (hailuo/kling/veo)
- Uploads to S3 with next version number
- Creates new artifact version
- Returns: `{"artifact_id": "...", "s3_url": "...", "version": 2}`

#### 2. Add Request Schemas

**File**: `backend/app/common/schemas.py` (add to existing)

```python
class SpecEditRequest(BaseModel):
    beats: Optional[List[Dict]] = None
    style: Optional[Dict] = None
    product: Optional[Dict] = None
    audio: Optional[Dict] = None
    # Only provided fields will be updated

class RegenerateBeatRequest(BaseModel):
    beat_index: int
    prompt_override: Optional[str] = None

class RegenerateChunkRequest(BaseModel):
    chunk_index: int
    model_override: Optional[str] = None  # 'hailuo', 'kling', 'veo'
```

#### 3. Implement Edit Spec Endpoint

**File**: `backend/app/api/checkpoints.py`

```python
@router.patch("/video/{video_id}/checkpoints/{checkpoint_id}/spec")
async def edit_spec(
    video_id: str,
    checkpoint_id: str,
    spec_edits: SpecEditRequest,
    current_user: dict = Depends(get_current_user)
):
    # Verify ownership and checkpoint is Phase 1
    checkpoint = get_checkpoint(checkpoint_id)
    if checkpoint['phase_number'] != 1:
        raise HTTPException(400, "Can only edit spec at Phase 1")

    # Get current spec artifact
    current_spec = get_latest_artifact_version(
        checkpoint_id, 'spec', 'spec'
    )

    # Apply edits (merge with existing)
    updated_spec = {
        **current_spec['metadata']['spec'],
        **spec_edits.dict(exclude_unset=True)
    }

    # Get next version number
    next_version = get_next_version_number(
        video_id, checkpoint['branch_name'], phase_number=1
    )

    # Create new artifact version
    new_artifact_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='spec',
        artifact_key='spec',
        s3_url='',
        s3_key='',
        version=next_version,
        metadata={'spec': updated_spec},
        parent_artifact_id=current_spec['id']
    )

    # Update checkpoint's phase_output
    update_checkpoint_phase_output(checkpoint_id, {'spec': updated_spec})

    return {"artifact_id": new_artifact_id, "version": next_version}
```

#### 4. Implement Upload Image Endpoint

**File**: `backend/app/api/checkpoints.py`

```python
@router.post("/video/{video_id}/checkpoints/{checkpoint_id}/upload-image")
async def upload_replacement_image(
    video_id: str,
    checkpoint_id: str,
    beat_index: int = Form(...),
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    # Verify checkpoint is Phase 2
    checkpoint = get_checkpoint(checkpoint_id)
    if checkpoint['phase_number'] != 2:
        raise HTTPException(400, "Can only upload images at Phase 2")

    # Validate beat_index
    spec = checkpoint['phase_output']['output_data']['spec']
    if beat_index >= len(spec['beats']):
        raise HTTPException(400, f"Beat index {beat_index} out of range")

    # Save uploaded file temporarily
    temp_path = f"/tmp/{uuid.uuid4()}.png"
    with open(temp_path, 'wb') as f:
        f.write(await image.read())

    # Get next version
    next_version = get_next_version_number(
        video_id, checkpoint['branch_name'], phase_number=2
    )

    # Upload to S3 with versioned path
    s3_key = f"{current_user['uid']}/videos/{video_id}/beat_{beat_index:02d}_v{next_version}.png"
    s3_url = s3_client.upload_file(temp_path, s3_key)

    # Get parent artifact (previous version)
    parent_artifact = get_latest_artifact_version(
        checkpoint_id, 'beat_image', f'beat_{beat_index}'
    )

    # Create new artifact version
    new_artifact_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='beat_image',
        artifact_key=f'beat_{beat_index}',
        s3_url=s3_url,
        s3_key=s3_key,
        version=next_version,
        metadata={
            'beat_id': spec['beats'][beat_index]['beat_id'],
            'uploaded_by_user': True
        },
        parent_artifact_id=parent_artifact['id'] if parent_artifact else None
    )

    os.remove(temp_path)

    return {"artifact_id": new_artifact_id, "s3_url": s3_url, "version": next_version}
```

#### 5. Implement Regenerate Beat Endpoint

**File**: `backend/app/api/checkpoints.py`

```python
@router.post("/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-beat")
async def regenerate_beat(
    video_id: str,
    checkpoint_id: str,
    request: RegenerateBeatRequest,
    current_user: dict = Depends(get_current_user)
):
    # Verify checkpoint is Phase 2
    checkpoint = get_checkpoint(checkpoint_id)
    if checkpoint['phase_number'] != 2:
        raise HTTPException(400, "Can only regenerate beats at Phase 2")

    # Get spec and beat
    spec = checkpoint['phase_output']['output_data']['spec']
    beat = spec['beats'][request.beat_index]

    # Use override prompt or original
    prompt = request.prompt_override or beat.get('prompt_template', '')

    # Call FLUX to regenerate image
    from app.phases.phase2_storyboard.image_generation import generate_beat_image

    new_beat_image = generate_beat_image(
        video_id=video_id,
        beat_index=request.beat_index,
        beat=beat,
        style=spec['style'],
        product=spec['product'],
        user_id=current_user['uid']
    )

    # Get next version
    next_version = get_next_version_number(
        video_id, checkpoint['branch_name'], phase_number=2
    )

    # Upload to S3
    s3_key = f"{current_user['uid']}/videos/{video_id}/beat_{request.beat_index:02d}_v{next_version}.png"
    s3_url = s3_client.upload_file(new_beat_image['temp_path'], s3_key)

    # Get parent artifact
    parent_artifact = get_latest_artifact_version(
        checkpoint_id, 'beat_image', f'beat_{request.beat_index}'
    )

    # Create new artifact
    new_artifact_id = create_artifact(
        checkpoint_id=checkpoint_id,
        artifact_type='beat_image',
        artifact_key=f'beat_{request.beat_index}',
        s3_url=s3_url,
        s3_key=s3_key,
        version=next_version,
        metadata={
            'beat_id': beat['beat_id'],
            'prompt_used': prompt,
            'regenerated': True
        },
        parent_artifact_id=parent_artifact['id']
    )

    return {"artifact_id": new_artifact_id, "s3_url": s3_url, "version": next_version}
```

#### 6. Implement Regenerate Chunk Endpoint

**File**: `backend/app/api/checkpoints.py`

Similar to regenerate beat:
- Verify checkpoint is Phase 3
- Extract spec and chunk info
- Determine if reference or continuous chunk
- Call appropriate chunk generation function
- Upload to S3 with versioned path
- Create new artifact version

#### 7. Update Continue Endpoint

**Already implemented in Phase 3** - continue endpoint checks `has_checkpoint_been_edited()` and creates new branch if artifacts were modified.

#### 8. Create Tests

**File**: `backend/tests/test_artifact_editing.py` (new)

Test cases:
- `test_edit_spec_creates_new_version()` - PATCH /spec creates v2 artifact
- `test_upload_image_replaces_beat()` - POST /upload-image creates new artifact
- `test_regenerate_beat_calls_flux()` - POST /regenerate-beat calls FLUX (mocked)
- `test_regenerate_chunk_calls_hailuo()` - POST /regenerate-chunk calls video model (mocked)
- `test_continue_with_edits_creates_branch()` - Continue after edit creates new branch
- `test_continue_without_edits_same_branch()` - Continue without edit stays on branch
- `test_branch_naming_nested()` - Test main → main-1 → main-1-1
- `test_latest_artifacts_mixed_versions()` - Test query returns correct versions when beats edited separately
- `test_edit_phase1_only_at_phase1()` - Test can't edit spec at Phase 2 (400 error)
- `test_regenerate_phase2_only_at_phase2()` - Test can't regenerate beat at Phase 3 (400 error)

### Success Criteria

#### Automated Verification (Required):
- [ ] Edit spec endpoint creates new artifact version: `test_edit_spec_creates_new_version` passes
- [ ] Upload image endpoint creates new beat artifact: `test_upload_image_replaces_beat` passes
- [ ] Regenerate beat calls FLUX (mocked): `test_regenerate_beat_calls_flux` passes
- [ ] Regenerate chunk calls video model (mocked): `test_regenerate_chunk_calls_hailuo` passes
- [ ] Continue with edits creates new branch: `test_continue_with_edits_creates_branch` passes
- [ ] Branch naming works correctly: `test_branch_naming_nested` passes (main → main-1, main-1 → main-1-1)
- [ ] Latest artifacts query handles mixed versions: `test_latest_artifacts_mixed_versions` passes
- [ ] Phase restrictions enforced: `test_edit_phase1_only_at_phase1` and similar tests pass
- [ ] All tests pass: `pytest backend/tests/test_artifact_editing.py -v`

#### Manual Verification (Prompt user):
```
Phase 4 automated tests passed. Before continuing to Phase 5:

Optional manual test (requires real AI calls):
1. Generate video and pause at Phase 2
2. Edit beat 3:
   POST /api/video/{id}/checkpoints/{checkpoint_id}/regenerate-beat
   {"beat_index": 3, "prompt_override": "close-up product shot"}
3. Verify in database:
   SELECT * FROM checkpoint_artifacts
   WHERE checkpoint_id = '{checkpoint_id}' AND artifact_key = 'beat_3'
   ORDER BY version;
   - Should see 2 rows (v1 and v2)
   - v2 has parent_artifact_id = v1's id
4. Continue pipeline:
   POST /api/video/{id}/continue {"checkpoint_id": "..."}
5. Verify response:
   {"next_phase": 3, "branch_name": "main-1", "created_new_branch": true}
6. Wait for Phase 3 to complete
7. Verify database:
   SELECT * FROM video_checkpoints WHERE video_id = '{id}';
   - Phase 2 checkpoint on "main" (approved)
   - Phase 3 checkpoint on "main-1" (pending)
   - Phase 3 parent_checkpoint_id = Phase 2 checkpoint_id

Cost estimate: ~$0.03 (1 FLUX regeneration)

Should I continue to Phase 5, or test this manually first?
```

---

## Phase 5: Status & Monitoring Updates

### Overview
Update existing status endpoints to include checkpoint information. Add checkpoint events to SSE streaming. Update Redis caching to include checkpoint ID.

### Changes Required

#### 1. Update Status Endpoint

**File**: `backend/app/api/status.py`

**Lines 71-110** (modify existing endpoint):
```python
@router.get("/status/{video_id}")
async def get_status(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Existing status logic...

    # Add checkpoint info
    current_checkpoint = get_current_checkpoint(video_id)

    if current_checkpoint:
        # Get latest artifacts (handles mixed versions)
        artifacts = get_latest_artifacts_for_checkpoint(current_checkpoint['id'])

        checkpoint_info = {
            "checkpoint_id": current_checkpoint['id'],
            "branch_name": current_checkpoint['branch_name'],
            "phase_number": current_checkpoint['phase_number'],
            "version": current_checkpoint['version'],
            "status": current_checkpoint['status'],
            "created_at": current_checkpoint['created_at'],
            "artifacts": artifacts
        }
    else:
        checkpoint_info = None

    # Get branch tree for visualization
    checkpoint_tree = build_checkpoint_tree(video_id)

    # Get active branches
    active_branches = get_leaf_checkpoints(video_id)

    return StatusResponse(
        # ... existing fields ...
        current_checkpoint=checkpoint_info,
        checkpoint_tree=checkpoint_tree,
        active_branches=active_branches
    )
```

#### 2. Update StatusResponse Schema

**File**: `backend/app/common/schemas.py`

**Modify existing StatusResponse**:
```python
class StatusResponse(BaseModel):
    video_id: str
    status: str
    progress: float
    current_phase: Optional[str]
    # ... existing fields ...

    # NEW: Checkpoint fields
    current_checkpoint: Optional[CheckpointInfo] = None
    checkpoint_tree: Optional[List[CheckpointTreeNode]] = None
    active_branches: Optional[List[BranchInfo]] = None

class CheckpointInfo(BaseModel):
    checkpoint_id: str
    branch_name: str
    phase_number: int
    version: int
    status: str
    created_at: datetime
    artifacts: Dict[str, ArtifactResponse]  # Keyed by artifact_key

class CheckpointTreeNode(BaseModel):
    checkpoint: CheckpointResponse
    children: List['CheckpointTreeNode']

class BranchInfo(BaseModel):
    branch_name: str
    latest_checkpoint_id: str
    phase_number: int
    status: str
    can_continue: bool
```

#### 3. Update SSE Streaming

**File**: `backend/app/api/status.py`

**Lines 113-218** (modify existing stream endpoint):
```python
@router.get("/status/{video_id}/stream")
async def stream_status(
    video_id: str,
    current_user: dict = Depends(get_current_user)
):
    async def event_generator():
        last_checkpoint_id = None
        last_status = None

        while True:
            # Get current status
            status = build_status_response(video_id)

            # Check for checkpoint changes
            current_checkpoint = get_current_checkpoint(video_id)
            checkpoint_id = current_checkpoint['id'] if current_checkpoint else None

            # Emit event if checkpoint changed
            if checkpoint_id != last_checkpoint_id:
                yield {
                    "event": "checkpoint_created",
                    "data": json.dumps({
                        "checkpoint_id": checkpoint_id,
                        "phase": current_checkpoint['phase_number'],
                        "branch": current_checkpoint['branch_name']
                    })
                }
                last_checkpoint_id = checkpoint_id

            # Emit status update if changed
            if status.status != last_status:
                yield {
                    "event": "status_update",
                    "data": json.dumps(status.dict())
                }
                last_status = status.status

            # Stop streaming if complete/failed
            if status.status in ['complete', 'failed']:
                break

            await asyncio.sleep(1.5)

    return EventSourceResponse(event_generator())
```

#### 4. Update Redis Cache

**File**: `backend/app/services/redis.py`

**Add methods**:
```python
def set_video_checkpoint(self, video_id: str, checkpoint_id: str) -> bool:
    """Set current checkpoint ID for video."""
    return self._client.set(
        self._key(video_id, "checkpoint_id"),
        checkpoint_id,
        ex=self.REDIS_TTL
    )

def get_video_checkpoint(self, video_id: str) -> Optional[str]:
    """Get current checkpoint ID."""
    val = self._client.get(self._key(video_id, "checkpoint_id"))
    return val.decode() if val else None
```

#### 5. Update Progress Tracking

**File**: `backend/app/orchestrator/progress.py`

**Lines 17-191** (modify update_progress):
```python
def update_progress(
    video_id: str,
    status: str,
    progress: Optional[float] = None,
    checkpoint_id: Optional[str] = None,  # NEW
    **kwargs
) -> None:
    """Update video progress including checkpoint info."""

    # Existing Redis/DB update logic...

    # Add checkpoint to Redis
    if checkpoint_id:
        redis_client.set_video_checkpoint(video_id, checkpoint_id)
```

#### 6. Create Tests

**File**: `backend/tests/test_status_checkpoints.py` (new)

Test cases:
- `test_status_includes_checkpoint()` - Verify current_checkpoint in response
- `test_status_includes_tree()` - Verify checkpoint_tree in response
- `test_status_active_branches()` - Verify active_branches in response
- `test_sse_emits_checkpoint_events()` - Verify SSE emits checkpoint_created
- `test_sse_stops_on_complete()` - Verify stream terminates correctly
- `test_redis_checkpoint_caching()` - Verify checkpoint_id cached in Redis

### Success Criteria

#### Automated Verification (Required):
- [ ] Status endpoint includes checkpoint info: `test_status_includes_checkpoint` passes
- [ ] Status endpoint includes tree structure: `test_status_includes_tree` passes
- [ ] Status endpoint includes active branches: `test_status_active_branches` passes
- [ ] SSE emits checkpoint events: `test_sse_emits_checkpoint_events` passes
- [ ] SSE terminates correctly: `test_sse_stops_on_complete` passes
- [ ] Redis caches checkpoint ID: `test_redis_checkpoint_caching` passes
- [ ] All tests pass: `pytest backend/tests/test_status_checkpoints.py -v`

#### Manual Verification (Optional):
```
Phase 5 automated tests passed. Optionally verify:

1. Start video generation
2. Connect to SSE stream:
   curl -N -H "Authorization: Bearer {token}" \
   http://localhost:8000/api/status/{video_id}/stream
3. Verify events received:
   event: checkpoint_created
   data: {"checkpoint_id": "...", "phase": 1, "branch": "main"}

   event: status_update
   data: {"status": "paused_at_phase1", ...}
4. Call GET /api/status/{video_id}
5. Verify response includes:
   - current_checkpoint: {...}
   - checkpoint_tree: [...]
   - active_branches: [...]

Should I continue to Phase 6 (final phase)?
```

---

## Phase 6: YOLO Mode

### Overview
Implement auto-continue mode ("YOLO mode") that runs pipeline straight through without pausing. Reuses same code path as manual mode, just auto-approves checkpoints.

### Changes Required

#### 1. Add Auto-Continue Flag to Generate Request

**File**: `backend/app/common/schemas.py`

**Lines 22-30** (modify existing GenerateRequest):
```python
class GenerateRequest(BaseModel):
    title: Optional[str]
    description: Optional[str]
    prompt: str
    reference_assets: Optional[List[str]]
    model: Optional[str] = 'hailuo'
    auto_continue: bool = False  # NEW: YOLO mode flag
```

#### 2. Update Generate Endpoint

**File**: `backend/app/api/generate.py`

**Lines 28-40** (modify video creation):
```python
# Create video record
video = VideoGeneration(
    id=video_id,
    user_id=user_id,
    prompt=request.prompt,
    title=request.title,
    description=request.description,
    auto_continue=request.auto_continue,  # NEW: Set YOLO flag
    model=request.model,
    status=VideoStatus.QUEUED
)
db.add(video)
db.commit()
```

#### 3. Auto-Approval Logic

**Already implemented in Phase 2** - Each phase task checks:
```python
# At end of each phase task
if get_auto_continue_flag(video_id):
    approve_checkpoint(checkpoint_id)
    dispatch_next_phase(video_id, checkpoint_id)
```

**Functions already created**:
- `get_auto_continue_flag()` in `backend/app/orchestrator/pipeline.py`
- `dispatch_next_phase()` in `backend/app/orchestrator/pipeline.py`

#### 4. Create Tests

**File**: `backend/tests/test_yolo_mode.py` (new)

Test cases:
- `test_generate_with_yolo_mode()` - POST /generate with auto_continue=true
- `test_yolo_auto_approves_checkpoints()` - Verify checkpoints auto-approved
- `test_yolo_runs_to_completion()` - Verify all phases run without pausing
- `test_yolo_vs_manual_same_output()` - Verify same final artifacts (mocked)
- `test_yolo_creates_checkpoints()` - Verify checkpoint records still created
- `test_yolo_approved_at_timestamps()` - Verify approved_at set immediately
- `test_manual_mode_pauses()` - Verify auto_continue=false still pauses

### Success Criteria

#### Automated Verification (Required):
- [ ] Generate endpoint accepts auto_continue flag: `test_generate_with_yolo_mode` passes
- [ ] YOLO mode auto-approves checkpoints: `test_yolo_auto_approves_checkpoints` passes
- [ ] YOLO mode creates checkpoint records: `test_yolo_creates_checkpoints` passes
- [ ] Checkpoints have approved_at timestamps: `test_yolo_approved_at_timestamps` passes
- [ ] Manual mode still pauses correctly: `test_manual_mode_pauses` passes
- [ ] All tests pass: `pytest backend/tests/test_yolo_mode.py -v`

#### Manual Verification (Prompt user):
```
Phase 6 automated tests passed. Final verification:

Manual test (requires real AI calls):
1. Test YOLO mode:
   POST /api/generate {
     "prompt": "luxury watch commercial",
     "auto_continue": true
   }

2. Monitor logs - verify phases run automatically:
   - Phase 1 completes → auto-approves → Phase 2 starts
   - Phase 2 completes → auto-approves → Phase 3 starts
   - Phase 3 completes → auto-approves → Phase 4 starts
   - Phase 4 completes → video status = 'complete'

3. Check database:
   SELECT * FROM video_checkpoints WHERE video_id = '{id}';
   - Should see 4 checkpoints (one per phase)
   - All have approved_at timestamps
   - All on "main" branch

4. Test manual mode:
   POST /api/generate {
     "prompt": "luxury watch commercial",
     "auto_continue": false
   }

5. Verify pipeline pauses at Phase 1
6. Continue manually and verify works as expected

Cost estimate for YOLO test: ~$0.50 (full pipeline with mocked AI if possible, or ~$2-3 with real AI)

All 6 phases complete! Implementation plan finished.
```

---

## Testing Strategy

### Unit Tests (Cheap, Automated)
**Mock AI services** (GPT-4, FLUX, Hailuo) for all unit tests:
- Use fixtures from `backend/tests/mocks/ai_services.py`
- Tests run fast (~seconds) and cost nothing
- Validate logic, database operations, API responses

### Integration Tests (One Smoke Test)
**One real pipeline run** (Phase 1 → Phase 2 only):
- Uses actual GPT-4 and FLUX APIs
- Cost: ~$0.10 (GPT-4 $0.02 + FLUX 3 images $0.075)
- Validates end-to-end integration
- Run after Phase 2 implementation

### Manual Verification
**Prompt user to confirm** after phases with complex workflows:
- Phase 2: One real video generation
- Phase 4: Edit and branch creation
- Phase 6: YOLO mode full pipeline

**Format**:
```
Automated tests passed. Optional manual test:
[Steps to verify]
Cost estimate: $X.XX
Options: a) Test yourself, b) Skip, c) Add more automated tests
```

### Test Commands

Run all tests:
```bash
pytest backend/tests/ -v
```

Run specific phase tests:
```bash
pytest backend/tests/test_checkpoints_db.py -v          # Phase 1
pytest backend/tests/test_checkpoint_creation.py -v     # Phase 2
pytest backend/tests/test_checkpoint_api.py -v          # Phase 3
pytest backend/tests/test_artifact_editing.py -v        # Phase 4
pytest backend/tests/test_status_checkpoints.py -v      # Phase 5
pytest backend/tests/test_yolo_mode.py -v               # Phase 6
```

---

## Performance Considerations

### Database Queries
- **Checkpoint tree query**: Uses recursive CTE with index on `parent_checkpoint_id`
- **Latest artifacts query**: Uses `DISTINCT ON (artifact_key) ... ORDER BY version DESC` with index on `checkpoint_id`
- **Branch listing**: Queries leaf checkpoints (WHERE id NOT IN (SELECT parent_checkpoint_id ...)) with index

### S3 Storage
- **No file copying**: Artifacts track S3 URLs in database, reuse URLs across checkpoints
- **Versioned paths**: `beat_00_v1.png`, `beat_00_v2.png` - no overwrites
- **Cleanup strategy**: TBD - implement garbage collection later if needed

### Redis Caching
- **Checkpoint ID cached**: Fast lookup of current checkpoint (60-min TTL)
- **Status endpoint**: Checks Redis first, falls back to DB
- **SSE streaming**: Polls every 1.5 seconds, minimal DB load

### Celery Task Management
- **No chain overhead**: Phases dispatched individually, no waiting tasks
- **YOLO mode**: Same code path, just auto-dispatch (no polling)
- **Worker efficiency**: Tasks complete and exit, no blocking

---

## Migration Notes

### Database Migration
```bash
# Apply migration
python backend/migrate.py up

# Verify tables created
psql -d aivideo -c "\dt video_checkpoints"
psql -d aivideo -c "\dt checkpoint_artifacts"

# Check indexes
psql -d aivideo -c "\di" | grep checkpoints
```

### No Data Migration Needed
- Existing videos (pre-checkpoint) ignored - no backward compatibility
- New videos start with checkpoints from day 1
- Old videos continue to work in read-only mode

### Rollback Plan
If implementation fails:
1. Remove checkpoint-related code
2. Restore Celery chain in `pipeline.py`
3. Drop tables: `DROP TABLE checkpoint_artifacts; DROP TABLE video_checkpoints;`
4. Remove enum values (requires new migration)

---

## References

- **Original Feature Spec**: `feature.md`
- **Codebase Research**: `thoughts/shared/research/2025-11-20-checkpoint-feature-analysis.md`
- **Current Pipeline**: `backend/app/orchestrator/pipeline.py:22-109`
- **Phase Tasks**:
  - Phase 1: `backend/app/phases/phase1_validate/task.py:26-144`
  - Phase 2: `backend/app/phases/phase2_storyboard/task.py:221-261`
  - Phase 3: `backend/app/phases/phase3_chunks/task.py:294-542`
  - Phase 4: `backend/app/phases/phase4_refine/task.py:14-282`
- **Database Models**: `backend/app/common/models.py:52-96`
- **S3 Service**: `backend/app/services/s3.py`
- **Migration System**: `backend/migrate.py`

---

## Implementation Timeline Estimate

**Phase 1**: 1-2 days (database schema + tests)
**Phase 2**: 2-3 days (modify 4 phase tasks + tests)
**Phase 3**: 1-2 days (API endpoints + tests)
**Phase 4**: 2-3 days (edit endpoints + branching logic + tests)
**Phase 5**: 1 day (status updates + tests)
**Phase 6**: 0.5 day (YOLO flag + tests)

**Total**: ~8-12 days for complete implementation and testing

**Parallelization Opportunities**:
- Phase 1 can be done independently
- Phase 3-5 can be developed in parallel with Phase 2 (using mocked checkpoints)
- Frontend development can start after Phase 3 (API contracts defined)
