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

- [ ] Review `generate_storyboard` function implementation
- [ ] Trace how beats are extracted from spec
- [ ] Identify where image count is determined
- [ ] Check for any hardcoded image counts or fixed loops
- [ ] Document current behavior with examples

### Task 7.2: Fix Image Generation to Match Beat Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Ensure loop iterates over `spec['beats']` directly
- [ ] Remove any fixed image count logic (e.g., always generating 5 images)
- [ ] Verify beat extraction: `beats = spec.get('beats', [])`
- [ ] Ensure loop uses `enumerate(beats)` to get correct beat_index
- [ ] Add logging to show beat count vs image count

### Task 7.3: Add Validation for Image Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] After generation loop, verify `len(storyboard_images) == len(beats)`
- [ ] Raise ValueError if counts don't match
- [ ] Log validation success/failure
- [ ] Include beat count and image count in error message

### Task 7.4: Add Beat Count Validation and Truncation

**Goal:** Prevent Phase 1 from generating too many beats for the target duration

**File:** `backend/app/phases/phase1_validate/validation.py`

- [ ] Add validation function: `validate_and_fix_beat_count(spec: dict) -> dict`
- [ ] Calculate maximum beats: `max_beats = ceil(duration / 5)` (5s minimum beat length)
- [ ] If `len(beats) > max_beats`: truncate beats to fit duration
- [ ] Recalculate start times after truncation
- [ ] Log WARNING when truncation occurs with details
- [ ] Save truncation events to `backend/logs/beat_truncation.log` with timestamp, video_id, original count, truncated count
- [ ] Call validation function in `build_full_spec()` before returning spec

### Task 7.5: Testing and Verification

- [ ] Test with 1 beat (should generate 1 image)
- [ ] Test with 3 beats (should generate 3 images)
- [ ] Test with 5 beats (should generate 5 images)
- [ ] Test with 7 beats (should generate 7 images)
- [ ] Verify each image is correctly mapped to its beat
- [ ] Verify beat_index in storyboard_images matches beat order
- [ ] Test truncation: manually create spec with 10 beats for 15s duration (should truncate to 3)
- [ ] Verify truncation log file is created when truncation occurs

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

- [ ] Review `orchestrate_video_generation` function implementation
- [ ] Identify all `.get()` calls that block worker threads
- [ ] Document current execution flow showing blocking points
- [ ] Measure how many videos can be processed concurrently with current approach
- [ ] Document worker thread utilization (should show idle time waiting for subtasks)
- [ ] Review Phase 2 storyboard sequential generation loop
- [ ] Identify where `generate_beat_image` is called sequentially
- [ ] Check for any dependencies between beat generations

### Task 8.2: Design Non-Blocking Orchestration Strategy

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Design Celery Chain workflow for entire pipeline
- [ ] Map phase dependencies (Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5)
- [ ] Design chain structure: `chain(phase1.s(), phase2.s(), phase3.s(), phase4.s(), phase5.s())`
- [ ] Plan how to pass data between chain links (each phase receives previous phase output)
- [ ] Design parallel beat generation using Celery `group` within Phase 2
- [ ] Review Celery group/chord patterns for parallel tasks
- [ ] Consider rate limiting for image generation API
- [ ] Design error handling for chain failures and partial failures
- [ ] Plan progress tracking mechanism for chain execution

### Task 8.3: Implement Non-Blocking Orchestrator with Celery Chains

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Refactor `orchestrate_video_generation` to use `chain()` instead of sequential `.get()` calls
- [ ] Create chain workflow: `chain(phase1.s(video_id), phase2.s(), phase3.s(), phase4.s(), phase5.s())`
- [ ] Use `.apply_async()` to dispatch chain non-blocking
- [ ] Return workflow ID immediately (don't wait for completion)
- [ ] Ensure each phase task receives output from previous phase as input
- [ ] Remove all `.get()` blocking calls from orchestrator
- [ ] Update progress tracking to work with async chain execution
- [ ] Test that orchestrator returns immediately without blocking

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Convert `generate_beat_image` to Celery task (if not already)
- [ ] Use Celery `group` to create parallel tasks for all beats
- [ ] Execute group and collect results
- [ ] Handle task results and extract image data
- [ ] Maintain beat order in results (use beat_index for sorting)

### Task 8.4: Add Error Handling for Chains and Parallel Tasks

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Handle chain link failures (if one phase fails, chain stops)
- [ ] Design error propagation through chain
- [ ] Update database status on chain failure
- [ ] Log chain execution progress and failures
- [ ] Handle timeout scenarios for long-running chains

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Handle individual task failures gracefully in beat generation group
- [ ] Collect successful and failed beat generations
- [ ] Log which beats succeeded/failed
- [ ] Decide on failure strategy (fail all vs partial success)
- [ ] Return appropriate error messages

### Task 8.5: Add Progress Tracking for Chains

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Track progress of chain execution
- [ ] Update progress when each phase completes
- [ ] Use Celery result callbacks or signals to track chain progress
- [ ] Update database with phase completion status
- [ ] Log chain execution progress (e.g., "Phase 2/5 complete")

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Track progress of parallel beat generation tasks
- [ ] Update progress for each completed beat image
- [ ] Log progress updates (e.g., "3/5 beats generated")
- [ ] Use Celery result tracking if available

### Task 8.6: Testing and Performance Measurement

**Chain Orchestration Tests:**
- [ ] Test that orchestrator returns immediately (non-blocking)
- [ ] Test concurrent video processing (start 10 videos, verify all accepted)
- [ ] Measure worker thread utilization (should handle more than concurrency limit)
- [ ] Verify chain executes phases in correct order
- [ ] Test chain error handling (simulate phase failure)
- [ ] Verify progress tracking works with async chains
- [ ] Measure overall throughput improvement

**Parallel Beat Generation Tests:**
- [ ] Test parallel generation with 3 beats
- [ ] Test parallel generation with 5 beats
- [ ] Test parallel generation with 7 beats
- [ ] Measure time improvement vs sequential generation
- [ ] Verify cost calculation remains accurate (sum of all image costs)
- [ ] Verify all images are generated correctly
- [ ] Test error handling with simulated failures

**Expected Results:**
- Worker with `--concurrency=4` should be able to handle many more than 4 videos concurrently
- Orchestrator should return immediately without blocking
- Chain should execute phases automatically in sequence
- Parallel beat generation should significantly reduce Phase 2 time

---

