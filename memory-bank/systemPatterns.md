# System Patterns

## Architecture Overview

### High-Level Pattern
**Hybrid Deterministic-Generative Architecture**
- Templates provide structure and reliability
- AI fills in creative content within constraints
- Best of both worlds: consistency + creativity

### Team Collaboration Pattern (PRD v2.0)
**Phase-Based Vertical Slices**
- 3-person team, each owns 2 complete phases
- Zero merge conflicts (separate directories)
- Parallel development from Day 1
- Shared contracts defined upfront (`common/`)

**Ownership:**
- Person A: `phases/phase1_validate/` + `phases/phase2_animatic/` + `features/generate/`
- Person B: `phases/phase3_references/` + `phases/phase4_chunks/` + `features/progress/`
- Person C: `phases/phase5_refine/` + `phases/phase6_export/` + `features/video/`

### Deployment Pattern
**Multi-Tier AWS Architecture (us-east-2)**
```
Frontend (S3 + CloudFront)
    ↓
API Gateway (ALB)
    ↓
Web Tier (Elastic Beanstalk - FastAPI)
    ↓
Job Queue (ElastiCache Redis)
    ↓
Worker Tier (Elastic Beanstalk - Celery)
    ↓
Storage (S3) + Database (RDS Postgres)
```

**Visual Diagrams:**
- `architecture-deployment.mermaid` - Full AWS infrastructure
- `architecture-pipeline.mermaid` - Six-phase workflow

## Core Design Patterns

### 1. Pipeline Pattern (Six-Phase Processing)

Each video generation flows through 6 sequential phases:

**Phase 1: Intelligent Planning (TDD v2.0)**
- Input: Natural language prompt + creativity level (0.0-1.0)
- Process: Single GPT-4 call performs:
  1. Analyze user intent
  2. Select archetype from library (5 options)
  3. Compose beat sequence from beat library (15 beats)
  4. Build style specification
- Output: Complete spec with beats, each beat 5/10/15s duration
- Cost: $0.02 | Time: 5-10s
- Key Change: LLM composes custom sequences, not just template selection

**Phase 2: Storyboard Generation (TDD v2.0)** ✅ ACTIVE
- Input: Spec with beats from Phase 1
- Process: Generate 1 SDXL image per beat (1:1 mapping)
- Output: N storyboard images (N = number of beats)
- Cost: $0.0055 per image | Time: ~8s per image
- Key Change: REPLACES Phase 3 reference generation
- Images used at beat boundaries in Phase 4
- Example: 3 beats = 3 images, 6 beats = 6 images

**Phase 3: Reference Assets** ❌ DISABLED (TDD v2.0)
- Status: Explicitly disabled, kept in codebase for backward compatibility
- OLD: Generated 1 reference image per video
- NEW: Phase 2 storyboard images replace this functionality
- Function returns "skipped" status immediately
- May be removed entirely in future refactor

**Phase 4: Chunked Video Generation (TDD v2.0)** ✅ UPDATED
- Input: Spec + Storyboard Images (from Phase 2)
- Process: Generate video chunks with dynamic beat-boundary mapping
- Init Image Strategy (Option C):
  - Chunks at beat boundaries: Use storyboard image from Phase 2
  - Chunks within beats: Use last-frame continuation
  - Example: Beat 1 (10s) = Chunk 0 (storyboard) + Chunk 1 (last-frame)
- **Dynamic Mapping**: Phase 4 adapts to any number of storyboard images
  - No hardcoded thresholds - works with 1, 3, 10, or any number of images
  - Beat-to-chunk mapping calculated from actual beat start times
  - Gracefully handles partial images (uses available, falls back for missing)
- Output: N video chunks (depends on total duration and model)
- Cost: $0.04 per 5s chunk (hailuo) | Time: ~45s per chunk
- Pattern: Sequential generation for temporal coherence

**Phase 5: Refinement**
- Input: Stitched video
- Process: Temporal smoothing, upscaling, color grading, audio sync
- Output: Polished final video
- Cost: $0.15 | Time: 2 minutes

**Phase 6: Export**
- Input: Final video
- Process: Upload to S3, generate pre-signed URLs
- Output: Downloadable video

### 2. Beat Library System Pattern (TDD v2.0)

**Beat-Based Composition Architecture**
- **15-Beat Library**: Reusable shot types organized by position (opening/middle/closing)
- **LLM Composer**: GPT-4 selects archetype and composes custom beat sequences
- **Strict Duration Constraint**: All beats must be 5s, 10s, or 15s (no exceptions)
- **1:1 Beat-to-Storyboard Mapping**: Each beat = 1 SDXL-generated storyboard image

**OLD System (Deprecated):**
- JSON template files with embedded beats
- Template selection (choose from 3 templates)
- Arbitrary beat durations (3s, 5s, 7s, 10s)
- Duration optimization logic in service layer

**NEW System (TDD v2.0):**
```python
# Beat Library Structure
{
    "beat_id": "hero_shot",
    "duration": 5,  # MUST be 5, 10, or 15
    "shot_type": "close_up",
    "action": "product_reveal",
    "prompt_template": "Cinematic close-up of {product_name}...",
    "camera_movement": "slow_dolly_in",
    "typical_position": "opening",
    "compatible_products": ["all"],
    "energy_level": "medium"
}

# Template Archetypes (High-Level Guides)
{
    "archetype_id": "luxury_showcase",
    "suggested_beat_sequence": ["hero_shot", "detail_showcase", ...],
    "typical_duration_range": (15, 30),
    "energy_curve": "steady",
    "narrative_structure": "reveal → appreciate → aspire → desire"
}
```

**Key Differences:**
- Templates are now **guides**, not rigid structures
- LLM **composes** beat sequences, doesn't just fill in placeholders
- Beats are **reusable** across different video types
- All durations conform to 5/10/15s constraint for chunk alignment

### 3. Temporal Consistency Pattern

**Beat Boundary Images + Last-Frame Continuation (TDD v2.0)** ✅ ACTIVE
- **Beat Boundaries**: Use storyboard images from Phase 2
  - Each beat starts with its corresponding storyboard image
  - Provides visual refresh at narrative transitions
  - Example: Chunk 0 (beat 1), Chunk 2 (beat 2), Chunk 3 (beat 3)
- **Within Beats**: Use last-frame continuation
  - Maintains temporal coherence during the beat
  - Smooth motion within narrative segment
  - Example: Beat 1 (10s) = Chunk 0 (storyboard) + Chunk 1 (last-frame)
- **Dynamic Mapping Algorithm**: 
  ```python
  # Uses actual beat['start'] values from Phase 1 (not recalculated)
  beat_to_chunk = {}
  for beat_idx, beat in enumerate(beats):
      beat_start = beat.get('start', 0.0)
      chunk_spacing = actual_chunk_duration * 0.75  # 25% overlap
      chunk_idx = int(beat_start // chunk_spacing)
      # Only map if chunk actually starts at beat (within 0.5s tolerance)
      if abs(chunk_idx * chunk_spacing - beat_start) < 0.5:
          beat_to_chunk[chunk_idx] = beat_idx
  ```
- **Key Features**:
  - Dynamically adapts to any number of storyboard images
  - No hardcoded assumptions about image count
  - Handles partial images gracefully (warns but continues)
  - Falls back to old logic only if 0 images found
- Result: Narrative structure + temporal coherence
- Trade-off: Sequential generation required (slower but better)

**OLD: Phase 3 Single Reference (PR #8)** ❌ DEPRECATED
- Chunk 0: Uses Phase 3 reference image
- Chunks 1+: Use last frame continuation
- Replaced by beat boundary system (more dynamic)

### 4. Processing Pattern Evolution

**Current: Two-Phase Parallel Generation (PR #9)** ✅ ACTIVE
- **Phase 1**: All reference image chunks generated in parallel
  - Chunks that start beats (use storyboard images)
  - Independent of each other, can all start together
  - Example: Chunks 0, 2, 4 (if beats start at those chunks)
- **Phase 2**: All continuous chunks generated in parallel (after Phase 1)
  - Chunks within beats (use last frame from reference chunk)
  - Each uses its reference chunk's last frame
  - Example: Chunks 1, 3 (continuous chunks)
- **Technology**: LangChain RunnableParallel for I/O-bound operations
- **Architecture**: Celery for pipeline orchestration, LangChain for chunk parallelism
- **Performance**: 40-50% faster than sequential while maintaining temporal coherence
- **Key Design**: Chunk generation functions are regular functions (not Celery tasks)

**Previous: Sequential Generation (PR #8)** ❌ DEPRECATED
- Chunks generated one at a time (0, 1, 2, 3, ...)
- Required for last-frame continuation
- Each chunk needs previous chunk's last frame
- Slower but ensures temporal coherence
- Generation time: ~45s × chunk_count
- Replaced by two-phase parallel approach

**Original: Parallel Generation (Deprecated)**
- All chunks generated simultaneously
- Fast but no temporal continuity between chunks
- Caused visual resets and inconsistency
- Replaced by sequential approach (now replaced by two-phase parallel)

### 5. Model Reality Pattern (PR #7)

**Actual vs Requested Duration**
- **Critical Discovery**: Models output different durations regardless of parameters
- **wan**: Outputs ~5s chunks (ignores duration param, trained on 5s clips)
- **zeroscope**: Outputs ~3s chunks (24 frames @ 8fps)
- **animatediff**: Outputs ~2s chunks (16 frames @ 8fps)
- **runway**: Outputs ~5-10s chunks (varies by tier)

**Chunk Count Calculation**
```python
# WRONG (old approach):
chunk_count = video_duration / 2  # Assumed all models output 2s

# RIGHT (PR #7):
model_config = get_default_model()
actual_chunk_duration = model_config['actual_chunk_duration']
chunk_count = math.ceil(video_duration / actual_chunk_duration)

# Example: 30s video with wan (5s chunks) = 6 chunks (not 15!)
```

**Impact**: Must use actual_chunk_duration for accurate planning
- Affects chunk count calculation
- Affects overlap calculations  
- Affects cost estimation
- Affects generation time estimation

### 6. Progressive Enhancement Pattern

**Low-to-High Fidelity**
- Development: Use wan ($0.09/s, fast, 480p)
- Final: Can switch to higher quality models
- Allows rapid iteration during development
- Model switching via single constant change

## Data Flow Patterns

### 1. Job Queue Pattern
- Web tier submits job to Redis queue
- Returns immediately with video_id
- Worker tier pulls jobs and processes
- Results stored in Redis + PostgreSQL
- Client polls for status updates

### 2. Asset Storage Pattern
```
/videos/:video_id/
  ├── animatic/
  │   ├── frame_00.png through frame_14.png
  ├── references/
  │   ├── style_guide.png
  │   ├── product.png
  ├── chunks/
  │   ├── chunk_00.mp4 through chunk_14.mp4
  └── final.mp4
```

### 3. Cleanup Pattern
- Keep animatic and chunks during generation
- Delete after final video is complete
- Reduces storage costs
- Keeps only final.mp4 long-term

## Error Handling Patterns

### 1. Retry with Exponential Backoff
- Replicate API calls can fail due to rate limits
- Retry up to 3 times with increasing delays
- If still fails, mark video as failed with clear error

### 2. Partial Recovery
- If single chunk fails, regenerate only that chunk
- Don't restart entire pipeline
- Saves time and cost

### 3. Graceful Degradation
- If music generation fails, continue without audio
- Better to deliver video without music than fail completely

## Integration Patterns

### 1. External API Abstraction
- Wrap all external APIs (Replicate, OpenAI, S3) in service classes
- Centralizes error handling and retry logic
- Makes it easy to swap providers

### 2. Progress Tracking
- Each phase updates database with status and progress %
- Frontend polls /api/status/:video_id every 3 seconds
- Real-time feedback to user

### 3. Cost Tracking
- Track cost at each phase
- Store breakdown in database
- Enables cost analytics and optimization

## Testing Patterns

### 1. Unit Tests
- Test each phase independently
- Mock external API calls
- Fast, reliable, cheap

### 2. Integration Tests
- Test full pipeline with real APIs
- Use small, cheap inputs (10s videos)
- Run nightly, not on every commit

### 3. Load Tests
- Simulate concurrent users
- Verify queue system handles load
- Test auto-scaling behavior

## Scalability Patterns

### 1. Horizontal Scaling
- Workers scale independently from web tier
- Add more worker instances during peak load
- Elastic Beanstalk auto-scaling based on queue depth

### 2. Queue-Based Load Leveling
- Jobs queued in Redis
- Workers pull at their own pace
- Prevents overload, ensures fair processing

### 3. CDN for Static Assets
- Frontend served via CloudFront
- Final videos served via pre-signed S3 URLs with CloudFront
- Reduces latency, improves user experience

## Security Patterns

### 1. Pre-Signed URLs
- Don't expose S3 bucket publicly
- Generate time-limited URLs for downloads
- Prevents unauthorized access

### 2. Input Validation
- Validate prompt length, format
- Sanitize user inputs before sending to AI
- Prevent prompt injection attacks

### 3. Rate Limiting
- 1 video per user concurrently (MVP)
- Prevents abuse and cost overruns
- Can be lifted post-competition

