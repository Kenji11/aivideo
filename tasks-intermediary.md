# Tasks: MVP Pipeline Simplification & Phase 4 Improvements

## Overview

Simplify the video generation pipeline for MVP by temporarily removing Phase 2 (Animatic) and Phase 3 (References), making Phase 1 output directly to Phase 4. Additionally, improve Phase 4 with model configuration management, text-to-video fallback, comprehensive logging, and video length debugging.

**PRIORITY: Complete PR #1 and PR #3 first**

### Task Order
1. **PR #1** - Comment out Phase 2 & 3 (MVP simplification)
2. **PR #3** - Add text-to-video fallback
3. PR #2 - Model configuration system
4. PR #4 - Comprehensive logging
5. PR #5 - Video length investigation & fix

## Model Configuration Reference

The model config system will include these models:

- **wan** (wan-2.1-480p) - Currently used, will be DEFAULT_MODEL
- **zeroscope** (Zeroscope v2 XL)
- **animatediff** (AnimateDiff)
- **runway** (Runway Gen-2)

Each model config includes: name, replicate_model, cost_per_generation, params (num_frames, fps, width, height), supports_multi_image, max_reference_assets.

## Relevant Files

- `backend/app/orchestrator/pipeline.py` - Main pipeline orchestration (comment out Phase 2 & 3)
- `backend/app/phases/phase4_chunks/chunk_generator.py` - Chunk generation logic (add text-to-video fallback, logging)
- `backend/app/phases/phase4_chunks/service.py` - Chunk service orchestration (add logging)
- `backend/app/phases/phase4_chunks/schemas.py` - ChunkSpec schema (may need updates for text-to-video)
- `backend/app/phases/phase4_chunks/model_config.py` - NEW: Model configuration management
- `backend/app/common/constants.py` - Add model cost constants
- `backend/app/phases/phase4_chunks/stitcher.py` - Video stitching logic (investigate length issues)

## Tasks

### 🔥 Priority Tasks (Complete First)

- [x] 1.0 Comment Out Phase 2 & 3 in Pipeline (PR #1) **← START HERE**
  - [x] 1.1 In `pipeline.py`, comment out Phase 2 (Animatic) section (lines ~67-100)
  - [x] 1.2 In `pipeline.py`, comment out Phase 3 (References) section (lines ~102-143)
  - [x] 1.3 Update Phase 4 call to pass empty lists: `generate_chunks.apply(args=[video_id, spec, [], {}])`
  - [x] 1.4 Update progress tracking to skip Phase 2 & 3 milestones
  - [x] 1.5 Update cost summary print to exclude Phase 2 & 3
  - [x] 1.6 Add comment documenting temporary removal: "# Phase 2 & 3 temporarily disabled for MVP"
  - [ ] 1.7 Test pipeline runs Phase 1 → Phase 4 successfully

- [x] 3.0 Add Text-to-Video Fallback Support (PR #3) **← DO THIS NEXT**
  - [x] 3.1 Update `build_chunk_specs()` to handle empty `animatic_urls` and `reference_urls`
  - [x] 3.2 Add `use_text_to_video` flag to ChunkSpec schema (boolean, default False)
  - [x] 3.3 When animatic_urls is empty, set `use_text_to_video=True` in ChunkSpec
  - [x] 3.4 Modify `generate_single_chunk()` to check `use_text_to_video` flag
  - [x] 3.5 When `use_text_to_video=True`, skip image composite creation
  - [x] 3.6 When `use_text_to_video=True`, call Replicate with prompt only (no image input)
  - [x] 3.7 Ensure prompt from spec is used (from beat prompt_template)
  - [x] 3.8 Add fallback logic: if image-to-video fails, retry with text-to-video
  - [ ] 3.9 Test text-to-video generation works with empty animatic/reference URLs
  - [ ] 3.10 Test image-to-video still works when URLs are provided

### 📋 Secondary Tasks (Complete After Priorities)

- [x] 2.0 Create Model Configuration System (PR #2)
  - [x] 2.1 Create `backend/app/phases/phase4_chunks/model_config.py` with MODEL_CONFIGS dictionary
  - [x] 2.2 Add model configurations for 'wan', 'zeroscope', 'animatediff', 'runway'
  - [x] 2.3 Add DEFAULT_MODEL constant (set to 'wan' initially - currently used model)
  - [x] 2.4 Create `get_model_config(model_name: str) -> dict` function with validation
  - [x] 2.5 Create `get_default_model() -> dict` function that returns DEFAULT_MODEL config
  - [x] 2.6 Add model cost constants to `backend/app/common/constants.py` (COST_WAN, COST_ZEROSCOPE, COST_ANIMATEDIFF, COST_RUNWAY)
  - [x] 2.7 Add docstrings explaining how to switch models (change DEFAULT_MODEL constant)
  - [x] 2.8 Update `chunk_generator.py` to import and use model config instead of hardcoded values
  - [ ] 2.9 Test model config loads correctly and can be switched

- [x] 4.0 Add Comprehensive Logging to Phase 4 (PR #4)
  - [x] 4.1 **Service Layer**: Add input logging at start of `ChunkGenerationService.generate_all_chunks()`
  - [x] 4.2 Log summary: video_id, spec.duration, num_beats, num_animatic_urls, has_style_guide, has_product_ref
  - [x] 4.3 Log full details: complete spec dict, animatic_urls list, reference_urls dict (use json.dumps for readability)
  - [x] 4.4 **Chunk Generator**: Add input logging at start of `generate_single_chunk()`
  - [x] 4.5 Log chunk_num, start_time, duration, prompt (first 100 chars), use_text_to_video flag
  - [x] 4.6 Log model being used (from model config)
  - [x] 4.7 **Chunk Generator**: Add success logging at end of `generate_single_chunk()`
  - [x] 4.8 Log chunk_num, chunk_url, last_frame_url, cost, generation time
  - [x] 4.9 **Service Layer**: Add success logging at end of `generate_all_chunks()`
  - [x] 4.10 Log total chunks generated, total cost, total time, list of all chunk URLs
  - [x] 4.11 Use consistent log format: emoji prefix + timestamp + structured data
  - [ ] 4.12 Test logging appears correctly in console during generation

- [ ] 5.0 Investigate & Fix Video Length Issues (PR #5)
  - [ ] 5.1 Add logging to `build_chunk_specs()`: log calculated chunk_duration, chunk_overlap, chunk_count
  - [ ] 5.2 Log each ChunkSpec: chunk_num, start_time, duration
  - [ ] 5.3 Verify chunk duration is consistently 2 seconds (check model config params)
  - [ ] 5.4 Find stitcher implementation (likely in `phase4_chunks/` or `phase6_export/`)
  - [ ] 5.5 Add logging to stitcher: log input chunk count, each chunk duration, expected total duration
  - [ ] 5.6 Log actual stitched video duration (use ffprobe to get real duration)
  - [ ] 5.7 Check if overlap logic is working correctly (should trim overlap, not concatenate full chunks)
  - [ ] 5.8 Document findings in comments: what's causing extra length (overlap issue, chunk duration, stitching logic)
  - [ ] 5.9 Implement fix based on findings (adjust overlap calculation or stitching logic)
  - [ ] 5.10 Test stitched video matches expected duration (spec.duration)
  - [ ] 5.11 Add validation: raise warning if stitched duration > spec.duration + 0.5s tolerance

## Notes

- **Phase 2 & 3 Removal**: Temporarily commented out for MVP. Will be re-enabled after Phase 4 is stable.
- **Model Switching**: To switch models, simply change `DEFAULT_MODEL` in `model_config.py`. No code changes needed elsewhere.
- **Current Model**: wan-2.1-480p (wavespeedai/wan-2.1-i2v-480p) is currently used. Will be set as DEFAULT_MODEL.
- **Text-to-Video Fallback**: Gracefully handles missing image inputs by falling back to text-only generation.
- **Logging Strategy**: Two-level logging (summary + details) provides quick overview and deep debugging capability.
- **Video Length Investigation**: Root cause needs to be identified before implementing fix. Could be chunk duration, overlap, or stitching logic.

## Testing Strategy

After each PR:
1. Run integration test with Phase 1 → Phase 4 flow
2. Verify logs appear correctly
3. Check generated video duration
4. Validate cost tracking accuracy

## Success Criteria

- [ ] Pipeline runs Phase 1 → Phase 4 (skipping 2 & 3)
- [ ] Phase 4 generates chunks successfully with or without image inputs
- [ ] Models can be switched by changing single constant
- [ ] Comprehensive logs show all inputs and outputs
- [ ] Video length matches expected duration (±0.5s tolerance)

