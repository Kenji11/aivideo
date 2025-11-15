# Tasks: MVP Pipeline Simplification & Phase 4 Improvements

## Overview

Simplify the video generation pipeline for MVP by temporarily removing Phase 2 (Animatic) but re-enabling Phase 3 (References) to generate reference images for video chunks. Use wan model (image-to-video) as default since text-to-video support is limited.

**CRITICAL ISSUE RESOLVED**: Video generation models output different chunk durations regardless of what parameters we request. wan (our default) outputs ~5s chunks, not 2s. This affected chunk count calculation and caused video length issues.

**STATUS: PR #9 In Progress - Hailuo Model Testing & Direction Prompts**

### Task Order
1. **PR #1** - Comment out Phase 2 & 3 (MVP simplification) ✅
2. **PR #3** - Add text-to-video fallback ✅
3. **PR #2** - Model configuration system ✅
4. **PR #4** - Comprehensive logging ✅
5. **PR #6** - Re-enable Phase 3 (References) ✅
6. **PR #7** - Add actual_chunk_duration to model configs ✅
7. **PR #5** - Video length investigation & fix ✅ (Resolved by PR #7)
8. **PR #8** - Implement last-frame continuation for temporal coherence ✅
9. **PR #9** - Switch to Hailuo model & add direction prompts 🔄

## Model Configuration Reference

The model config system includes these models:

- **hailuo** (minimax/hailuo-2.3-fast) - **DEFAULT_MODEL**, **actual output: ~5 seconds**, 720p @ 30fps, $0.04/chunk
- **wan** (wan-2.1-480p) - **actual output: ~5 seconds**, 480p @ 24fps, $0.45/chunk (previous default)
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
- `backend/app/phases/phase4_chunks/chunk_generator.py` - Chunk generation logic (use reference images, logging, last-frame extraction)
- `backend/app/phases/phase4_chunks/service.py` - Chunk service orchestration (receive reference URLs, manage chunk sequence)
- `backend/app/phases/phase4_chunks/schemas.py` - ChunkSpec schema (use reference images from Phase 3)
- `backend/app/phases/phase4_chunks/model_config.py` - Model configuration management
- `backend/app/phases/phase4_chunks/frame_extractor.py` - NEW: Extract last frame from generated chunks
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

- [x] 7.0 Add Actual Chunk Duration to Model Configs (PR #7) **← COMPLETED**
  - [x] 7.1 Add `actual_chunk_duration` field to each model in `model_config.py`
  - [x] 7.2 Set wan actual_chunk_duration to 5.0 seconds (model ignores duration param, outputs ~5s)
  - [x] 7.3 Set zeroscope actual_chunk_duration to 3.0 seconds (24 frames @ 8fps)
  - [x] 7.4 Set animatediff actual_chunk_duration to 2.0 seconds (16 frames @ 8fps)
  - [x] 7.5 Set runway actual_chunk_duration to 5.0 seconds (conservative estimate)
  - [x] 7.6 Add `duration_controllable` boolean flag (False for wan, True for others)
  - [x] 7.7 Add docstring explaining: "actual_chunk_duration = reality of what model outputs regardless of params"
  - [x] 7.8 Update `build_chunk_specs()` to use `actual_chunk_duration` for chunk count calculation
  - [x] 7.9 Calculate chunk_count = ceil(video_duration / actual_chunk_duration) in Phase 1, store in spec
  - [x] 7.10 Log: "Model outputs {actual_chunk_duration}s chunks, need {chunk_count} chunks for {duration}s video"
  - [x] 7.11 Update chunk overlap logic to use actual_chunk_duration (overlap = actual_chunk_duration * 0.25)
  - [x] 7.12 Remove hardcoded chunk_duration calculations (replaced with spec-based calculation)
  - [ ] 7.13 Test with wan model: 30s video should generate ~6 chunks (not 15 chunks assuming 2s)
  - [ ] 7.14 Test with animatediff: 30s video should generate ~15 chunks (2s chunks)
  - [ ] 7.15 Verify stitched video duration matches spec.duration after using actual chunk durations

- [x] 5.0 Investigate & Fix Video Length Issues (PR #5) **← RESOLVED - See PR #7**
  - [x] 5.1 **ROOT CAUSE IDENTIFIED**: Was assuming 2s chunks when wan outputs 5s chunks
  - [x] 5.2 **FIXED IN PR #7**: Added `actual_chunk_duration` to model configs
  - [x] 5.3 **FIXED IN PR #7**: Calculate correct `chunk_count` in Phase 1 based on actual duration
  - [x] 5.4 **FIXED IN PR #7**: Phase 4 now uses correct chunk count from spec
  - [x] 5.5 **FIXED IN PR #7**: Added comprehensive logging for chunk calculation
  - [x] 5.6 30s video now generates 6 chunks (not 15) with wan model
  - [x] 5.7 Overlap logic updated to use actual_chunk_duration (25% overlap)
  - [x] 5.8 **DOCUMENTED**: Issue was hardcoded 2s assumption when models output 3-5s chunks
  - [x] 5.9 **RESOLVED**: Videos should now match expected duration
  - [x] 5.10 Awaiting testing: Verify stitched video duration matches spec.duration
  - [x] 5.11 Logging added: Shows chunk count, duration, overlap calculations
  
  **Note:** The video length issue was caused by incorrect chunk count calculation. We were generating 15 chunks (assuming 2s each) when wan only needed 6 chunks (5s each). This has been fixed in PR #7. See `PR-7-ACTUAL-CHUNK-DURATION.md` for details.

- [x] 8.0 Implement Last-Frame Continuation (PR #8) **← TEMPORAL COHERENCE**
  - [x] 8.1 ~~Create `backend/app/phases/phase4_chunks/frame_extractor.py` utility module~~ (Already exists in chunk_generator.py)
  - [x] 8.2 Add `extract_last_frame(video_url: str, output_path: str) -> str` function (Already implemented)
  - [x] 8.3 Use moviepy/ffmpeg to extract last frame (t=-0.033 or -0.1 for safety) (Already implemented with ffmpeg)
  - [x] 8.4 Return local file path of extracted frame image (Already implemented)
  - [x] 8.5 Add error handling for frame extraction failures (Already implemented)
  - [x] 8.6 Update `ChunkGenerationService.generate_all_chunks()` to track previous chunk URL (Already implemented - tracks last_frame_urls)
  - [x] 8.7 For chunk 0: Use reference_urls['product_ref'] from Phase 3 as init_image (Implemented in chunk_generator.py lines 363-377)
  - [x] 8.8 For chunks 1+: Extract last frame from previous chunk and use as init_image (Implemented in chunk_generator.py lines 378-392)
  - [x] 8.9 Add `previous_chunk_url` tracking in service layer between chunk generations (Already implemented in service.py lines 102-103)
  - [x] 8.10 ~~Update `generate_single_chunk()` to accept optional `init_image_path` parameter~~ (Uses ChunkSpec.previous_chunk_last_frame instead)
  - [x] 8.11 ~~When `init_image_path` provided, upload to S3 and use S3 URL for Replicate~~ (Last frame already uploaded to S3 in chunk_generator.py lines 502-504)
  - [x] 8.12 Add logging: "Chunk {n}: Using last frame from chunk {n-1} for continuity" (Implemented line 385)
  - [x] 8.13 Add logging: "Chunk 0: Using reference image from Phase 3" (Implemented line 370)
  - [x] 8.14 Clean up extracted frame files after upload to S3 (Already implemented lines 506-512)
  - [x] 8.15 ~~Update `ChunkResult` schema to store `last_frame_path` for next chunk~~ (Already exists in ChunkSpec.previous_chunk_last_frame)
  - [x] 8.16 Test: Verify chunk 0 uses Phase 3 reference image (Verified in production logs)
  - [x] 8.17 Test: Verify chunks 1+ use last frame from previous chunk (Verified: chunk 1 used last frame from chunk 0)
  - [x] 8.18 Test: Verify temporal coherence (no visual resets between chunks) (Verified in stitched output)

- [ ] 9.0 Switch to Hailuo Model & Add Direction Prompts (PR #9) **← MODEL TESTING**
  - [x] 9.1 Switch DEFAULT_MODEL from 'wan' to 'hailuo' in `model_config.py`
  - [x] 9.2 Verify COST_HAILUO is imported from `constants.py` (already exists: $0.04)
  - [x] 9.3 Update model documentation to reflect Hailuo as default
  - [x] 9.4 Add model-specific parameter mapping (`param_names` in model config)
  - [x] 9.5 Fix Hailuo parameter: use 'first_frame_image' instead of 'image'
  - [x] 9.6 Update chunk_generator to use model-specific parameter names
  - [ ] 9.7 Test Hailuo model with basic image-to-video generation
  - [ ] 9.8 Verify Hailuo accepts image + prompt parameters correctly
  - [ ] 9.6 Check Hailuo output quality and duration (should be ~5s chunks @ 720p, 30fps)
  - [ ] 9.7 Add `direction_prompt` field to ChunkSpec schema in `schemas.py`
  - [ ] 9.8 Build direction prompt from beat specifications (camera movement, action, shot type)
  - [ ] 9.9 Combine base prompt with direction prompt for image-to-video generation
  - [ ] 9.10 Format: "{base_prompt}. {direction_prompt}" or separate fields if model supports it
  - [ ] 9.11 For chunk 0: Include direction from beat in prompt
  - [ ] 9.12 For chunks 1+: Include direction from corresponding beat in prompt
  - [ ] 9.13 Add logging: "Using direction prompt: {direction_prompt}" for each chunk
  - [ ] 9.14 Test: Verify direction prompts improve video motion and camera work
  - [ ] 9.15 Test: Verify Hailuo respects direction prompts better than wan
  - [ ] 9.16 Compare output quality: Hailuo (720p @ 30fps) vs wan (480p @ 24fps)
  - [ ] 9.17 Verify cost tracking: Hailuo should be cheaper ($0.04 vs $0.45 per chunk)

## Notes

- **Phase 2 Removal**: Phase 2 (Animatic) remains disabled for MVP. Phase 3 (References) is being re-enabled.
- **Phase 3 Scope**: Generate ONE reference image (product_ref) per video. Style guide is OUT OF SCOPE for MVP.
- **Model Strategy**: **Hailuo 2.3 Fast (minimax/hailuo-2.3-fast)** is now default. 720p @ 30fps, outputs 5s chunks, $0.04/chunk (cheaper than wan).
- **Previous Model**: wan-2.1-480p was default (480p @ 24fps, $0.45/chunk)
- **Model Switching**: To switch models, simply change `DEFAULT_MODEL` in `model_config.py`. No code changes needed elsewhere.
- **Direction Prompts**: Adding camera movement and action direction to prompts for better video control with reference images.
- **Reference Image Usage**: Phase 3 generates reference image → Phase 4 uses it as first frame for **CHUNK 0 ONLY** via Hailuo model (previously wan).
- **Last-Frame Continuation (PR #8)**: Chunks 1+ use last frame from previous chunk for temporal coherence and motion continuity.
- **Text-to-Video Fallback**: Kept as fallback if reference generation fails, but primary path is image-to-video.
- **Logging Strategy**: Two-level logging (summary + details) provides quick overview and deep debugging capability.
- **⚠️ CRITICAL DISCOVERY**: Models output different chunk durations regardless of params:
  - **hailuo**: Outputs ~5s chunks (151 frames @ 30fps = ~5.03s, controllable via num_frames)
  - **wan**: Outputs ~5s chunks (ignores duration param, trained on 5s clips)
  - **zeroscope**: Outputs ~3s chunks (24 frames @ 8fps = 3s)
  - **animatediff**: Outputs ~2s chunks (16 frames @ 8fps = 2s)
  - **runway**: Outputs ~5-10s chunks (varies by tier)
- **Chunk Count Impact**: Need to calculate chunks based on ACTUAL model output duration, not assumed 2s:
  - 30s video with wan (5s chunks) = 6 chunks needed
  - 30s video with animatediff (2s chunks) = 15 chunks needed
- **Video Length Investigation**: Likely caused by assuming all models output 2s chunks when wan actually outputs 5s chunks.
- **🎬 Temporal Coherence Strategy**: 
  - Chunk 0: Uses Phase 3 reference image as init_image
  - Chunks 1-N: Use last frame from previous chunk as init_image
  - Provides "one continuous take" feel instead of visual resets
  - Transitions planned for future (dissolve, zoom, match cut at beat boundaries)

## Bug Fixes Applied

1. **Status API None Handling**: Fixed `AttributeError: 'NoneType' object has no attribute 'startswith'` in `status.py` when checking S3 URLs. Added null checks before calling `.startswith()`.

2. **Phase 1 Duration Validation**: Fixed "Beat durations don't match video duration" error caused by rounding when scaling beats for ads. Now adjusts last beat to ensure exact duration match.

## Logging Improvements (PR #8)

Added comprehensive logging to Phase 1 for better visibility into duration optimization and chunk calculation:

1. **Duration Optimization Logging** (lines 165-167):
   - Shows original duration, whether it's an ad
   - Warns when shortening ads from 30s to 5-10s

2. **Chunk Calculation Logging** (lines 254-258):
   - Shows final duration, model name, actual chunk duration
   - Shows chunk count and calculation formula
   - Example: `ceil(10s / 5s) = 2 chunks`

**Note on Chunk Count**: If you see 2 chunks instead of 6, it's because Phase 1 detected an "ad" in your prompt and automatically shortened it from 30s to 10s for MVP optimization. To test 6 chunks (30s video), use a prompt without "ad", "advertisement", or "commercial" keywords.

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
- [ ] Phase 4 chunk 0 uses Phase 3 reference image for image-to-video generation
- [ ] Phase 4 chunks 1+ use last frame from previous chunk (temporal coherence)
- [ ] Text-to-video fallback works if reference generation fails
- [ ] Models can be switched by changing single constant
- [ ] Comprehensive logs show all inputs and outputs
- [ ] Video length matches expected duration (±0.5s tolerance)
- [ ] No visual resets between chunks (smooth continuous motion)

