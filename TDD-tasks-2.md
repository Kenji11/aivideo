# TDD Implementation Tasks - Part 2: Phase 2 Storyboard (Replaces Phase 3 References)

**Goal:** Implement Phase 2 storyboard generation with beat-to-image mapping

**Architecture Decision:** Phase 2 storyboard images REPLACE Phase 3 reference generation. 
- OLD: Phase 3 generates 1 reference image per video
- NEW: Phase 2 generates 1 storyboard image per beat (N beats = N images)
- Phase 3 will be **explicitly disabled** but kept in codebase

**Beat-to-Chunk Mapping (Option C):**
- Storyboard images are used at **beat boundaries**
- Beat 1 (10s) = Chunk 0 (storyboard) + Chunk 1 (last-frame continuation)
- Beat 2 (5s) = Chunk 2 (storyboard from beat 2)
- Beat 3 (5s) = Chunk 3 (storyboard from beat 3)
- Example: 3 beats (10s + 5s + 5s) = 4 chunks, 3 storyboard images

---

## PR #4: Phase 2 Structure & Implementation

### Task 4.0: Disable Phase 3 Explicitly

**File:** `backend/app/phases/phase3_references/task.py`

- [ ] Add large comment block at top of file:
  ```python
  # ============================================================================
  # PHASE 3 DISABLED - REPLACED BY PHASE 2 STORYBOARD GENERATION (TDD v2.0)
  # ============================================================================
  # This phase is kept in codebase for backward compatibility with old videos
  # but is NOT used for new video generation.
  # 
  # OLD System: Phase 3 generated 1 reference image per video
  # NEW System: Phase 2 generates N storyboard images (1 per beat)
  # 
  # DO NOT DELETE - May be needed for legacy video playback/debugging
  # ============================================================================
  ```
- [ ] Comment out the entire `generate_references` task function body
- [ ] Keep function signature but return error immediately:
  ```python
  return PhaseOutput(
      video_id=video_id,
      phase="phase3_references",
      status="skipped",
      output_data={"message": "Phase 3 disabled - using Phase 2 storyboard instead"},
      cost_usd=0.0,
      duration_seconds=0.0,
      error_message="Phase 3 is disabled in TDD v2.0"
  ).dict()
  ```

### Task 4.1: Create Phase 2 Directory Structure

- [ ] Create directory `backend/app/phases/phase2_storyboard/`
- [ ] Create `__init__.py` in phase2_storyboard
- [ ] Create `task.py` in phase2_storyboard
- [ ] Create `image_generation.py` in phase2_storyboard

### Task 4.2: Implement Image Generation Helper

**File:** `backend/app/phases/phase2_storyboard/image_generation.py`

- [ ] Import replicate_client, s3_client
- [ ] Import COST_SDXL_IMAGE from constants
- [ ] Import tempfile, requests, logging
- [ ] Create logger instance
- [ ] Create `generate_beat_image(video_id, beat_index, beat, style, product, user_id) -> dict` function
- [ ] Add docstring explaining:
  - [ ] Returns dict with: beat_id, beat_index, start, duration, image_url, shot_type, prompt_used
  - [ ] beat_index used for determining which chunk this starts
- [ ] Extract base_prompt from beat['prompt_template']
- [ ] Fill in {product_name} placeholder in prompt
- [ ] Extract colors from style['color_palette'], join with commas
- [ ] Extract lighting from style['lighting']
- [ ] Compose full_prompt with:
  - [ ] base_prompt (with product filled in)
  - [ ] color palette
  - [ ] lighting
  - [ ] "cinematic composition"
  - [ ] "high quality professional photography"
  - [ ] "1280x720 aspect ratio"
  - [ ] shot_type framing
- [ ] Create negative_prompt with:
  - [ ] "blurry, low quality, distorted, deformed, ugly, amateur"
  - [ ] "watermark, text, signature, letters, words"
  - [ ] "multiple subjects, cluttered, busy, messy, chaotic"
- [ ] Log prompt (first 100 chars)

### Task 4.3: Implement SDXL Generation Call

**File:** `backend/app/phases/phase2_storyboard/image_generation.py` (continued)

- [ ] Call replicate_client.run with:
  - [ ] model="stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
  - [ ] input.prompt = full_prompt
  - [ ] input.negative_prompt = negative_prompt
  - [ ] input.width = 1280
  - [ ] input.height = 720
  - [ ] input.num_inference_steps = 30
  - [ ] input.guidance_scale = 7.5
  - [ ] input.scheduler = "K_EULER"
- [ ] Extract image_url from output[0]
- [ ] Download image with requests.get
- [ ] Save to temp file with .png suffix
- [ ] Construct s3_key using get_video_s3_key helper: `users/{user_id}/videos/{video_id}/storyboard/beat_{beat_index:02d}.png`
- [ ] Upload to S3 with s3_client.upload_file
- [ ] Log upload success
- [ ] Return dict with:
  - [ ] beat_id, beat_index, start, duration
  - [ ] image_url (S3 URL)
  - [ ] shot_type
  - [ ] prompt_used (full_prompt)

### Task 4.4: Implement Phase 2 Task

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Import celery_app
- [ ] Import PhaseOutput from common.schemas
- [ ] Import generate_beat_image from .image_generation
- [ ] Import COST_SDXL_IMAGE from constants
- [ ] Import time, logging
- [ ] Create logger instance
- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_storyboard(self, video_id, spec, user_id)` function
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Extract beats, style, product from spec
- [ ] Log start message with video_id and beat count

### Task 4.5: Implement Storyboard Generation Loop

**File:** `backend/app/phases/phase2_storyboard/task.py` (continued)

- [ ] Wrap in try/except block
- [ ] Initialize empty storyboard_images list
- [ ] Initialize total_cost = 0.0
- [ ] Loop through beats with enumerate:
  - [ ] Log progress (i+1/total, beat_id)
  - [ ] Call generate_beat_image(video_id, i, beat, style, product, user_id)
  - [ ] Append returned dict to storyboard_images
  - [ ] Add COST_SDXL_IMAGE to total_cost
- [ ] Log completion with count and cost

### Task 4.6: Implement Success/Failure Paths

**File:** `backend/app/phases/phase2_storyboard/task.py` (continued)

- [ ] Create PhaseOutput with:
  - [ ] video_id
  - [ ] phase="phase2_storyboard"
  - [ ] status="success"
  - [ ] output_data={"storyboard_images": storyboard_images}
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

## PR #5: Phase 4 Integration (Use Storyboard Images at Beat Boundaries)

### Task 5.1: Update Phase 4 Chunk Generation Logic

**File:** `backend/app/phases/phase4_chunks/task.py`

**Goal:** Modify chunk generation to use storyboard images at beat boundaries

**Current Logic:**
- Chunk 0: Uses Phase 3 reference image
- Chunks 1+: Use last-frame continuation

**NEW Logic (Option C):**
- Determine which chunks start new beats
- Use storyboard image at beat boundaries
- Use last-frame continuation within beats

**Changes:**
- [ ] Read `storyboard_images` from Phase 2 output (stored in DB or passed in)
- [ ] Calculate beat boundaries → chunk mapping
- [ ] For each chunk:
  - [ ] Check if chunk starts a new beat
  - [ ] If yes: Use corresponding storyboard image as init_image
  - [ ] If no: Use last frame from previous chunk (existing logic)
- [ ] Log which init_image source is used for each chunk

**Algorithm for Beat-to-Chunk Mapping:**
```python
# Example: 3 beats (10s + 5s + 5s) with 5s chunks = 4 chunks
# Beat 0 starts at 0s → Chunk 0
# Beat 1 starts at 10s → Chunk 2 (10s / 5s per chunk)
# Beat 2 starts at 15s → Chunk 3 (15s / 5s per chunk)

beat_to_chunk = {}
current_time = 0
for beat_idx, beat in enumerate(beats):
    chunk_idx = current_time // actual_chunk_duration
    beat_to_chunk[chunk_idx] = beat_idx  # This chunk starts a beat
    current_time += beat['duration']
```

### Task 5.2: Update Chunk Generation Function

**File:** `backend/app/phases/phase4_chunks/service.py` (or wherever generate_single_chunk is)

- [ ] Add `storyboard_images` parameter to chunk generation function
- [ ] Add `beat_to_chunk_map` parameter
- [ ] Check if current chunk_idx is in beat_to_chunk_map
- [ ] If yes: Get storyboard_images[beat_idx]['image_url'] as init_image
- [ ] If no: Use last_frame from previous chunk (existing logic)
- [ ] Log: "Chunk {idx} - Using storyboard from beat {beat_idx}" or "Chunk {idx} - Using last frame continuation"

---

## ✅ PR #4 & #5 Checklist

Before merging:
- [ ] Phase 3 explicitly disabled with clear comments
- [ ] Phase 2 generates N storyboard images (1 per beat)
- [ ] Storyboard images stored in database
- [ ] Phase 4 calculates beat-to-chunk mapping correctly
- [ ] Phase 4 uses storyboard images at beat boundaries
- [ ] Phase 4 uses last-frame continuation within beats
- [ ] All S3 uploads work correctly
- [ ] Cost calculation is accurate

**Next:** Move to `TDD-tasks-3.md` for Phase 4 refinement and end-to-end testing