# Phase 2 Storyboard Implementation Plan

## Overview

Phase 2 storyboard generation **replaces** the old Phase 3 reference generation system. This document outlines the architectural decisions and implementation plan.

## Architectural Decision: Option C - Beat Boundary Images

### The Problem
- **OLD System**: Phase 3 generated 1 reference image per video
- **Challenge**: How to map N beat storyboard images to M video chunks?

### The Solution: Beat Boundary Images + Last-Frame Continuation

**Core Principle**: Storyboard images are used at **beat boundaries only**, with last-frame continuation within beats.

### Example 1: Simple Case (All 5s Beats)
```
Video: 15s total
Beats: 3 beats (5s + 5s + 5s)
Chunks: 3 chunks (5s each with wan model)

Beat 0 (0-5s)  → Chunk 0: Storyboard Image 0
Beat 1 (5-10s) → Chunk 1: Storyboard Image 1
Beat 2 (10-15s) → Chunk 2: Storyboard Image 2
```

### Example 2: Mixed Duration Beats
```
Video: 20s total
Beats: 3 beats (10s + 5s + 5s)
Chunks: 4 chunks (5s each)

Beat 0 (0-10s):
  - Chunk 0 (0-5s): Storyboard Image 0 ← Beat boundary
  - Chunk 1 (5-10s): Last frame from Chunk 0 ← Within beat
Beat 1 (10-15s):
  - Chunk 2 (10-15s): Storyboard Image 1 ← Beat boundary
Beat 2 (15-20s):
  - Chunk 3 (15-20s): Storyboard Image 2 ← Beat boundary
```

### Benefits of Option C

1. **Narrative Structure**: Visual refresh at story beats
2. **Temporal Coherence**: Smooth motion within beats
3. **Follows TDD**: 1:1 beat-to-image mapping preserved
4. **Scalable**: Works with any beat/chunk duration combination

## Algorithm: Beat-to-Chunk Mapping

```python
def calculate_beat_to_chunk_map(beats, actual_chunk_duration):
    """
    Calculate which chunks start new beats.
    
    Returns:
        dict: {chunk_idx: beat_idx} for chunks that start beats
    """
    beat_to_chunk = {}
    current_time = 0
    
    for beat_idx, beat in enumerate(beats):
        chunk_idx = current_time // actual_chunk_duration
        beat_to_chunk[chunk_idx] = beat_idx
        current_time += beat['duration']
    
    return beat_to_chunk

# Example usage:
beats = [
    {'duration': 10, ...},  # Beat 0
    {'duration': 5, ...},   # Beat 1
    {'duration': 5, ...}    # Beat 2
]
actual_chunk_duration = 5  # wan model

result = calculate_beat_to_chunk_map(beats, actual_chunk_duration)
# result = {0: 0, 2: 1, 3: 2}
# Chunk 0 starts beat 0
# Chunk 2 starts beat 1
# Chunk 3 starts beat 2
```

## Implementation Tasks

### PR #4: Phase 2 Storyboard Generation

**Task 4.0: Disable Phase 3**
- Add explicit comment block at top of `phase3_references/task.py`
- Keep code but return "skipped" status immediately
- Maintain backward compatibility for old videos

**Task 4.1-4.6: Implement Phase 2**
1. Create `phase2_storyboard/` directory
2. Implement `image_generation.py` helper (SDXL generation)
3. Implement `task.py` main task (loop through beats)
4. Store results in `storyboard_images` database field

**Phase 2 Output Format:**
```python
{
    "storyboard_images": [
        {
            "beat_id": "hero_shot",
            "beat_index": 0,
            "start": 0,
            "duration": 10,
            "image_url": "s3://bucket/users/{user_id}/videos/{video_id}/storyboard/beat_00.png",
            "shot_type": "close_up",
            "prompt_used": "Cinematic close-up of Nike sneakers..."
        },
        {
            "beat_id": "product_in_motion",
            "beat_index": 1,
            "start": 10,
            "duration": 5,
            "image_url": "s3://bucket/.../beat_01.png",
            "shot_type": "tracking",
            "prompt_used": "Tracking shot of Nike sneakers in motion..."
        },
        ...
    ]
}
```

### PR #5: Phase 4 Integration

**Task 5.1: Calculate Beat-to-Chunk Mapping**
- Implement algorithm in Phase 4 task
- Read `storyboard_images` from Phase 2 output
- Calculate which chunks start new beats

**Task 5.2: Update Chunk Generation**
- For each chunk, check if it's in `beat_to_chunk_map`
- If yes: Use `storyboard_images[beat_idx]['image_url']` as init_image
- If no: Use last frame from previous chunk (existing logic)
- Log which source is used for each chunk

## Phase 3 Transition

### What Happens to Phase 3?

**Status**: Explicitly disabled but kept in codebase

**Rationale**:
1. Backward compatibility for old videos
2. May need for debugging/comparison
3. Clean git history (shows what was replaced)
4. Can be deleted in future cleanup PR

**Implementation**:
```python
# phase3_references/task.py

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

@celery_app.task(bind=True)
def generate_references(self, video_id: str, spec: dict, user_id: str = None):
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

## Pipeline Flow (Updated)

```
User Prompt
    ↓
Phase 1: Planning (GPT-4)
    - Selects archetype
    - Composes beat sequence
    - Validates durations
    ↓
Phase 2: Storyboard (SDXL) ← NEW!
    - Generates 1 image per beat
    - Stores in database
    ↓
Phase 3: References ← DISABLED
    - Returns "skipped" immediately
    ↓
Phase 4: Chunks (wan/zeroscope)
    - Calculates beat-to-chunk map
    - Uses storyboard images at beat boundaries
    - Uses last-frame continuation within beats
    ↓
Phase 5: Refinement
    - Stitches chunks
    - Applies effects
    ↓
Phase 6: Export
    - Final video delivery
```

## Cost Comparison

### OLD System (Phase 3 Reference)
- 1 reference image per video
- Cost: $0.025 (FLUX Dev)
- Time: ~15s

### NEW System (Phase 2 Storyboard)
- N images (1 per beat)
- Cost: $0.0055 × N (SDXL)
- Time: ~8s × N

**Examples**:
- 3 beats: $0.017 (cheaper!)
- 6 beats: $0.033 (slightly more)
- Average 3-5 beats: Similar or cheaper

## Testing Strategy

**Deferred until after implementation**:
- Focus on getting core system working first
- Will add comprehensive tests after PRs #4-5
- Use integration testing with real APIs as primary validation

**Key Test Cases** (later):
1. Simple case: 3 beats (5s each) = 3 chunks
2. Mixed durations: 3 beats (10s + 5s + 5s) = 4 chunks
3. Long beats: 2 beats (15s each) = 6 chunks
4. Verify storyboard images used at correct chunks
5. Verify last-frame continuation within beats

## Success Criteria

- [ ] Phase 3 explicitly disabled
- [ ] Phase 2 generates N storyboard images (1 per beat)
- [ ] Storyboard images stored in database
- [ ] Phase 4 calculates beat-to-chunk mapping correctly
- [ ] Phase 4 uses storyboard images at beat boundaries
- [ ] Phase 4 uses last-frame continuation within beats
- [ ] All S3 uploads work correctly
- [ ] Cost calculation accurate
- [ ] End-to-end test: Prompt → Phase 1 → Phase 2 → Phase 4 → Video

## Next Steps

1. ✅ Planning complete (this document)
2. ✅ Task file updated (`TDD-tasks-2.md`)
3. ✅ Memory bank updated (architecture decisions)
4. 🔄 Start implementation (PR #4)
5. 🔄 Phase 4 integration (PR #5)
6. 🔄 End-to-end testing
7. 🔄 Add comprehensive test suite (later)

---

**Last Updated**: November 17, 2025  
**Status**: Planning Complete, Ready for Implementation

