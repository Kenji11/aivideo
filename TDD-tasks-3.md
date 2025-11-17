# TDD Implementation Tasks - Part 3: Phase 3 Chunk Generation

**Goal:** Implement Phase 3 chunk generation with beat-to-chunk mapping

---

## PR #7: Phase 3 Structure & Helpers

### Task 7.1: Create Phase 3 Directory Structure

- [ ] Create directory `backend/app/phases/phase3_chunks/`
- [ ] Create `__init__.py` in phase3_chunks
- [ ] Create `task.py` in phase3_chunks
- [ ] Create `video_generation.py` in phase3_chunks
- [ ] Create `frame_extraction.py` in phase3_chunks

### Task 7.2: Implement Frame Extraction Helper

**File:** `backend/app/phases/phase3_chunks/frame_extraction.py`

- [ ] Import s3_client, ffmpeg_service
- [ ] Import tempfile, os, logging
- [ ] Create logger instance
- [ ] Create `download_from_s3(s3_url: str) -> str` function:
  - [ ] Extract bucket and key from s3:// URL
  - [ ] Split on '/' to get bucket and key
  - [ ] Create temp file with correct suffix
  - [ ] Call s3_client.client.download_file
  - [ ] Return temp file path
- [ ] Create `extract_last_frame(video_url, video_id, chunk_idx) -> str` function:
  - [ ] Add docstring
  - [ ] Download video from S3
  - [ ] Create output path for PNG
  - [ ] Run ffmpeg command:
    - [ ] `-sseof -0.1` (0.1s before end)
    - [ ] `-i video_path`
    - [ ] `-update 1`
    - [ ] `-q:v 1` (high quality)
    - [ ] `-frames:v 1`
    - [ ] output_path
  - [ ] Upload frame to S3: `videos/{video_id}/frames/chunk_{chunk_idx}_last_frame.png`
  - [ ] Log success
  - [ ] Return S3 URL

### Task 7.3: Implement Video Generation Helper

**File:** `backend/app/phases/phase3_chunks/video_generation.py`

- [ ] Import replicate_client, s3_client
- [ ] Import MODEL_CONFIGS, DEFAULT_MODEL from constants
- [ ] Import download_from_s3 from .frame_extraction
- [ ] Import tempfile, requests, logging
- [ ] Create logger instance
- [ ] Create `generate_video_chunk(video_id, chunk_idx, input_image, model) -> str` function
- [ ] Add docstring with Args and Returns
- [ ] Get model_config from MODEL_CONFIGS
- [ ] Download input_image to temp path
- [ ] Log generation start with model name

### Task 7.4: Implement Replicate Video Call

**File:** `backend/app/phases/phase3_chunks/video_generation.py` (continued)

- [ ] Open input image file
- [ ] Call replicate_client.run with:
  - [ ] model = config['replicate_model']
  - [ ] input = {image param, **config['params']}
  - [ ] Use config['param_names']['image'] for image key
- [ ] Extract video URL from output (handle str or list)
- [ ] Download video with requests.get
- [ ] Save to temp file with .mp4 suffix
- [ ] Construct s3_key: `videos/{video_id}/chunks/chunk_{chunk_idx:02d}.mp4`
- [ ] Upload to S3
- [ ] Log upload success
- [ ] Return S3 URL

---

## PR #8: Phase 3 Task Implementation

### Task 8.1: Implement Phase 3 Task Structure

**File:** `backend/app/phases/phase3_chunks/task.py`

- [ ] Import celery_app
- [ ] Import PhaseOutput from common.schemas
- [ ] Import generate_video_chunk from .video_generation
- [ ] Import extract_last_frame from .frame_extraction
- [ ] Import MODEL_CONFIGS, DEFAULT_MODEL from constants
- [ ] Import time, logging
- [ ] Create logger instance
- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_chunks(self, video_id, spec, storyboard)` function
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Extract beats from spec
- [ ] Build storyboard_images dict mapping beat_id → image_url
- [ ] Get model config
- [ ] Log start message with model and beat count

### Task 8.2: Implement Beat-to-Chunk Mapping Loop

**File:** `backend/app/phases/phase3_chunks/task.py` (continued)

- [ ] Wrap in try/except block
- [ ] Initialize empty chunks list
- [ ] Initialize total_cost = 0.0
- [ ] Loop through beats:
  - [ ] Log beat processing (beat_id, duration)
  - [ ] Calculate num_chunks = beat['duration'] // 5
  - [ ] Loop chunk_idx_in_beat from 0 to num_chunks:
    - [ ] Calculate chunk_start = beat['start'] + (chunk_idx_in_beat * 5)
    - [ ] Calculate global_chunk_idx = len(chunks)
    - [ ] Determine input_image and input_type

### Task 8.3: Implement Input Selection Logic

**File:** `backend/app/phases/phase3_chunks/task.py` (continued)

- [ ] If chunk_idx_in_beat == 0:
  - [ ] Set input_image = storyboard_images[beat['beat_id']]
  - [ ] Set input_type = "storyboard"
- [ ] Else:
  - [ ] Call extract_last_frame(chunks[-1]['url'], video_id, global_chunk_idx)
  - [ ] Set input_image = result
  - [ ] Set input_type = "previous_frame"
- [ ] Log input decision (chunk idx, input_type)

### Task 8.4: Implement Chunk Generation & Result Tracking

**File:** `backend/app/phases/phase3_chunks/task.py` (continued)

- [ ] Call generate_video_chunk(video_id, global_chunk_idx, input_image, model)
- [ ] Append to chunks list:
  - [ ] chunk_idx: global_chunk_idx
  - [ ] beat_id: beat['beat_id']
  - [ ] start: chunk_start
  - [ ] duration: 5
  - [ ] url: chunk_url
  - [ ] input_type: input_type
  - [ ] input_url: input_image
- [ ] Add cost_per_generation to total_cost
- [ ] After all beats processed, log completion with chunk count and total cost

### Task 8.5: Implement Success/Failure Paths

**File:** `backend/app/phases/phase3_chunks/task.py` (continued)

- [ ] Create PhaseOutput with:
  - [ ] video_id
  - [ ] phase="phase3_chunks"
  - [ ] status="success"
  - [ ] output_data={"chunks": chunks}
  - [ ] cost_usd=total_cost
  - [ ] duration_seconds
  - [ ] error_message=None
- [ ] Return output.dict()
- [ ] In except block:
  - [ ] Log error
  - [ ] Create PhaseOutput with status="failed"
  - [ ] Set error_message
  - [ ] cost_usd=0.0
  - [ ] Return output.dict()

---

## PR #9: Phase 3 Tests

### Task 9.1: Create Phase 3 Unit Tests

**File:** `backend/app/tests/test_phase3/test_chunks.py`

- [ ] Import pytest
- [ ] Import generate_chunks from phase3_chunks.task
- [ ] Create mock spec with 3 beats (5s each)
- [ ] Create mock storyboard with 3 images
- [ ] Create `test_chunk_count_simple()`:
  - [ ] Spec: 3 beats × 5s = 15s
  - [ ] Assert should generate 3 chunks
- [ ] Create `test_chunk_count_mixed_durations()`:
  - [ ] Spec: 1×5s + 1×10s + 1×5s = 20s
  - [ ] Assert should generate 4 chunks (1+2+1)
- [ ] Create `test_chunk_beat_mapping()`:
  - [ ] Verify first chunk of each beat uses storyboard
  - [ ] Verify subsequent chunks use previous_frame
- [ ] Create `test_chunk_cost_calculation()`:
  - [ ] 3 chunks
  - [ ] Assert cost = 3 * model_cost

### Task 9.2: Create Frame Extraction Tests

**File:** `backend/app/tests/test_phase3/test_frame_extraction.py`

- [ ] Import pytest
- [ ] Import extract_last_frame from frame_extraction
- [ ] Create `test_download_from_s3()`:
  - [ ] Mock S3 download
  - [ ] Verify temp file created
- [ ] Create `test_extract_last_frame()` (integration):
  - [ ] Requires test video file
  - [ ] Call extract_last_frame
  - [ ] Verify PNG created
  - [ ] Verify S3 upload

### Task 9.3: Create Integration Test (Phase 1+2+3)

**File:** `backend/app/tests/test_integration/test_phase1_2_3.py`

- [ ] Import pytest, os
- [ ] Import all three phase tasks
- [ ] Create `@pytest.mark.integration` decorator
- [ ] Create `@pytest.mark.skipif` for API keys
- [ ] Create `test_phase1_to_phase3()`:
  - [ ] Call Phase 1 with "15s Nike sneakers"
  - [ ] Assert success, extract spec
  - [ ] Call Phase 2 with spec
  - [ ] Assert success, extract storyboard
  - [ ] Call Phase 3 with spec and storyboard
  - [ ] Assert success
  - [ ] Verify chunk count matches expected (3 chunks for 15s)
  - [ ] Verify all chunks have S3 URLs
  - [ ] Verify total cost = sum of all phases

---

## ✅ PR #7, #8, #9 Checklist

Before merging:
- [ ] Frame extraction works correctly
- [ ] Video generation works with Hailuo/Wan
- [ ] Beat-to-chunk mapping is correct for 5s, 10s, 15s beats
- [ ] First chunk of each beat uses storyboard image
- [ ] Subsequent chunks use previous frame
- [ ] All Phase 3 unit tests pass
- [ ] Integration test (Phase 1+2+3) passes

**Next:** Move to `TDD-tasks-4.md` for Phase 4 & 5 implementation