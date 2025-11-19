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

## PR #9: Parallel Chunk Generation with Dependency-Aware Waves

**Goal:** Enable parallel chunk generation while respecting dependencies between reference-based and last-frame-based chunks

**Current Issue:**
- Phase 4 generates chunks sequentially (slow)
- Chunks with reference images could be generated in parallel
- Chunks using last frames need to wait for their predecessor, but can run in parallel with other dependent chunks

**The Solution:**
- Use Celery `chord` pattern for parallel execution
- Split Phase 4 into two waves:
  - **Wave 1**: Generate all chunks with reference images (parallel)
  - **Wave 2**: Generate all chunks using last frames (parallel, after Wave 1 completes)
- Maintain chain pattern for non-blocking orchestration

**Benefits:**
- Significant speedup for videos with multiple beats
- 6 beats with 3 reference images: Wave 1 runs 3 chunks in parallel, Wave 2 runs 3 chunks in parallel
- Worker threads remain non-blocking
- Respects chunk generation dependencies

**Dependency Structure Example:**
```
Wave 1 (Parallel): Beats with reference_image
- Beat 0 (has ref) → Chunk 0
- Beat 2 (has ref) → Chunk 2  
- Beat 4 (has ref) → Chunk 4

Wave 2 (Parallel): Beats using last_frame from previous chunk
- Beat 1 (uses Chunk 0's last frame) → Chunk 1
- Beat 3 (uses Chunk 2's last frame) → Chunk 3
- Beat 5 (uses Chunk 4's last frame) → Chunk 5
```

**Chord Pattern Example:**
```python
from celery import chain, chord

# Individual parallelizable tasks
@celery_app.task
def generate_chunk_with_reference(beat, video_id):
    chunk_url = hailuo_generate(beat["reference_image"])
    save_chunk_to_db(video_id, beat["beat_id"], chunk_url)
    return chunk_url

@celery_app.task
def generate_chunk_with_last_frame(beat, video_id, previous_chunk_id):
    last_frame = extract_last_frame(previous_chunk_id)
    chunk_url = hailuo_generate(last_frame)
    save_chunk_to_db(video_id, beat["beat_id"], chunk_url)
    return chunk_url

# Wave tasks with chords
@celery_app.task
def phase4_wave1_chunks(phase3_result):
    """Create chord for parallel reference-based chunks."""
    beats_with_refs = [b for b in beats if b.get("reference_image")]
    
    result = chord([
        generate_chunk_with_reference.s(beat, video_id)
        for beat in beats_with_refs
    ])(phase4_wave1_complete.s(phase3_result))
    
    # DON'T call .get() - return chord AsyncResult
    return result

@celery_app.task
def phase4_wave2_chunks(phase4_wave1_result):
    """Create chord for parallel last-frame-based chunks."""
    beats_with_last_frames = [b for b in beats if not b.get("reference_image")]
    
    result = chord([
        generate_chunk_with_last_frame.s(beat, video_id, prev_chunk_id)
        for beat in beats_with_last_frames
    ])(phase4_wave2_complete.s(phase4_wave1_result))
    
    return result

# Main pipeline
workflow = chain(
    phase1_planning.s(video_id, prompt),
    phase2_storyboards.s(),
    phase3_references.s(),
    phase4_wave1_chunks.s(),  # Returns chord (auto-waits)
    phase4_wave2_chunks.s(),  # Returns chord (auto-waits)
    phase5_stitch.s(),
    phase6_music.s()
).apply_async()
```

**Files to Review:**
- `backend/app/phases/phase4_chunks_storyboard/task.py` (main chunk generation logic)
- `backend/app/orchestrator/pipeline.py` (orchestrator with chain pattern)
- `backend/app/orchestrator/celery_app.py` (Celery configuration)

### Task 9.1: Investigate Current Phase 4 Implementation

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Review current sequential chunk generation loop
- [ ] Identify how reference images are used vs last frames
- [ ] Understand chunk dependency structure in spec
- [ ] Document how beats are marked with `reference_image` field
- [ ] Trace how last frames are extracted and passed to next chunk
- [ ] Confirm chunks are saved to DB with proper ordering

### Task 9.2: Design Two-Wave Chord Pattern

**Files:** `backend/app/phases/phase4_chunks_storyboard/task.py`, `backend/app/orchestrator/pipeline.py`

- [ ] Design Wave 1 chord: parallel chunks with reference images
- [ ] Design Wave 2 chord: parallel chunks using last frames
- [ ] Plan data flow: Wave 1 results → extract last frames → Wave 2 input
- [ ] Design chord callback structure for each wave
- [ ] Map how to identify which beats belong to which wave
- [ ] Plan error handling for partial failures in each wave
- [ ] Design progress tracking for two-wave execution

**Key Questions:**
- [ ] How to filter beats by `reference_image` presence?
- [ ] How to map dependent beats to their predecessor's last frame?
- [ ] How to merge Wave 1 and Wave 2 results in correct order?

### Task 9.3: Create Individual Chunk Generation Tasks

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Create `generate_chunk_with_reference` task (for Wave 1)
  - Input: beat dict, video_id
  - Extract reference_image from beat
  - Call video generation API with reference
  - Save chunk to DB with beat_index
  - Return chunk metadata (id, url, beat_index, last_frame_path)

- [ ] Create `generate_chunk_with_last_frame` task (for Wave 2)
  - Input: beat dict, video_id, previous_chunk_id
  - Fetch last frame from previous chunk
  - Call video generation API with last frame
  - Save chunk to DB with beat_index
  - Return chunk metadata (id, url, beat_index, last_frame_path)

- [ ] Ensure both tasks are idempotent (can retry safely)
- [ ] Add proper error handling and logging
- [ ] Extract last frame after generation for next wave

### Task 9.4: Create Wave 1 Chord (Reference-Based Chunks)

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Create `phase4_wave1_chunks` task
  - Input: phase3_result (contains beats and storyboard data)
  - Filter beats with `reference_image` field
  - Build chord with `generate_chunk_with_reference` for each beat
  - Attach `phase4_wave1_complete` callback
  - Return chord AsyncResult (Celery auto-waits)

- [ ] Create `phase4_wave1_complete` callback task
  - Input: list of chunk results, phase3_result
  - Merge results with phase3_result
  - Return updated result dict with wave1_chunks
  - Log completion and chunk count

### Task 9.5: Create Wave 2 Chord (Last-Frame-Based Chunks)

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Create `phase4_wave2_chunks` task
  - Input: phase4_wave1_result (contains wave1 chunks)
  - Filter beats without `reference_image` field
  - Map each dependent beat to its predecessor chunk (by beat_index - 1)
  - Build chord with `generate_chunk_with_last_frame` for each beat
  - Attach `phase4_wave2_complete` callback
  - Return chord AsyncResult

- [ ] Create `phase4_wave2_complete` callback task
  - Input: list of chunk results, phase4_wave1_result
  - Merge Wave 1 and Wave 2 results in correct beat order
  - Return complete phase4_result with all chunks
  - Log completion and total chunk count

### Task 9.6: Update Orchestrator Chain

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Update `run_pipeline` to use two-wave Phase 4:
  ```python
  workflow = chain(
      phase1_planning.s(...),
      phase2_storyboards.s(),
      phase3_references.s(),
      phase4_wave1_chunks.s(),  # Returns chord (auto-waits)
      phase4_wave2_chunks.s(),  # Returns chord (auto-waits)
      phase5_stitch.s(),
      phase6_music.s()
  ).apply_async()
  ```
- [ ] Remove old blocking `phase4_chunks` task
- [ ] Update progress tracking to account for two waves
- [ ] Test chain execution flows correctly

### Task 9.7: Handle Edge Cases

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Handle case where all beats have reference images (Wave 2 is empty)
  - Wave 2 chord should be skipped or return empty list gracefully
  
- [ ] Handle case where no beats have reference images (Wave 1 is empty)
  - This shouldn't happen (first beat should always have reference)
  - Add validation and error if this occurs

- [ ] Handle case with single beat (no parallelization needed)
  - Still use chord pattern for consistency

- [ ] Ensure beat_index ordering is preserved in final results
  - Sort chunks by beat_index before returning

### Task 9.8: Update Progress Tracking

**Files:** `backend/app/orchestrator/progress.py`, chunk generation tasks

- [ ] Update progress for Wave 1 start
- [ ] Update progress for each Wave 1 chunk completion
- [ ] Update progress for Wave 1 completion
- [ ] Update progress for Wave 2 start
- [ ] Update progress for each Wave 2 chunk completion
- [ ] Update progress for Wave 2 completion
- [ ] Calculate progress percentage accounting for two waves

### Task 9.9: Testing and Verification

- [ ] Test with 2 beats (1 reference, 1 last-frame): should run sequentially as 2 waves
- [ ] Test with 4 beats (2 reference, 2 last-frame): Wave 1 runs 2 parallel, Wave 2 runs 2 parallel
- [ ] Test with 6 beats (3 reference, 3 last-frame): Wave 1 runs 3 parallel, Wave 2 runs 3 parallel
- [ ] Test with all reference images: Wave 2 should handle empty case gracefully
- [ ] Verify chunks are saved to DB in correct beat_index order
- [ ] Verify last frames are correctly extracted and passed to Wave 2
- [ ] Test error handling: if 1 chunk in Wave 1 fails, how does Wave 2 handle missing last frame?
- [ ] Verify progress tracking shows both waves correctly
- [ ] Test with concurrent video generations to verify true parallelization

**Key Implementation Notes:**
1. **No `.get()` calls** - return chord AsyncResults, let Celery handle waiting
2. **Wave dependencies** - Wave 2 task receives Wave 1 results via chain
3. **Beat ordering** - preserve beat_index throughout both waves
4. **Last frame extraction** - must happen in Wave 1 before Wave 2 starts
5. **Error isolation** - failure in one chord doesn't block others (within same wave)

---