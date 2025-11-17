# Active Context

## Current Status
**Project Phase**: TDD Implementation - Beat-Based Architecture Refactor  
**TDD Version**: TDD-storyboarding.md (Version 2.0)  
**Date**: November 16, 2025  
**Day**: 2 (TDD Implementation)  
**Team Size**: 1 person (solo development)  
**Region**: AWS us-east-2 (Ohio)

## What Just Happened
1. ✅ **TDD-tasks-1.md PR #1 Complete**: Beat Library & Template Archetypes implemented
2. ✅ **Phase 2 Architecture Defined**: Storyboard generation replaces Phase 3 references
3. ✅ **TDD-tasks-2.md Updated**: Removed PR #4 (testing), clarified Phase 2→3 replacement
4. 🔄 **Starting TDD-tasks-2.md**: PR #4 & PR #5 - Phase 2 Storyboard + Phase 4 Integration
5. ⏸️ **Full Testing Postponed**: Will add comprehensive tests after core implementation

## Current Focus
**Planning TDD-tasks-2.md PRs #4 & #5: Phase 2 Storyboard Generation**

### Immediate Tasks (TDD PRs #4-5)
1. ✅ Define Phase 2 architecture (Option C: beat boundary images)
2. ✅ Update TDD-tasks-2.md with detailed implementation plan
3. 🔄 Disable Phase 3 explicitly (keep code, mark as disabled)
4. 🔄 Implement Phase 2 storyboard generation (1 image per beat)
5. 🔄 Update Phase 4 to use storyboard images at beat boundaries
6. 🔄 Update memory bank with architectural decisions

## Recent Decisions

### TDD Architecture Decisions (November 17, 2025)

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
   - Add ONLY `storyboard_images` field (JSON, list of image URLs)
   - Store `creativity_level`, `selected_archetype`, `num_beats`, `num_chunks` in `spec` JSON
   - Do NOT remove old fields yet (backward compat for existing data)
   - Do NOT modify `VideoStatus` enum (out of scope)
   - Migration executed LAST (after all TDD PRs)

4. **No Backward Compatibility for New Videos** ✅
   - Old videos in DB stay untouched (spec is JSON)
   - New videos use new spec format
   - No code to support old format generation
   - Clean break for forward progress

5. **Phase 2 Replaces Phase 3** ✅ NEW
   - OLD: Phase 3 generates 1 reference image per video
   - NEW: Phase 2 generates N storyboard images (1 per beat)
   - Phase 3 explicitly disabled but kept in codebase
   - Storyboard images stored in database `storyboard_images` field

6. **Beat-to-Chunk Mapping (Option C)** ✅ NEW
   - Storyboard images used at **beat boundaries only**
   - Within a beat: use last-frame continuation
   - Example: Beat 1 (10s) = Chunk 0 (storyboard) + Chunk 1 (last-frame)
   - Example: Beat 2 (5s) = Chunk 2 (storyboard from beat 2)
   - Algorithm: `chunk_idx = beat_start_time // actual_chunk_duration`
   - Maintains temporal coherence within beats
   - Provides visual reset at narrative boundaries

7. **Testing Strategy** ✅ NEW
   - Comprehensive testing deferred until after core implementation
   - Focus on getting system working end-to-end first
   - Will add full test suite after PRs #4-5 complete
   - Integration testing with real APIs as primary validation

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

### Immediate (TDD PRs #4-5) - CURRENT
1. 🔄 Disable Phase 3 explicitly (add comments, return skipped status)
2. 🔄 Create Phase 2 directory structure
3. 🔄 Implement Phase 2 storyboard generation (1 image per beat)
4. 🔄 Update Phase 4 to calculate beat-to-chunk mapping
5. 🔄 Update Phase 4 to use storyboard images at beat boundaries

### Short Term (After PRs #4-5)
1. Test Phase 1 → Phase 2 → Phase 4 pipeline
2. Verify beat boundary images working correctly
3. Verify last-frame continuation within beats
4. Update orchestrator/pipeline to call Phase 2 (not Phase 3)
5. End-to-end test with various beat sequences

### Medium Term (TDD Completion)
1. Add comprehensive test suite
2. Execute database migration
3. Update frontend to show storyboard images
4. Performance optimization (parallel generation within beats)
5. Fix any remaining Phase 5 S3 path issues

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

