---
date: 2025-11-20T22:06:35-06:00
researcher: lousydropout
git_commit: dc35ffbb8a886cf2e40f8faddca7f25e126de6e1
branch: main
repository: aivideo
topic: "Checkpoint Feature - Codebase Analysis for Pipeline Interruption and Artifact Storage"
tags: [research, codebase, pipeline, checkpoints, s3, database, artifacts]
status: complete
last_updated: 2025-11-20
last_updated_by: lousydropout
---

# Research: Checkpoint Feature - Codebase Analysis

**Date**: 2025-11-20T22:06:35-06:00
**Researcher**: lousydropout
**Git Commit**: dc35ffbb8a886cf2e40f8faddca7f25e126de6e1
**Branch**: main
**Repository**: aivideo

## Research Question

Analyze the codebase to identify all files and line numbers relevant to implementing the checkpoint feature described in `feature.md`. The feature requires adding checkpoints after each pipeline phase to allow:
1. Pausing pipeline execution after each step/phase
2. Storing intermediates in S3 with proper versioning/tagging
3. Storing metadata in database to track checkpoint state
4. Enabling end users to edit artifacts at each checkpoint
5. Supporting branching from checkpoints (transforming linear history into a tree)

## Summary

The AI Video generation pipeline currently executes as a **sequential 4-phase Celery chain** from prompt to final video without intermediate pausing. The codebase already implements comprehensive **artifact storage in S3** and **metadata tracking in PostgreSQL/Redis**, providing a strong foundation for checkpoint functionality. Key findings:

### Current State
- **Pipeline**: 4 phases (Planning → Storyboard → Chunks → Refinement) executed via Celery `chain()` primitive
- **Artifact Storage**: All intermediates already stored in S3 with user-scoped paths (`{user_id}/videos/{video_id}/`)
- **Metadata**: Phase outputs stored in DB `phase_outputs` JSON column with complete history
- **Progress Tracking**: Redis cache (60-min TTL) + PostgreSQL for real-time status updates
- **No Pause Mechanism**: Chain executes continuously; only cancellation available (destructive)

### Infrastructure Already in Place
✅ S3 storage with organized artifact naming (`beat_00.png`, `chunk_00.mp4`, etc.)
✅ Database schema for metadata storage (`phase_outputs`, `spec`, `cost_breakdown`)
✅ Progress tracking system (Redis + PostgreSQL)
✅ Phase output standardization (`PhaseOutput` schema)
✅ User-scoped S3 paths for isolation

### What Needs Implementation
❌ Checkpoint pause/resume mechanism (Celery chain doesn't support pausing)
❌ Versioning/tagging for S3 artifacts (no datetime or branch tracking)
❌ Branching support in database (tree structure vs linear history)
❌ User artifact editing API endpoints
❌ Checkpoint state management (checkpointed vs in-progress vs resumed)

## Detailed Findings

### 1. Pipeline Orchestration and Phase Execution

#### Primary Orchestration Entry Point
**File**: `backend/app/orchestrator/pipeline.py`

- **Lines 22-109**: `run_pipeline()` - Main Celery task orchestrator
  - **Importance**: Creates the Celery chain that links all 4 phases sequentially. **CRITICAL** for checkpoint implementation as this is where execution flow must be interrupted to enable pausing.
  - Current behavior: Creates chain at lines 83-95 and dispatches immediately with `.apply_async()` at line 98
  - **Checkpoint relevance**: To support checkpoints, this would need to dispatch only the next phase rather than the entire chain, or use a state machine pattern instead of Celery chains

```python
# Current implementation (lines 83-95)
workflow = chain(
    plan_video_intelligent.s(video_id, prompt),
    generate_storyboard.s(user_id),
    generate_chunks.s(user_id, model),
    refine_video.s(user_id)
)
result = workflow.apply_async()  # All phases dispatched as one unit
```

#### Phase Task Implementations

**Phase 1: Intelligent Planning**
**File**: `backend/app/phases/phase1_validate/task.py`

- **Lines 26-144**: `plan_video_intelligent()` Celery task
  - **Importance**: Generates complete video specification (beats, style, product, audio). This is the **first checkpoint** where spec should be presented to user for approval.
  - Returns `PhaseOutput` with spec in `output_data['spec']` (lines 118-126)
  - **Checkpoint artifact**: Video specification (JSON) - stored in DB at `VideoGeneration.spec`

**Phase 2: Storyboard Generation**
**File**: `backend/app/phases/phase2_storyboard/task.py`

- **Lines 221-261**: `generate_storyboard()` Celery task
  - **Importance**: Generates storyboard images for each beat. This is the **second checkpoint** where users should review/edit storyboard images before video generation.
  - Stores outputs in DB at lines 147-149: `video.phase_outputs['phase2_storyboard']`
  - **Checkpoint artifacts**: Storyboard images in S3 (`beat_00.png`, `beat_01.png`, etc.) with URLs in spec

**File**: `backend/app/phases/phase2_storyboard/image_generation.py`

- **Lines 121-126**: S3 upload of beat images
  - **Importance**: Shows exact S3 key pattern for storyboard artifacts
  - S3 key format: `{user_id}/videos/{video_id}/beat_{index:02d}.png`

**Phase 3: Chunk Generation and Stitching**
**File**: `backend/app/phases/phase3_chunks/task.py`

- **Lines 294-542**: `generate_chunks()` Celery task
  - **Importance**: Most expensive phase (video generation). This is the **third checkpoint** where users could review individual chunks or the stitched video before audio integration.
  - Parallel execution using `RunnableParallel` at lines 202-205, 239-242
  - Stores outputs at lines 425-438: `video.phase_outputs['phase3_chunks']`
  - **Checkpoint artifacts**: Individual chunks (`chunk_00.mp4`, etc.) and stitched video (`stitched.mp4`)

**Phase 4: Refinement (Audio Integration)**
**File**: `backend/app/phases/phase4_refine/task.py`

- **Lines 14-282**: `refine_video()` Celery task
  - **Importance**: Final phase combining video with music. This is the **fourth checkpoint** where users could approve final video or request music changes.
  - Final state updates at lines 129-156: Sets `VideoStatus.COMPLETE`, stores final URLs
  - **Checkpoint artifacts**: Final video (`final.mp4`) and background music (`background.mp3`)

#### Phase Data Flow Pattern

**File**: All phase task files follow this pattern

- **Importance**: Understanding how data flows between phases is critical for checkpoint resume functionality
- Each phase receives previous phase's `PhaseOutput` as first argument (Celery chain automatic passing)
- Spec is extracted, modified in-place, and passed to next phase
- **Checkpoint implication**: When resuming from checkpoint, must reconstruct the exact `PhaseOutput` dict that the next phase expects

### 2. S3 Storage Infrastructure

#### S3 Client Service
**File**: `backend/app/services/s3.py`

- **Lines 21-24**: `upload_file()` - Primary upload method
  - **Importance**: Used throughout pipeline to store all artifacts to S3
  - Takes local file path and S3 key, returns S3 URL

- **Lines 34-56**: `download_file()` - Download with temp file handling
  - **Importance**: Needed for checkpoint resume when fetching stored artifacts for continuation

- **Lines 66-100**: `list_files()` - List objects by prefix with pagination
  - **Importance**: Could be used to list all checkpoints/versions for a video

- **Lines 124-179**: `delete_directory()` - Batch deletion by prefix
  - **Importance**: Used when deleting video and all its checkpoints/branches

#### S3 Path Organization
**File**: `backend/app/common/constants.py`

- **Lines 84-103**: `get_video_s3_prefix()` - Returns `{user_id}/videos/{video_id}/`
  - **Importance**: **CRITICAL** for checkpoint implementation. All video artifacts are co-located under this prefix.
  - **Checkpoint extension needed**: Add version/branch parameter, e.g., `{user_id}/videos/{video_id}/{branch_id}/{checkpoint_id}/`

- **Lines 106-128**: `get_video_s3_key()` - Constructs full S3 key
  - **Importance**: Used everywhere for artifact uploads. Would need to be modified to include checkpoint/branch identifiers.

#### Current S3 Artifact Naming Patterns

**Storyboard Images** (Phase 2):
- Pattern: `beat_{index:02d}.png` (e.g., `beat_00.png`, `beat_01.png`)
- Location: `{user_id}/videos/{video_id}/beat_00.png`
- **Checkpoint relevance**: Each beat image is an editable artifact at Phase 2 checkpoint

**Video Chunks** (Phase 3):
- Pattern: `chunk_{index:02d}.mp4`
- Location: `{user_id}/videos/{video_id}/chunks/chunk_00.mp4`
- **Checkpoint relevance**: Individual chunks could be regenerated/edited at Phase 3 checkpoint

**Stitched Video** (Phase 3):
- Pattern: `stitched.mp4`
- Location: `{user_id}/videos/{video_id}/stitched.mp4`
- **Checkpoint relevance**: Stitched video is reviewable artifact before audio integration

**Final Artifacts** (Phase 4):
- Pattern: `final.mp4`, `background.mp3`
- Location: `{user_id}/videos/{video_id}/final.mp4`
- **Checkpoint relevance**: Final deliverables at end of pipeline

### 3. Database Schema for Metadata Storage

#### Core Video Model
**File**: `backend/app/common/models.py`

- **Lines 52-96**: `VideoGeneration` table schema
  - **Importance**: **CENTRAL** to checkpoint metadata storage. Contains all state needed to pause/resume pipeline.

**Critical Fields for Checkpoints**:

- **Line 64**: `status` (VideoStatus ENUM)
  - Current values: QUEUED, VALIDATING, GENERATING_CHUNKS, REFINING, COMPLETE, FAILED
  - **Checkpoint extension needed**: Add states like PAUSED_AT_PHASE1, PAUSED_AT_PHASE2, etc.

- **Line 66**: `current_phase` (VARCHAR)
  - **Importance**: Tracks which phase is executing. Critical for checkpoint resume to know where to restart.

- **Line 67**: `progress` (FLOAT 0-100)
  - **Importance**: Enables granular progress tracking within phases

- **Line 75**: `spec` (JSON)
  - **Importance**: Contains complete video specification from Phase 1. Editable at Phase 1 checkpoint.

- **Line 76**: `phase_outputs` (JSON)
  - **Importance**: **CRITICAL** for checkpoints. Stores complete output from each phase with structure:
  ```json
  {
    "phase1_planning": {"status": "success", "output_data": {...}, "cost_usd": 0.02},
    "phase2_storyboard": {"status": "success", "output_data": {...}, "cost_usd": 0.075},
    ...
  }
  ```
  - Contains all metadata needed to resume from any checkpoint

- **Lines 82-86**: Artifact URLs
  - `animatic_urls` (JSON list) - Phase 2 storyboard images
  - `chunk_urls` (JSON list) - Phase 3 video chunks
  - `stitched_url` (VARCHAR) - Phase 3 stitched video
  - `final_video_url` (VARCHAR) - Phase 4 final video
  - `final_music_url` (VARCHAR) - Phase 4 background music
  - **Importance**: Direct references to S3 artifacts. Would need versioning if supporting branches.

- **Line 89**: `cost_breakdown` (JSON)
  - **Importance**: Tracks per-phase costs. Useful for showing cost implications of regenerating from checkpoint.

**Missing Fields for Checkpoints**:
- No `checkpoint_id` or `branch_id` field
- No `parent_video_id` for branching support
- No `checkpoint_state` enum to distinguish checkpointed vs resumed videos
- No `version` or `created_from_checkpoint` field

#### Database Migration System
**File**: `backend/migrate.py`

- **Lines 1-169**: Migration runner using raw SQL
  - **Importance**: Would be used to add new checkpoint-related columns to `VideoGeneration` table

**File**: `backend/migrations/001_initial_schema.sql`

- **Lines 1-83**: Initial database schema
  - **Importance**: Shows how to create ENUMs and tables. Template for checkpoint schema additions.

### 4. Progress and State Tracking

#### Redis Caching Layer
**File**: `backend/app/services/redis.py`

- **Lines 1-253**: RedisClient singleton
  - **Importance**: Provides fast access to in-progress video state. Would be used to store checkpoint pause state.

**Key Redis Operations for Checkpoints**:

- **Lines 41-65**: `set_video_spec()`, `set_video_progress()`, etc.
  - TTL: 3600 seconds (60 minutes)
  - **Checkpoint relevance**: Could store checkpoint pause timestamp and awaiting_user_action flag

- **Lines 89-98**: `set_video_phase_outputs()`
  - Stores nested JSON structure matching DB
  - **Importance**: Could be extended to include checkpoint metadata

- **Lines 129-163**: `get_video_data()`
  - Retrieves all video state as dict
  - **Importance**: Used by status endpoints to show checkpoint state to users

#### Progress Update Mechanism
**File**: `backend/app/orchestrator/progress.py`

- **Lines 17-191**: `update_progress()` function
  - **Importance**: **CRITICAL** entry point for updating video state. Would be called when pausing at checkpoint.
  - Updates Redis first (line 42-96), DB second (line 110-191)
  - Accepts kwargs for phase_outputs, spec, current_phase, error_message
  - **Checkpoint usage**: Call this with status='paused_at_phase2' and checkpoint metadata

- **Lines 192-235**: `update_cost()` function
  - **Importance**: Tracks cumulative costs. Useful for showing cost of continuing from checkpoint vs restarting.

#### Status Query Endpoints
**File**: `backend/app/api/status.py`

- **Lines 71-110**: GET `/api/status/{video_id}` endpoint
  - **Importance**: Would return checkpoint state to frontend for user decision-making
  - Checks Redis first (fast), falls back to DB

- **Lines 113-218**: GET `/api/status/{video_id}/stream` - Server-Sent Events
  - **Importance**: Real-time streaming of progress. Could push checkpoint notifications to frontend.
  - Polls every 1.5 seconds (line 204)

### 5. Artifact Generation Patterns

#### Beat Image Generation (Phase 2 Artifacts)
**File**: `backend/app/phases/phase2_storyboard/image_generation.py`

- **Lines 20-143**: `generate_beat_image()` function
  - **Importance**: Shows complete pattern for generating, downloading, and uploading artifacts
  - Returns dict with metadata: `beat_id`, `beat_index`, `image_url`, `prompt_used`
  - **Checkpoint relevance**: This metadata would be stored at Phase 2 checkpoint for user review

**Artifact Metadata Structure**:
```python
{
    "beat_id": "hero_shot",
    "beat_index": 0,
    "start": 0,
    "duration": 10,
    "image_url": "s3://bucket/user-123/videos/video-456/beat_00.png",
    "shot_type": "wide",
    "prompt_used": "Cinematic hero shot of product..."
}
```

#### Chunk Generation (Phase 3 Artifacts)
**File**: `backend/app/phases/phase3_chunks/chunk_generator.py`

- **Lines 92-121**: `calculate_beat_to_chunk_mapping()`
  - **Importance**: Maps chunk indices to beat boundaries for storyboard placement
  - **Checkpoint relevance**: This mapping is needed to reconstruct chunk generation from Phase 2 checkpoint

- **Lines 399-409**: Chunk upload to S3
  - Uploads both chunk video and last frame PNG
  - **Importance**: Last frame is used for continuity in next chunk. Critical for resuming Phase 3 from checkpoint.

#### Video Stitching (Phase 3 Output)
**File**: `backend/app/phases/phase3_chunks/stitcher.py`

- **Lines 56-72**: Download chunks from S3 for stitching
  - **Importance**: Shows pattern for retrieving stored artifacts. Would be used when resuming from checkpoint.

- **Lines 318-326**: Upload stitched video to S3
  - **Importance**: Stitched video is final artifact of Phase 3 checkpoint

#### Music Integration (Phase 4 Artifacts)
**File**: `backend/app/phases/phase4_refine/service.py`

- **Lines 67-71**: Download stitched video from Phase 3
  - **Importance**: Shows dependency between phases. When resuming from Phase 4 checkpoint, must retrieve Phase 3 output.

- **Lines 156-162**: Upload final video with audio
  - **Importance**: Final deliverable stored in S3

### 6. Pipeline Control Flow

#### Celery Chain Mechanism
**File**: `backend/app/orchestrator/celery_app.py`

- **Lines 1-24**: Celery configuration
  - **Importance**: Configured with Redis broker. **LIMITATION**: Celery chains don't support pausing mid-chain.
  - **Checkpoint implication**: May need to switch from `chain()` to manual task dispatching or workflow engine

#### Cancellation (Only Existing Control Mechanism)
**File**: `backend/cancel_video.py`

- **Lines 12-93**: `cancel_video_generation()` function
  - **Importance**: Shows how to find and revoke Celery tasks. Could be adapted for checkpoint pausing.
  - Uses `celery_app.control.revoke(task_id, terminate=True)` at line 52
  - **Limitation**: Cancellation is destructive; doesn't preserve state for resume

### 7. API Entry Points

#### Video Generation Endpoint
**File**: `backend/app/api/generate.py`

- **Lines 16-97**: POST `/api/generate` endpoint
  - **Importance**: Pipeline entry point. Would need parameter for `resume_from_checkpoint_id`.
  - Creates DB record at lines 28-40
  - Initializes Redis at lines 64-76
  - Dispatches pipeline at line 85: `run_pipeline.delay()`

**Checkpoint Extension Needed**:
```python
# New parameter: checkpoint_id
if checkpoint_id:
    # Resume from checkpoint instead of starting fresh
    resume_pipeline_from_checkpoint(video_id, checkpoint_id)
else:
    # Start new pipeline
    run_pipeline.delay(video_id, prompt, assets, model)
```

#### Video Management
**File**: `backend/app/api/video.py`

- **Lines 125-137**: DELETE `/api/video/{video_id}` endpoint
  - Uses `s3_client.delete_directory()` to remove all artifacts
  - **Checkpoint relevance**: When deleting video with multiple checkpoint branches, would need to delete entire tree

### 8. Supporting Infrastructure

#### Constants and Configuration
**File**: `backend/app/common/constants.py`

- **Lines 76-81**: Legacy S3 prefixes (deprecated)
  - Shows evolution of artifact organization
  - **Importance**: Indicates team is actively refactoring storage patterns

**File**: `backend/app/config.py`

- **Lines 31-35**: AWS configuration
  - S3 bucket, region, credentials from environment
  - **Importance**: S3 infrastructure is production-ready for checkpoint storage

#### Beat and Template Libraries
**File**: `backend/app/common/beat_library.py`

- **Lines 1-220**: 15 predefined beat templates
  - **Importance**: Phase 1 uses these to compose video. When user edits at Phase 1 checkpoint, they could select different beats.

**File**: `backend/app/common/template_archetypes.py`

- **Lines 1-127**: 5 creative templates
  - **Importance**: LLM uses these in Phase 1. Editing template selection could be a Phase 1 checkpoint action.

#### Phase Output Schema Contract
**File**: `backend/app/common/schemas.py`

- **Lines 12-20**: `PhaseOutput` Pydantic model
  - **Importance**: **CRITICAL** standard contract between phases. Checkpoint resume must construct valid `PhaseOutput` for next phase.

```python
class PhaseOutput(BaseModel):
    video_id: str
    phase: str
    status: str  # "success" or "failed"
    output_data: Dict  # Varies by phase
    cost_usd: float
    duration_seconds: float
    error_message: Optional[str] = None
```

## Code References by Checkpoint Stage

### Checkpoint 1: After Phase 1 (Planning) - Spec Review/Edit

**Primary Files**:
- `backend/app/phases/phase1_validate/task.py:118-126` - PhaseOutput with spec
- `backend/app/common/models.py:75` - Spec storage in DB
- `backend/app/orchestrator/progress.py:77-79` - Spec update in Redis
- `backend/app/common/beat_library.py` - Beat templates for editing
- `backend/app/common/template_archetypes.py` - Template selection

**Artifacts to Present**:
- Video specification (JSON) with beats, style, product, audio config
- Template archetype used
- Estimated costs and duration

**Potential User Actions**:
- Edit beat sequence (reorder, add, remove)
- Modify style/product descriptions
- Change template archetype
- Adjust creativity level

### Checkpoint 2: After Phase 2 (Storyboard) - Image Review/Edit

**Primary Files**:
- `backend/app/phases/phase2_storyboard/task.py:147-149` - Phase outputs storage
- `backend/app/phases/phase2_storyboard/image_generation.py:121-126` - Image upload
- `backend/app/common/models.py:82` - `animatic_urls` storage
- `backend/app/services/s3.py:21-24` - S3 upload service
- `backend/app/common/constants.py:106-128` - S3 key generation

**Artifacts to Present**:
- Storyboard images (one per beat): `beat_00.png`, `beat_01.png`, etc.
- Beat metadata (duration, shot_type, prompt used)
- Updated spec with `image_url` in each beat

**Potential User Actions**:
- Regenerate specific beat images with different prompts
- Upload custom images to replace generated ones
- Adjust beat timing/transitions
- Approve and continue to Phase 3

### Checkpoint 3: After Phase 3 (Chunks) - Video Review/Edit

**Primary Files**:
- `backend/app/phases/phase3_chunks/task.py:425-438` - Phase outputs storage
- `backend/app/phases/phase3_chunks/stitcher.py:318-326` - Stitched video upload
- `backend/app/common/models.py:83-85` - Chunk and stitched URL storage
- `backend/app/phases/phase3_chunks/chunk_generator.py:92-121` - Chunk mapping

**Artifacts to Present**:
- Individual video chunks: `chunk_00.mp4`, `chunk_01.mp4`, etc.
- Stitched video with transitions: `stitched.mp4`
- Chunk metadata (timing, beat association, model used)
- Cumulative cost breakdown

**Potential User Actions**:
- Regenerate specific chunks with different models (hailuo/kling/veo)
- Adjust transition parameters
- Upload custom video segments
- Review stitched video before audio
- Approve and continue to Phase 4

### Checkpoint 4: After Phase 4 (Refinement) - Final Review

**Primary Files**:
- `backend/app/phases/phase4_refine/task.py:129-156` - Final state updates
- `backend/app/phases/phase4_refine/service.py:156-162` - Final upload
- `backend/app/common/models.py:86-87` - Final video/music URL storage

**Artifacts to Present**:
- Final video with audio: `final.mp4`
- Background music track: `background.mp3`
- Complete cost breakdown
- Generation time metrics

**Potential User Actions**:
- Change music selection
- Adjust audio levels
- Upload custom music
- Regenerate with different music parameters
- Approve and mark complete

## Architecture Documentation

### Current Pipeline Flow (Linear)

```
User Prompt
    ↓
POST /api/generate
    ↓
run_pipeline() creates Celery chain:
    ↓
[Phase 1: Planning] → spec.json
    ↓
[Phase 2: Storyboard] → beat_00.png, beat_01.png, ...
    ↓
[Phase 3: Chunks] → chunk_00.mp4, ..., stitched.mp4
    ↓
[Phase 4: Refinement] → final.mp4, background.mp3
    ↓
VideoStatus.COMPLETE
```

### Proposed Checkpoint Flow (Tree-Based)

```
User Prompt
    ↓
POST /api/generate
    ↓
[Phase 1: Planning] → PAUSED_AT_PHASE1
    ↓ (checkpoint_id: cp1)
    ├─ User Action: Edit Spec
    │   ↓
    │   Resume → [Phase 2] (branch: main)
    │
    └─ User Action: Try Different Template
        ↓
        Resume → [Phase 1 Retry] → [Phase 2] (branch: alt_template)

[Phase 2: Storyboard] → PAUSED_AT_PHASE2
    ↓ (checkpoint_id: cp2)
    ├─ Branch A: Regenerate Beat 3
    │   ↓
    │   [Phase 2 Partial] → [Phase 3] (branch: beat3_regen)
    │
    └─ Branch B: Approve as-is
        ↓
        [Phase 3] (branch: main)
```

### Data Model Extensions for Checkpoints

**New Database Fields Needed**:
```sql
ALTER TABLE video_generations ADD COLUMN checkpoint_id VARCHAR;
ALTER TABLE video_generations ADD COLUMN parent_video_id VARCHAR;
ALTER TABLE video_generations ADD COLUMN branch_name VARCHAR DEFAULT 'main';
ALTER TABLE video_generations ADD COLUMN checkpoint_state VARCHAR;  -- 'checkpointed', 'resumed', 'completed'
ALTER TABLE video_generations ADD COLUMN paused_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE video_generations ADD COLUMN resumed_at TIMESTAMP WITH TIME ZONE;

-- New enum values
ALTER TYPE videostatus ADD VALUE 'PAUSED_AT_PHASE1';
ALTER TYPE videostatus ADD VALUE 'PAUSED_AT_PHASE2';
ALTER TYPE videostatus ADD VALUE 'PAUSED_AT_PHASE3';
ALTER TYPE videostatus ADD VALUE 'PAUSED_AT_PHASE4';
```

**S3 Path Extensions**:
```
Current: {user_id}/videos/{video_id}/artifact.png
Proposed: {user_id}/videos/{video_id}/{branch_name}/{checkpoint_id}/artifact.png

Example tree:
user-123/videos/video-456/
  ├── main/
  │   ├── cp1/  (Phase 1 checkpoint)
  │   │   └── spec.json
  │   ├── cp2/  (Phase 2 checkpoint)
  │   │   ├── beat_00.png
  │   │   └── beat_01.png
  │   └── cp3/  (Phase 3 checkpoint)
  │       ├── chunk_00.mp4
  │       └── stitched.mp4
  └── alt_template/
      ├── cp1/
      │   └── spec.json
      └── cp2/
          ├── beat_00.png
          └── beat_01.png
```

### Control Flow Modifications

**Replace Celery Chain with State Machine**:

Current approach:
```python
workflow = chain(phase1.s(), phase2.s(), phase3.s(), phase4.s())
workflow.apply_async()  # All phases dispatched
```

Checkpoint approach:
```python
def run_phase(video_id, phase_number):
    if phase_number == 1:
        result = phase1.delay(video_id)
        # Wait for completion, then pause
        update_progress(video_id, status='paused_at_phase1')
        # Don't dispatch phase 2 yet
    # User approves checkpoint
    elif phase_number == 2:
        prev_output = get_phase_output(video_id, 'phase1')
        result = phase2.delay(prev_output)
        # Repeat pattern
```

## Related Research

No previous research documents found for checkpoint functionality.

## Open Questions

1. **Celery Limitations**: Can Celery chains be paused mid-execution, or do we need to switch to a different orchestration pattern (e.g., temporal.io, manual state machine)?

2. **S3 Versioning Strategy**: Should we use S3 native versioning or implement application-level versioning with timestamped/tagged paths?

3. **Branch Management**: How should branches be visualized and managed in the UI? Tree view? Timeline view?

4. **Cost Implications**: How to communicate cost of regenerating from checkpoints (especially Phase 3 which is most expensive)?

5. **Garbage Collection**: How long to retain checkpoint branches before cleanup? User-controlled vs automatic expiration?

6. **Concurrent Editing**: Can multiple branches be processing in parallel from the same checkpoint, or should we enforce sequential processing?

7. **Artifact Editing API**: What operations should be supported at each checkpoint?
   - Phase 1: Edit spec JSON directly? Or provide structured editing endpoints?
   - Phase 2: Upload replacement images? Regenerate with new prompts?
   - Phase 3: Upload custom video segments? Adjust stitching parameters?
   - Phase 4: Upload custom music? Adjust audio levels?

8. **Database Query Performance**: With tree structure, how to efficiently query for:
   - All branches of a video
   - Latest checkpoint of a branch
   - All videos at a specific checkpoint state

9. **Frontend State Management**: How to represent checkpoint state in frontend (React components, state management)?

10. **Backward Compatibility**: How to handle existing videos (linear history) vs new checkpoint videos (tree structure)?
