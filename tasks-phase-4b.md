# Phase 4 Tasks - Part B: Parallel Execution & Stitching

**Owner:** Person handling Phase 4  
**Goal:** Implement parallel chunk generation and video stitching

---

## PR #18: Parallel Chunk Generation Service

### Task 18.1: Create ChunkGenerationService Class

**File:** `backend/app/phases/phase4_chunks/service.py`

- [ ] Import celery group from celery
- [ ] Import generate_single_chunk from chunk_generator
- [ ] Import build_chunk_specs function
- [ ] Create ChunkGenerationService class
- [ ] Add `__init__` method
- [ ] Add `total_cost` attribute for cost tracking

### Task 18.2: Implement generate_all_chunks Method

- [ ] Create `generate_all_chunks(video_id, spec, animatic_urls, reference_urls)` method
- [ ] Add docstring explaining parallel execution
- [ ] Call `build_chunk_specs()` to create chunk specifications
- [ ] Create Celery group with all chunk tasks
- [ ] Use `group([generate_single_chunk.s(spec) for spec in chunk_specs])`
- [ ] Execute group with `apply_async()`
- [ ] Wait for results with timeout=600 (10 minutes)
- [ ] Extract chunk URLs from results
- [ ] Extract last frame URLs for temporal consistency
- [ ] Calculate total_cost (num_chunks * COST_ZEROSCOPE_VIDEO)
- [ ] Handle partial failures (some chunks succeed, some fail)
- [ ] Return list of chunk URLs and last_frame URLs

### Task 18.3: Implement Chunk Retry Logic

- [ ] Create `_retry_failed_chunks(failed_chunks: List[ChunkSpec])` method
- [ ] Retry failed chunks individually (not in parallel)
- [ ] Limit retries to 2 attempts per chunk
- [ ] Log retry attempts
- [ ] Return retry results
- [ ] Update total_cost with retry costs

---

## PR #19: Video Stitcher

### Task 19.1: Create VideoStitcher Class

**File:** `backend/app/phases/phase4_chunks/stitcher.py`

- [ ] Import FFmpeg service
- [ ] Import s3_client
- [ ] Create VideoStitcher class
- [ ] Add `__init__` method

### Task 19.2: Implement stitch_with_transitions Method

- [ ] Create `stitch_with_transitions(video_id, chunk_urls, transitions)` method
- [ ] Add docstring explaining stitching process
- [ ] Download all chunk videos from S3 to temp directory
- [ ] Sort chunks by chunk_num (ensure correct order)
- [ ] Build FFmpeg concat filter with transitions
- [ ] Handle transition types:
  - [ ] "cut" - direct concatenation
  - [ ] "fade" - crossfade transition (0.5s default)
  - [ ] "dissolve" - dissolve transition
- [ ] Apply transitions between chunks
- [ ] Use FFmpeg filter_complex for transitions
- [ ] Example command structure:
  ```bash
  ffmpeg -i chunk0.mp4 -i chunk1.mp4 ... \
    -filter_complex "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=1.5[v]" \
    -map "[v]" -c:v libx264 -pix_fmt yuv420p output.mp4
  ```
- [ ] Encode output video (H.264, 1024x576, 24fps)
- [ ] Upload stitched video to S3 at `videos/{video_id}/stitched.mp4`
- [ ] Clean up temp files
- [ ] Return S3 URL of stitched video
- [ ] Add error handling for FFmpeg failures

### Task 19.3: Implement Transition Logic

- [ ] Create `_build_transition_filter(chunk_urls, transitions)` method
- [ ] Map transition types to FFmpeg filters
- [ ] Calculate transition offsets based on chunk durations
- [ ] Build filter_complex string
- [ ] Handle edge cases (first/last chunk)
- [ ] Return filter string

---

## PR #20: Phase 4 Task & Integration

### Task 20.1: Implement Phase 4 Celery Task

**File:** `backend/app/phases/phase4_chunks/task.py`

- [ ] Import celery_app from orchestrator
- [ ] Import PhaseOutput from common.schemas
- [ ] Import ChunkGenerationService
- [ ] Import VideoStitcher
- [ ] Import time module

### Task 20.2: Implement generate_chunks Task Function

- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_chunks(self, video_id, spec, animatic_urls, reference_urls)` signature
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Wrap logic in try/except block

### Task 20.3: Implement Success Path

- [ ] Initialize ChunkGenerationService
- [ ] Call service.generate_all_chunks(video_id, spec, animatic_urls, reference_urls)
- [ ] Initialize VideoStitcher
- [ ] Call stitcher.stitch_with_transitions(video_id, chunk_urls, spec['transitions'])
- [ ] Create PhaseOutput with success status
- [ ] Set video_id, phase="phase4_chunks"
- [ ] Set output_data with stitched_video_url and chunk_urls
- [ ] Set cost_usd from service.total_cost
- [ ] Calculate duration_seconds
- [ ] Return output.dict()

### Task 20.4: Implement Error Path

- [ ] In except block, create PhaseOutput with failed status
- [ ] Set empty output_data
- [ ] Set cost_usd=0.0
- [ ] Calculate duration_seconds
- [ ] Set error_message=str(e)
- [ ] Return output.dict()

### Task 20.5: Create Unit Tests

**File:** `backend/app/tests/test_phase4/test_chunks.py`

- [ ] Import pytest
- [ ] Import ChunkGenerationService, VideoStitcher
- [ ] Create `test_build_chunk_specs()` - verify chunk specs created correctly
- [ ] Create `test_create_reference_composite()` - test image compositing
- [ ] Create `test_stitch_transitions()` - test video stitching
- [ ] Add `@pytest.mark.skipif` for tests requiring API keys
- [ ] Create `test_generate_single_chunk()` - test with real API (if key present)

### Task 20.6: Create Manual Test Script

**File:** `backend/test_phase4.py`

- [ ] Add shebang and docstring
- [ ] Import sys and add app to path
- [ ] Import ChunkGenerationService, VideoStitcher
- [ ] Create test_chunks() function
- [ ] Define test spec with beats and transitions
- [ ] Mock animatic_urls (list of 15 frame URLs)
- [ ] Mock reference_urls (style_guide_url)
- [ ] Print header
- [ ] Call generate_all_chunks
- [ ] Print chunk URLs
- [ ] Call stitch_with_transitions
- [ ] Print stitched video URL
- [ ] Save output to `test_chunks_output.json`
- [ ] Add exception handling
- [ ] Add `if __name__ == "__main__"` block

---

## PR #21: Orchestrator Integration

### Task 21.1: Update Pipeline Orchestrator

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Import generate_chunks task from phase4
- [ ] After Phase 3 success, call `update_progress(video_id, "generating_chunks", 50)`
- [ ] Call `generate_chunks.delay(video_id, spec, animatic_urls, reference_urls).get(timeout=600)`
- [ ] Check if result4['status'] != "success", raise exception
- [ ] Add result4['cost_usd'] to total_cost
- [ ] Call `update_cost(video_id, "phase4", result4['cost_usd'])`
- [ ] Extract stitched_video_url from result4['output_data']
- [ ] Pass stitched_video_url to Phase 5

---

## ✅ PR #18, #19, #20, #21 Checklist

Before merging:
- [ ] Parallel chunk generation works
- [ ] All 15 chunks generated successfully
- [ ] Image compositing works (animatic + style guide for chunk 0)
- [ ] Temporal consistency works (previous frame for chunks 1+)
- [ ] Video stitching with transitions works
- [ ] FFmpeg transitions applied correctly
- [ ] Stitched video uploaded to S3
- [ ] Phase 4 task implemented
- [ ] Unit tests pass (or skip if no API keys)
- [ ] Manual test script works
- [ ] Pipeline orchestrator calls Phase 4
- [ ] Cost tracking updates database

**Test Commands:**
```bash
# Start services
docker-compose up --build

# Run manual test
docker-compose exec api python test_phase4.py

# Check for generated files
ls test_chunks_output.json
```

**Phase 4 is complete!**

