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

## PR #9: Streaming Downloads + Parallel Image Generation (Phase 2)

**Goal:** Implement streaming downloads for generated images, then enable parallel image generation for all beats in Phase 2 storyboard

**Current Issue:**
- Phase 2 generates storyboard images sequentially (one at a time)
- Large images are loaded entirely into memory before processing
- No parallelization means slow generation for videos with many beats
- Memory usage can spike with large image downloads

**The Solution (Two-Part):**

**Part 1: Enable Streaming Downloads**
- Implement streaming downloads for all image generation APIs (Replicate, etc.)
- Download images in chunks to avoid loading entire files into memory
- Write directly to disk/S3 as data arrives
- Reduce memory footprint in containers

**Part 2: Parallelize Image Generation**
- Use Celery `group()` to generate all beat images in parallel
- Each beat image generation becomes independent subtask
- Maintain beat order in results using `group()` ordering
- Add rate limiting to avoid API throttling

**Benefits:**
- Faster storyboard generation (parallel instead of sequential)
- Lower memory usage (streaming instead of buffering)
- Better container resource utilization
- More videos can be processed concurrently

**Investigation Needed:**
- Review current image download implementation
- Identify all places where images are downloaded (Replicate API responses)
- Review current sequential loop in Phase 2
- Design parallel task structure for beat image generation
- Determine optimal rate limiting strategy

**Files to Review:**
- `backend/app/phases/phase2_storyboard/task.py` (sequential generation loop)
- `backend/app/phases/phase2_storyboard/image_generation.py` (image generation logic)
- `backend/app/services/replicate.py` (image download implementation)
- `backend/app/services/s3.py` (S3 upload implementation)

### Task 9.1: Investigate Current Image Download Implementation

**Files:** `backend/app/services/replicate.py`, `backend/app/phases/phase2_storyboard/image_generation.py`

- [ ] Review how Replicate API responses are downloaded
- [ ] Identify where image bytes are loaded into memory
- [ ] Check if images are buffered entirely before processing
- [ ] Document current memory usage pattern
- [ ] Review S3 upload implementation for images
- [ ] Identify opportunities for streaming

### Task 9.2: Implement Streaming Downloads

**File:** `backend/app/services/replicate.py`

- [ ] Create `stream_download()` function for image URLs
- [ ] Use `requests.get(stream=True)` with `iter_content(chunk_size=8192)`
- [ ] Write chunks directly to temporary file or S3
- [ ] Add progress tracking for large downloads
- [ ] Handle partial downloads and errors gracefully
- [ ] Add retry logic for failed chunks
- [ ] Update all image download calls to use streaming

**File:** `backend/app/services/s3.py`

- [ ] Update S3 upload to accept file-like objects (streaming)
- [ ] Use `upload_fileobj()` instead of `upload_file()` where possible
- [ ] Enable multipart uploads for large files
- [ ] Stream directly from download to S3 (no intermediate disk)

### Task 9.3: Design Parallel Image Generation Structure

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Design task signature: `generate_single_beat_image(video_id, beat, beat_index, user_id)`
- [ ] Plan how to collect results maintaining beat order
- [ ] Design error handling for individual beat failures
- [ ] Plan progress tracking across parallel tasks
- [ ] Design rate limiting strategy (max concurrent image generations)

### Task 9.4: Implement Single Beat Image Generation Task

**File:** `backend/app/phases/phase2_storyboard/image_generation.py` (create new file if needed)

- [ ] Create `@celery_app.task` for single beat image generation
- [ ] Extract beat image generation logic from main loop
- [ ] Accept beat data and video_id as parameters
- [ ] Use streaming downloads for generated images
- [ ] Return beat_index and image_url in result
- [ ] Handle errors and return error status
- [ ] Update progress for this specific beat

### Task 9.5: Refactor Phase 2 to Use Celery Group

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Replace sequential loop with Celery `group()`
- [ ] Create list of tasks: `[generate_beat_image.s(video_id, beat, i, user_id) for i, beat in enumerate(beats)]`
- [ ] Execute group and collect results: `job = group(tasks).apply_async()`
- [ ] Wait for all tasks to complete: `results = job.get()`
- [ ] Sort results by beat_index to maintain order
- [ ] Check for any failed tasks and handle appropriately
- [ ] Update storyboard_images with results

### Task 9.6: Add Rate Limiting and Resource Management

**File:** `backend/app/orchestrator/celery_app.py`

- [ ] Configure rate limit for image generation tasks
- [ ] Set max concurrent image generations (e.g., 5 at a time)
- [ ] Add queue configuration for image generation
- [ ] Document rate limiting rationale (API limits, cost control)

### Task 9.7: Testing and Verification

- [ ] Test with 3 beats (verify all 3 images generated in parallel)
- [ ] Test with 10 beats (verify rate limiting works)
- [ ] Monitor memory usage during parallel generation
- [ ] Verify streaming reduces memory footprint
- [ ] Test error handling (one beat fails, others continue)
- [ ] Verify beat order is preserved in final results
- [ ] Compare generation time: sequential vs parallel
- [ ] Test with slow network to verify streaming works

---

## PR #10: Streaming Downloads + Parallel Chunk Generation (Phase 4)

**Goal:** Implement streaming downloads for video chunks, then enable parallel chunk generation for all beats in Phase 4

**Current Issue:**
- Phase 4 generates video chunks sequentially (one at a time)
- Large video files are loaded entirely into memory before processing
- No parallelization means slow generation for videos with many chunks
- Memory usage can spike with large video downloads (video files >> image files)

**The Solution (Two-Part):**

**Part 1: Enable Streaming Downloads**
- Implement streaming downloads for all video generation APIs (Hailuo, Replicate, etc.)
- Download video chunks in chunks (stream) to avoid loading entire files into memory
- Write directly to disk/S3 as data arrives
- Reduce memory footprint in containers (critical for video files)

**Part 2: Parallelize Chunk Generation**
- Use Celery `group()` to generate all video chunks in parallel
- Each chunk generation becomes independent subtask
- Maintain chunk order in results using `group()` ordering
- Add rate limiting to avoid API throttling and cost overruns

**Benefits:**
- Faster chunk generation (parallel instead of sequential)
- Lower memory usage (streaming instead of buffering entire videos)
- Better container resource utilization
- More videos can be processed concurrently

**Investigation Needed:**
- Review current video chunk download implementation
- Identify all places where video chunks are downloaded (Hailuo API, Replicate API)
- Review current sequential loop in Phase 4
- Design parallel task structure for chunk generation
- Determine optimal rate limiting strategy (video gen is expensive)

**Files to Review:**
- `backend/app/phases/phase4_chunks_storyboard/task.py` (sequential generation loop)
- `backend/app/phases/phase4_chunks_storyboard/service.py` (chunk generation logic)
- `backend/app/services/replicate.py` (video download implementation)
- `backend/app/services/s3.py` (S3 upload implementation for videos)

### Task 10.1: Investigate Current Video Chunk Download Implementation

**Files:** `backend/app/services/replicate.py`, `backend/app/phases/phase4_chunks_storyboard/service.py`

- [ ] Review how video generation API responses are downloaded
- [ ] Identify where video bytes are loaded into memory
- [ ] Check if videos are buffered entirely before processing
- [ ] Document current memory usage pattern for video chunks
- [ ] Review S3 upload implementation for video chunks
- [ ] Identify opportunities for streaming (critical for large video files)

### Task 10.2: Implement Streaming Downloads for Video Chunks

**File:** `backend/app/services/replicate.py`

- [ ] Create `stream_download_video()` function for video URLs
- [ ] Use `requests.get(stream=True)` with `iter_content(chunk_size=8192)`
- [ ] Write chunks directly to temporary file or S3
- [ ] Add progress tracking for large video downloads
- [ ] Handle partial downloads and errors gracefully
- [ ] Add retry logic for failed chunks
- [ ] Update all video download calls to use streaming

**File:** `backend/app/services/s3.py`

- [ ] Ensure S3 upload supports file-like objects for videos
- [ ] Use `upload_fileobj()` with multipart uploads for large videos
- [ ] Stream directly from download to S3 (no intermediate disk if possible)
- [ ] Configure appropriate chunk size for video uploads

### Task 10.3: Design Parallel Chunk Generation Structure

**File:** `backend/app/phases/phase4_chunks_storyboard/service.py`

- [ ] Design task signature: `generate_single_chunk(video_id, beat, chunk_index, spec, reference_urls, user_id)`
- [ ] Plan how to collect results maintaining chunk order
- [ ] Design error handling for individual chunk failures
- [ ] Plan progress tracking across parallel tasks
- [ ] Design rate limiting strategy (video gen is expensive, limit concurrent generations)

### Task 10.4: Implement Single Chunk Generation Task

**File:** `backend/app/phases/phase4_chunks_storyboard/service.py` (or new task file)

- [ ] Create `@celery_app.task` for single chunk generation
- [ ] Extract chunk generation logic from main loop
- [ ] Accept beat data, chunk_index, and video_id as parameters
- [ ] Use streaming downloads for generated video chunks
- [ ] Return chunk_index and chunk_url in result
- [ ] Handle errors and return error status
- [ ] Update progress for this specific chunk

### Task 10.5: Refactor Phase 4 to Use Celery Group

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Replace sequential loop with Celery `group()`
- [ ] Create list of tasks: `[generate_chunk.s(video_id, beat, i, spec, ref_urls, user_id) for i, beat in enumerate(beats)]`
- [ ] Execute group and collect results: `job = group(tasks).apply_async()`
- [ ] Wait for all tasks to complete: `results = job.get()`
- [ ] Sort results by chunk_index to maintain order
- [ ] Check for any failed tasks and handle appropriately
- [ ] Update chunk_urls with results
- [ ] Pass ordered chunks to stitcher

### Task 10.6: Add Rate Limiting and Resource Management

**File:** `backend/app/orchestrator/celery_app.py`

- [ ] Configure rate limit for chunk generation tasks
- [ ] Set max concurrent chunk generations (e.g., 3 at a time due to cost)
- [ ] Add queue configuration for chunk generation
- [ ] Document rate limiting rationale (API cost, memory limits)
- [ ] Consider separate queue for chunk generation vs image generation

### Task 10.7: Testing and Verification

- [ ] Test with 3 chunks (verify all 3 generated in parallel)
- [ ] Test with 7 chunks (verify rate limiting works)
- [ ] Monitor memory usage during parallel chunk generation
- [ ] Verify streaming reduces memory footprint significantly
- [ ] Test error handling (one chunk fails, others continue)
- [ ] Verify chunk order is preserved in final results
- [ ] Compare generation time: sequential vs parallel
- [ ] Test with slow network to verify streaming works
- [ ] Verify stitching works with parallel-generated chunks

---

