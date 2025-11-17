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

- [x] Add large comment block at top of file:
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
- [x] Comment out the entire `generate_references` task function body
- [x] Keep function signature but return error immediately:
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

- [x] Create directory `backend/app/phases/phase2_storyboard/`
- [x] Create `__init__.py` in phase2_storyboard
- [x] Create `task.py` in phase2_storyboard
- [x] Create `image_generation.py` in phase2_storyboard

### Task 4.2: Implement Image Generation Helper

**File:** `backend/app/phases/phase2_storyboard/image_generation.py`

- [x] Import replicate_client, s3_client
- [x] Import COST_SDXL_IMAGE from constants
- [x] Import tempfile, requests, logging
- [x] Create logger instance
- [x] Create `generate_beat_image(video_id, beat_index, beat, style, product, user_id) -> dict` function
- [x] Add docstring explaining:
  - [x] Returns dict with: beat_id, beat_index, start, duration, image_url, shot_type, prompt_used
  - [x] beat_index used for determining which chunk this starts
- [x] Extract base_prompt from beat['prompt_template']
- [x] Fill in {product_name} placeholder in prompt
- [x] Extract colors from style['color_palette'], join with commas
- [x] Extract lighting from style['lighting']
- [x] Compose full_prompt with:
  - [x] base_prompt (with product filled in)
  - [x] color palette
  - [x] lighting
  - [x] "cinematic composition"
  - [x] "high quality professional photography"
  - [x] "1280x720 aspect ratio"
  - [x] shot_type framing
- [x] Create negative_prompt with:
  - [x] "blurry, low quality, distorted, deformed, ugly, amateur"
  - [x] "watermark, text, signature, letters, words"
  - [x] "multiple subjects, cluttered, busy, messy, chaotic"
- [x] Log prompt (first 100 chars)

### Task 4.3: Implement SDXL Generation Call

**File:** `backend/app/phases/phase2_storyboard/image_generation.py` (continued)

- [x] Call replicate_client.run with:
  - [x] model="black-forest-labs/flux-dev" (same as Phase 3)
  - [x] input.prompt = full_prompt
  - [x] input.aspect_ratio = "16:9"
  - [x] input.output_format = "png"
  - [x] input.output_quality = 90
- [x] Extract image_url from output
- [x] Download image with requests.get
- [x] Save to temp file with .png suffix
- [x] Construct s3_key using get_video_s3_key helper: `users/{user_id}/videos/{video_id}/beat_{beat_index:02d}.png`
- [x] Upload to S3 with s3_client.upload_file
- [x] Log upload success
- [x] Return dict with:
  - [x] beat_id, beat_index, start, duration
  - [x] image_url (S3 URL)
  - [x] shot_type
  - [x] prompt_used (full_prompt)

### Task 4.4: Implement Phase 2 Task

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [x] Import celery_app
- [x] Import PhaseOutput from common.schemas
- [x] Import generate_beat_image from .image_generation
- [x] Import COST_FLUX_DEV_IMAGE from constants
- [x] Import time, logging
- [x] Create logger instance
- [x] Create `@celery_app.task(bind=True)` decorator
- [x] Define `generate_storyboard(self, video_id, spec, user_id)` function
- [x] Add docstring with Args and Returns
- [x] Record start_time
- [x] Extract beats, style, product from spec
- [x] Log start message with video_id and beat count

### Task 4.5: Implement Storyboard Generation Loop

**File:** `backend/app/phases/phase2_storyboard/task.py` (continued)

- [x] Wrap in try/except block
- [x] Initialize empty storyboard_images list
- [x] Initialize total_cost = 0.0
- [x] Loop through beats with enumerate:
  - [x] Log progress (i+1/total, beat_id)
  - [x] Call generate_beat_image(video_id, i, beat, style, product, user_id)
  - [x] Append returned dict to storyboard_images
  - [x] Add image_url to beat in spec
  - [x] Add COST_FLUX_DEV_IMAGE to total_cost
- [x] Log completion with count and cost

### Task 4.6: Implement Success/Failure Paths

**File:** `backend/app/phases/phase2_storyboard/task.py` (continued)

- [x] Create PhaseOutput with:
  - [x] video_id
  - [x] phase="phase2_storyboard"
  - [x] status="success"
  - [x] output_data={"storyboard_images": storyboard_images, "spec": spec}
  - [x] cost_usd=total_cost
  - [x] duration_seconds
  - [x] error_message=None
- [x] Return output.dict()
- [x] In except block:
  - [x] Log error
  - [x] Create PhaseOutput with status="failed"
  - [x] Set error_message
  - [x] cost_usd=0.0
  - [x] Return output.dict()

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

## ✅ PR #4 Checklist

Before merging:
- [x] Phase 3 explicitly disabled with clear comments
- [x] Phase 2 generates N storyboard images (1 per beat)
- [x] Storyboard images saved to S3 (directly in video_id folder)
- [x] Image URLs added to each beat in spec
- [x] All S3 uploads work correctly
- [x] Cost calculation is accurate
- [x] Test script created and working

## ✅ PR #5 Checklist (Phase 4 Integration - TODO)

Before merging:
- [ ] Phase 4 calculates beat-to-chunk mapping correctly
- [ ] Phase 4 uses storyboard images at beat boundaries
- [ ] Phase 4 uses last-frame continuation within beats

**Next:** Move to `TDD-tasks-3.md` for Phase 4 refinement and end-to-end testing

---

## PR #6: Refactor Phase 4 Architecture (Separate Storyboard Logic)

### Task 6.1: Create New Phase 4 Storyboard Directory

**Goal:** Separate storyboard-aware logic from old logic to avoid antipattern

- [ ] Create directory `backend/app/phases/phase4_chunks_storyboard/`
- [ ] Create `__init__.py` in phase4_chunks_storyboard
- [ ] Create `chunk_generator.py` in phase4_chunks_storyboard
- [ ] Create `service.py` in phase4_chunks_storyboard
- [ ] Create `task.py` in phase4_chunks_storyboard

### Task 6.2: Move Storyboard Logic to New Directory

**Files:** Move from `phase4_chunks/` to `phase4_chunks_storyboard/`

- [ ] Move `calculate_beat_to_chunk_mapping()` to `phase4_chunks_storyboard/chunk_generator.py`
- [ ] Move `build_chunk_specs_with_storyboard()` to `phase4_chunks_storyboard/chunk_generator.py`
- [ ] Move `_generate_single_chunk_with_storyboard_impl()` to `phase4_chunks_storyboard/chunk_generator.py`
- [ ] Move `generate_single_chunk_with_storyboard()` Celery task to `phase4_chunks_storyboard/task.py`
- [ ] Create new `ChunkGenerationService` in `phase4_chunks_storyboard/service.py` with storyboard-aware logic
- [ ] Remove storyboard logic from `phase4_chunks/chunk_generator.py` (keep old logic only)
- [ ] Remove storyboard logic from `phase4_chunks/service.py` (keep old logic only)

### Task 6.3: Update Pipeline to Choose Flow

**File:** `backend/app/orchestrator/pipeline.py`

**Goal:** Decision happens at pipeline level, not in phase itself

- [ ] After Phase 2 storyboard generation, check if storyboard images exist
- [ ] If storyboard images count > 1:
  - [ ] Call `phase4_chunks_storyboard` service/task
- [ ] Else (fallback):
  - [ ] Call `phase4_chunks` service/task (old logic)
- [ ] Remove storyboard detection logic from `phase4_chunks/service.py`
- [ ] Remove `use_storyboard_logic` flag from `phase4_chunks/service.py`

### Task 6.4: Update Imports and Dependencies

- [ ] Update `phase4_chunks_storyboard` imports to reference shared utilities
- [ ] Ensure both `phase4_chunks` and `phase4_chunks_storyboard` can import from:
  - [ ] `app.phases.phase4_chunks.schemas` (ChunkSpec)
  - [ ] `app.phases.phase4_chunks.stitcher` (VideoStitcher)
  - [ ] `app.phases.phase4_chunks.model_config` (model configs)
- [ ] Update pipeline imports to include both phase4_chunks and phase4_chunks_storyboard

### Task 6.5: Clean Up Old Code

- [ ] Remove `build_chunk_specs_with_storyboard` from `phase4_chunks/chunk_generator.py`
- [ ] Remove `generate_single_chunk_with_storyboard` from `phase4_chunks/chunk_generator.py`
- [ ] Remove `_generate_single_chunk_with_storyboard_impl` from `phase4_chunks/chunk_generator.py`
- [ ] Remove storyboard-related imports from `phase4_chunks/service.py`
- [ ] Remove storyboard detection logic from `phase4_chunks/service.py`
- [ ] Keep old `build_chunk_specs()` and `generate_single_chunk()` in `phase4_chunks/` unchanged

### Task 6.6: Testing

- [ ] Test pipeline with storyboard images (should use phase4_chunks_storyboard)
- [ ] Test pipeline without storyboard images (should use phase4_chunks fallback)
- [ ] Verify both flows generate chunks correctly
- [ ] Verify stitching works for both flows