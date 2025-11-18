# TDD Implementation Tasks - Part 3: Storyboard Generation Fixes

**Goal:** Fix storyboard image generation to match beat count and enable parallel generation

---

## PR #7: Fix Storyboard Image Count to Match Beat Count

**Goal:** Ensure storyboard generation creates exactly N images for N beats (e.g., 3 beats = 3 images, not 5)

**Current Issue:**
- Storyboard generation may be creating a fixed number of images (e.g., 5) regardless of actual beat count
- Need to ensure image count matches the number of beats in the spec

**Investigation Needed:**
- Review Phase 2 storyboard generation logic
- Identify where image count is determined
- Verify beat extraction from spec
- Check for any hardcoded image counts

**Files to Review:**
- `backend/app/phases/phase2_storyboard/task.py`
- `backend/app/phases/phase2_storyboard/image_generation.py`
- `backend/app/orchestrator/pipeline.py` (Phase 2 invocation)

### Task 7.1: Investigate Current Storyboard Generation Logic

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [x] Review `generate_storyboard` function implementation
- [x] Trace how beats are extracted from spec
- [x] Identify where image count is determined
- [x] Check for any hardcoded image counts or fixed loops
- [x] Document current behavior with examples

### Task 7.2: Fix Image Generation to Match Beat Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [x] Ensure loop iterates over `spec['beats']` directly
- [x] Remove any fixed image count logic (e.g., always generating 5 images)
- [x] Verify beat extraction: `beats = spec.get('beats', [])`
- [x] Ensure loop uses `enumerate(beats)` to get correct beat_index
- [x] Add logging to show beat count vs image count

### Task 7.3: Add Validation for Image Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [x] After generation loop, verify `len(storyboard_images) == len(beats)`
- [x] Raise ValueError if counts don't match
- [x] Log validation success/failure
- [x] Include beat count and image count in error message

### Task 7.4: Add Beat Count Validation and Truncation

**Goal:** Prevent Phase 1 from generating too many beats for the target duration

**File:** `backend/app/phases/phase1_validate/validation.py`

- [x] Add validation function: `validate_and_fix_beat_count(spec: dict) -> dict`
- [x] Calculate maximum beats: `max_beats = ceil(duration / 5)` (5s minimum beat length)
- [x] If `len(beats) > max_beats`: truncate beats to fit duration
- [x] Recalculate start times after truncation
- [x] Log WARNING when truncation occurs with details
- [x] Save truncation events to `backend/logs/beat_truncation.log` with timestamp, video_id, original count, truncated count
- [x] Call validation function in `build_full_spec()` before returning spec

### Task 7.5: Testing and Verification

- [x] Test with 1 beat (should generate 1 image)
- [x] Test with 3 beats (should generate 3 images)
- [x] Test with 5 beats (should generate 5 images)
- [x] Test with 7 beats (should generate 7 images)
- [x] Verify each image is correctly mapped to its beat
- [x] Verify beat_index in storyboard_images matches beat order
- [x] Test truncation: manually create spec with 10 beats for 15s duration (should truncate to 3)
- [x] Verify truncation log file is created when truncation occurs

---

## PR #8: Non-Blocking Orchestration with Celery Chains

**Goal:** Refactor orchestrator to use Celery Chains for non-blocking pipeline execution, enabling true concurrent video processing

**Current Issue:**
- **Blocking Orchestrator Problem**: The orchestrator uses `.get()` calls that block worker threads
- Worker with `--concurrency=4` can only handle 4 videos at once, even though worker is idle waiting for subtasks
- Each phase waits for the previous phase to complete before starting, holding worker threads hostage
- Sequential storyboard image generation is slow and inefficient (can be parallelized)

**The Problem (Current State):**
```python
# Current implementation (BAD - blocks worker)
@celery_app.task
def orchestrate_video(video_id):
    # Phase 1
    result1 = phase1_task.delay(video_id)
    plan = result1.get()  # ❌ BLOCKS worker thread waiting
    
    # Phase 2
    result2 = phase2_task.delay(video_id, plan)
    storyboard = result2.get()  # ❌ BLOCKS again
    
    # Phase 3
    result3 = phase3_task.delay(video_id, storyboard)
    chunks = result3.get()  # ❌ BLOCKS again
    
    # etc...
```

**Result:** Worker with `--concurrency=4` can only handle 4 videos at once, even though the worker is just sitting idle waiting for subtasks.

**The Solution: Celery Chains**
- Non-blocking orchestration using Celery's native workflow primitives
- Orchestrator dispatches entire pipeline as chain and returns immediately
- Worker thread freed to handle more videos concurrently
- Each phase automatically starts when previous phase completes

**Example Implementation:**
```python
from celery import chain

@celery_app.task
def orchestrate_video(video_id):
    """
    Dispatch entire pipeline as chain - returns immediately.
    Worker thread freed to handle more videos.
    """
    workflow = chain(
        phase1_planning.s(video_id),
        phase2_storyboard.s(),
        phase3_chunks.s(),
        phase4_stitch.s(),
        phase5_music.s()
    ).apply_async()
    
    # Returns immediately - worker thread freed!
    return workflow.id
```

**Investigation Needed:**
- Review current blocking orchestrator implementation in `pipeline.py`
- Identify all `.get()` calls that block worker threads
- Review current sequential storyboard generation implementation
- Identify dependencies between beat image generations
- Determine optimal parallelization strategy (Celery groups for beats, chains for phases)
- Consider rate limiting and cost implications

**Files to Review:**
- `backend/app/orchestrator/pipeline.py` (main orchestrator with blocking calls)
- `backend/app/phases/phase2_storyboard/task.py` (main generation loop)
- `backend/app/phases/phase2_storyboard/image_generation.py` (individual image generation)
- `backend/app/orchestrator/celery_app.py` (Celery configuration)

### Task 8.1: Investigate Current Blocking Orchestrator

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Review `run_pipeline` function implementation (note: function is `run_pipeline`, not `orchestrate_video_generation`)
- [x] Identify all `.apply()` calls that block worker threads (found 5 blocking points, one per phase)
- [x] Document current execution flow showing blocking points (see `backend/docs/pr8-investigation.md`)
- [x] Document worker thread utilization (worker threads spend most time idle waiting for API calls)
- [x] Review Phase 2 storyboard sequential generation loop (found in `task.py` lines 58-86)
- [x] Identify where `generate_beat_image` is called sequentially (sequential loop in Phase 2)
- [x] Check for any dependencies between beat generations (no dependencies - can be parallelized)

**Documentation**: See `backend/docs/pr8-investigation.md` for detailed analysis.

### Task 8.2: Design Non-Blocking Orchestration Strategy

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Design Celery Chain workflow for entire pipeline
- [x] Map phase dependencies (Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5)
- [x] Design chain structure: `chain(phase1.s(), phase2.s(), phase3.s(), phase4.s(), phase5.s())`
- [x] Plan how to pass data between chain links (each phase receives previous phase's PhaseOutput dict)
- [x] Design chain structure for orchestrator (parallelization within phases is out of scope)
- [x] Design error handling for chain failures and partial failures (each phase returns PhaseOutput with status)
- [x] Plan progress tracking mechanism for chain execution (each phase updates progress independently)

**Documentation**: See `backend/docs/pr8-design.md` for complete design specification.

---

