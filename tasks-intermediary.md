# Tasks: MVP Pipeline Simplification & Phase 4 Improvements

## Overview

Simplify the video generation pipeline for MVP by temporarily removing Phase 2 (Animatic) but re-enabling Phase 3 (References) to generate reference images for video chunks. Use wan model (image-to-video) as default since text-to-video support is limited.

**PRIORITY: Complete PR #6 next (Re-enable Phase 3)**

### Task Order
1. **PR #1** - Comment out Phase 2 & 3 (MVP simplification) ✅
2. **PR #3** - Add text-to-video fallback ✅
3. PR #2 - Model configuration system ✅
4. PR #4 - Comprehensive logging ✅
5. **PR #6** - Re-enable Phase 3 (References) ✅
6. **PR #7** - Add actual_chunk_duration to model configs **← DO THIS NEXT**
7. PR #5 - Video length investigation & fix

## Model Configuration Reference

The model config system will include these models:

- **wan** (wan-2.1-480p) - Currently used, DEFAULT_MODEL, **actual output: ~5 seconds** (ignores duration param)
- **zeroscope** (Zeroscope v2 XL) - **actual output: ~3 seconds** (24 frames @ 8fps)
- **animatediff** (AnimateDiff) - **actual output: ~2 seconds** (16 frames @ 8fps)
- **runway** (Runway Gen-2) - **actual output: ~5-10 seconds** (depends on tier)

Each model config includes: name, replicate_model, cost_per_generation, params (num_frames, fps, width, height), supports_multi_image, max_reference_assets, **actual_chunk_duration** (reality of what model outputs).

## Relevant Files

- `backend/app/orchestrator/pipeline.py` - Main pipeline orchestration (re-enable Phase 3, keep Phase 2 disabled)
- `backend/app/phases/phase3_references/task.py` - Phase 3 Celery task (generate reference images)
- `backend/app/phases/phase3_references/service.py` - Phase 3 service layer (orchestrate reference generation)
- `backend/app/phases/phase3_references/image_generator.py` - Generate reference images via Replicate
- `backend/app/phases/phase3_references/schemas.py` - Phase 3 schemas (ReferenceSpec, ReferenceResult)
- `backend/app/phases/phase4_chunks/chunk_generator.py` - Chunk generation logic (use reference images, logging)
- `backend/app/phases/phase4_chunks/service.py` - Chunk service orchestration (receive reference URLs)
- `backend/app/phases/phase4_chunks/schemas.py` - ChunkSpec schema (use reference images from Phase 3)
- `backend/app/phases/phase4_chunks/model_config.py` - Model configuration management
- `backend/app/common/constants.py` - Model cost constants
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

- [x] 6.0 Re-enable Phase 3 (Reference Generation) (PR #6) **← COMPLETED**
  - [x] 6.1 In `pipeline.py`, uncomment Phase 3 section (lines ~102-143)
  - [x] 6.2 Keep Phase 2 (Animatic) commented out with note: "# Phase 2 disabled for MVP - using Phase 3 references only"
  - [x] 6.3 Update Phase 4 call to pass reference_urls from Phase 3: `generate_chunks.apply(args=[video_id, spec, [], reference_urls])`
  - [x] 6.4 Verify Phase 3 generates ONE reference image per video (not per beat)
  - [x] 6.5 Update Phase 3 to skip style_guide generation (mark as OUT OF SCOPE for MVP)
  - [x] 6.6 In `phase3_references/service.py`, ensure only product_ref is generated (no style_guide)
  - [x] 6.7 Update `build_chunk_specs()` in Phase 4 to use reference_urls['product_ref'] for image-to-video
  - [x] 6.8 Set `use_text_to_video=False` in ChunkSpec when reference image is available
  - [x] 6.9 Update `generate_single_chunk()` to use reference image as first frame input for wan model
  - [x] 6.10 Update progress tracking to include Phase 3 milestone (20% → 40%)
  - [x] 6.11 Update cost summary to include Phase 3 reference generation cost
  - [x] 6.12 Add logging: "Using reference image from Phase 3: {reference_url}"
  - [ ] 6.13 Test pipeline runs Phase 1 → Phase 3 → Phase 4 successfully
  - [ ] 6.14 Verify chunks are generated using reference image (image-to-video mode)
  - [ ] 6.15 Confirm wan model works with reference image input

- [ ] 7.0 Add Actual Chunk Duration to Model Configs (PR #7) **← NEW**
  - [ ] 7.1 Add `actual_chunk_duration` field to each model in `model_config.py`
  - [ ] 7.2 Set wan actual_chunk_duration to 5.0 seconds (model ignores duration param, outputs ~5s)
  - [ ] 7.3 Set zeroscope actual_chunk_duration to 3.0 seconds (24 frames @ 8fps)
  - [ ] 7.4 Set animatediff actual_chunk_duration to 2.0 seconds (16 frames @ 8fps)
  - [ ] 7.5 Set runway actual_chunk_duration to 5.0 seconds (conservative estimate)
  - [ ] 7.6 Add `duration_controllable` boolean flag (False for wan, True for others)
  - [ ] 7.7 Add docstring explaining: "actual_chunk_duration = reality of what model outputs regardless of params"
  - [ ] 7.8 Update `build_chunk_specs()` to use `actual_chunk_duration` for chunk count calculation
  - [ ] 7.9 Calculate chunk_count = ceil(video_duration / actual_chunk_duration) instead of fixed 2s assumption
  - [ ] 7.10 Log: "Model outputs {actual_chunk_duration}s chunks, need {chunk_count} chunks for {duration}s video"
  - [ ] 7.11 Update chunk overlap logic to use actual_chunk_duration (overlap = actual_chunk_duration * 0.25)
  - [ ] 7.12 Remove hardcoded chunk_duration calculations (lines 184-194 in chunk_generator.py)
  - [ ] 7.13 Test with wan model: 30s video should generate ~6 chunks (not 15 chunks assuming 2s)
  - [ ] 7.14 Test with animatediff: 30s video should generate ~15 chunks (2s chunks)
  - [ ] 7.15 Verify stitched video duration matches spec.duration after using actual chunk durations

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

- **Phase 2 Removal**: Phase 2 (Animatic) remains disabled for MVP. Phase 3 (References) is being re-enabled.
- **Phase 3 Scope**: Generate ONE reference image (product_ref) per video. Style guide is OUT OF SCOPE for MVP.
- **Model Strategy**: wan-2.1-480p (image-to-video) is default. Text-to-video support is limited, so we prioritize image-to-video workflow.
- **Model Switching**: To switch models, simply change `DEFAULT_MODEL` in `model_config.py`. No code changes needed elsewhere.
- **Reference Image Usage**: Phase 3 generates reference image → Phase 4 uses it as first frame for all chunks via wan model.
- **Text-to-Video Fallback**: Kept as fallback if reference generation fails, but primary path is image-to-video.
- **Logging Strategy**: Two-level logging (summary + details) provides quick overview and deep debugging capability.
- **Video Length Investigation**: Root cause needs to be identified before implementing fix. Could be chunk duration, overlap, or stitching logic.

## Bug Fixes Applied

1. **Status API None Handling**: Fixed `AttributeError: 'NoneType' object has no attribute 'startswith'` in `status.py` when checking S3 URLs. Added null checks before calling `.startswith()`.

2. **Phase 1 Duration Validation**: Fixed "Beat durations don't match video duration" error caused by rounding when scaling beats for ads. Now adjusts last beat to ensure exact duration match.

## Testing Strategy

After each PR:
1. Run integration test with Phase 1 → Phase 3 → Phase 4 flow
2. Verify logs appear correctly
3. Check generated video duration
4. Validate cost tracking accuracy
5. Verify reference image is generated and used in chunks

## Success Criteria

- [ ] Pipeline runs Phase 1 → Phase 3 → Phase 4 (skipping Phase 2 only)
- [ ] Phase 3 generates reference image successfully
- [ ] Phase 4 uses reference image for image-to-video generation (wan model)
- [ ] Text-to-video fallback works if reference generation fails
- [ ] Models can be switched by changing single constant
- [ ] Comprehensive logs show all inputs and outputs
- [ ] Video length matches expected duration (±0.5s tolerance)

