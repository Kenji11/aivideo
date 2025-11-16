# Active Context

## Current Status
**Project Phase**: TDD Implementation - Beat-Based Architecture Refactor  
**TDD Version**: TDD-storyboarding.md (Version 2.0)  
**Date**: November 16, 2025  
**Day**: 2 (TDD Implementation)  
**Team Size**: 1 person (solo development)  
**Region**: AWS us-east-2 (Ohio)

## What Just Happened
1. ✅ **TDD Created**: New beat-based architecture design complete
2. ✅ **Implementation Strategy Defined**: Complete replacement of Phase 1
3. 🔄 **Starting TDD-tasks-1.md**: PR #1 - Beat Library & Template Archetypes
4. ⏸️ **Previous MVP Paused**: Refactoring to beat-based system
5. ⏸️ **Testing Postponed**: Will resume after TDD implementation

## Current Focus
**Implementing TDD-tasks-1.md PR #1: Beat Library & Template Archetypes**

### Immediate Tasks (TDD PR #1)
1. ✅ Review TDD and align on implementation strategy
2. 🔄 Create beat library module (`beat_library.py`) - 15 beats
3. 🔄 Create template archetypes module (`template_archetypes.py`) - 5 archetypes
4. 🔄 Update constants for creativity control
5. 🔄 Plan database migration (execute last)

## Recent Decisions

### TDD Architecture Decisions (November 16, 2025)

1. **Complete Phase 1 Replacement** ✅
   - DELETE old template JSON files (product_showcase.json, lifestyle_ad.json, announcement.json)
   - DELETE old service methods (template selection, duration optimization)
   - KEEP directory structure (`phase1_validate/` - no renaming)
   - Replace with beat library + LLM composition system

2. **Strict TDD Adherence** ✅
   - ALL beat durations MUST be 5s, 10s, or 15s (no exceptions)
   - LLM composes beat sequences (no hardcoded logic)
   - 15 beats in library (5 opening, 5 product, 3 dynamic, 2 closing)
   - 5 template archetypes as high-level guides

3. **Database Strategy** ✅
   - Add new fields: `creativity_level`, `selected_archetype`, `storyboard_images`, `num_beats`, `num_chunks`
   - Do NOT remove old fields yet (backward compat for existing data)
   - Migration executed LAST (after all TDD PRs)
   - `spec` JSON column handles format changes automatically

4. **No Backward Compatibility for New Videos** ✅
   - Old videos in DB stay untouched (spec is JSON)
   - New videos use new spec format
   - No code to support old format generation
   - Clean break for forward progress

5. **Phase Integration Deferred** ✅
   - Don't worry about Phases 2-6 integration yet
   - Focus on Phase 1 correctness first
   - Other phases will adapt to new spec format later

### Key Implementation Decisions (November 15, 2025)

1. **PR #8: Last-Frame Continuation** ✅
   - Chunk 0: Uses Phase 3 reference image as init_image
   - Chunks 1+: Use last frame from previous chunk as init_image
   - Why: Eliminates visual resets, creates temporal coherence
   - Result: "One continuous take" feel instead of slideshow

2. **Phase 2 Disabled for MVP** ✅
   - Animatic generation temporarily removed
   - Phase 3 (References) re-enabled instead
   - Why: Simpler workflow, faster iteration
   - One reference image per video (not per beat)

3. **Model Configuration System** (PR #2) ✅
   - Centralized model configs with actual_chunk_duration
   - DEFAULT_MODEL = 'wan' (wan-2.1-480p image-to-video)
   - Why: Easy model switching, accurate chunk count calculation

4. **Chunk Count Calculation** (PR #7) ✅
   - Fixed: Calculate based on actual model output duration
   - wan: 5s chunks (not 2s) → 30s video = 6 chunks
   - animatediff: 2s chunks → 30s video = 15 chunks
   - Why: Models ignore duration params, must use reality

5. **Duration Optimization Logic** (Today) ✅
   - Respect user-specified durations (extracted by GPT-4)
   - Only optimize ads when user doesn't specify duration
   - Why: User intent should override automatic optimization

6. **Sequential Chunk Generation** (PR #8) ✅
   - Generate chunks one at a time (not in parallel)
   - Why: Need previous chunk's last frame for next chunk
   - Trade-off: Slower but better quality (temporal coherence)

7. **Logging Enhancements** (PR #4 + PR #8) ✅
   - Phase 1: Duration optimization + chunk calculation
   - Phase 4: Init image selection per chunk
   - Why: Better debugging and transparency

### New Beat-Based Strategy (TDD)
**15-Beat Library:**
- 5 Opening: hero_shot, ambient_lifestyle, teaser_reveal, dynamic_intro, atmospheric_setup
- 5 Product: detail_showcase, product_in_motion, usage_scenario, lifestyle_context, feature_highlight_sequence
- 3 Dynamic: action_montage, benefit_showcase, transformation_moment
- 2 Closing: call_to_action, brand_moment

**5 Template Archetypes:**
1. **luxury_showcase**: Elegant, cinematic, premium goods
2. **energetic_lifestyle**: Dynamic, active, motivational
3. **minimalist_reveal**: Clean, simple, focused
4. **emotional_storytelling**: Narrative, connection, transformation
5. **feature_demo**: Informative, benefit-driven, professional

## Next Steps

### Immediate (TDD PR #1)
1. 🔄 Create `beat_library.py` with 15 beats
2. 🔄 Create `template_archetypes.py` with 5 archetypes
3. 🔄 Update `constants.py` with creativity controls
4. 🔄 Plan database migration (fields list)
5. 🔄 Update memory bank with decisions

### Short Term (TDD PRs #2-3)
1. Phase 1 structure & validation (PR #2)
2. Phase 1 LLM agent implementation (PR #3)
3. System prompt builder
4. Spec validation & builder
5. Test with multiple prompts

### Medium Term (After TDD)
1. Update Phases 2-6 to work with new spec format
2. Execute database migration
3. Resume testing with new system
4. Performance optimization (parallel generation)
5. Fix Phase 5 S3 path issue

### Known Issues to Address
1. **Phase 5 S3 Path**: Stitched video not found (404 error)
   - Likely bucket name mismatch or path format issue
   - Need to verify S3 client configuration

2. **Performance**: Sequential generation is slow
   - 6 chunks × ~45s each = ~4.5 minutes just for generation
   - Could optimize: Generate chunk 0, then parallelize chunks 1-5
   - Trade-off: Complexity vs speed

3. **Duration Override**: Now fixed, needs testing
   - User-specified "30 seconds" should work
   - GPT-4 extracts duration from prompt
   - Phase 1 respects user intent

## Active Considerations

### Cost Management
- Budget: ~$1/video for testing (2 chunks @ $0.45 each)
- wan model: $0.09/second of video output
- 30s video (6 chunks × 5s) = ~$2.70
- Phase 3 reference: $0.025 per generation
- Current: Testing with 10s videos to save costs

### Quality vs Speed Tradeoffs  
- **Current**: Sequential generation for temporal coherence
- **Future**: Hybrid approach - chunk 0 first, then parallel chunks 1-5
- **Trade-off**: 6× slower but smooth motion continuity
- Generation time: ~45s per chunk × 6 = ~4.5 minutes

### Technical Achievements
1. ✅ **Temporal Coherence**: Last-frame continuation working
2. ✅ **Model Reality**: Accurate chunk duration calculations
3. ✅ **User Intent**: Duration override bug fixed
4. ✅ **Comprehensive Logging**: Easy debugging and monitoring
5. ✅ **Phase 3 Integration**: Reference image generation working

## Current Blockers
1. **Phase 5 S3 Path Issue**: Refinement can't find stitched video
   - Error: 404 Not Found when downloading from S3
   - Need to verify bucket name and path format

## Success Indicators (Tracking Progress)
- [x] Local Docker Compose working
- [x] First successful prompt validation (Phase 1)
- [x] Phase 3 reference image generated
- [x] First video chunk generated (Phase 4)
- [x] Last-frame continuation working
- [x] 2-chunk video generated successfully (10s)
- [ ] 6-chunk video generated successfully (30s)
- [ ] Phase 5 refinement working
- [ ] First complete polished video
- [ ] Deploy optimizations (parallel after chunk 0)

## Notes
- PR #8 (Last-Frame Continuation) successfully implemented and tested
- Pipeline working end-to-end (Phase 1 → 3 → 4)
- Phase 2 disabled for MVP, may re-enable later
- wan model outputs 5s chunks regardless of parameters
- Sequential generation ensures temporal coherence
- User-specified durations now respected by Phase 1

