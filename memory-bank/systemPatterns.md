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
- Person C: `phases/phase4_refine/` + `phases/phase6_export/` + `features/video/`

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
- Input: Spec with beats from Phase 1 + reference_mapping (from Phase 1)
- Process: Generate 1 image per beat (1:1 mapping) with dual-path generation
  - **ControlNet Path** (when product reference exists):
    - Download product image from S3
    - Preprocess with Canny edge detection (OpenCV)
    - Generate with flux-dev-controlnet ($0.058/image)
  - **Regular Path** (no product reference):
    - Generate with regular flux-dev ($0.025/image)
- Output: N storyboard images (N = number of beats)
- Cost: $0.025 (regular) or $0.058 (ControlNet) per image | Time: ~8s per image
- Key Change: REPLACES Phase 3 reference generation, adds ControlNet for product consistency
- Images used at beat boundaries in Phase 4
- Example: 3 beats = 3 images, 6 beats = 6 images
- Reference Mapping: Uses beat_ids as keys to look up product references per beat

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
- **Parallel Generation**: LangChain RunnableParallel for I/O-bound operations
  - Two-phase execution: Reference chunks (parallel) → Continuous chunks (parallel)
  - 40-50% faster generation while maintaining temporal coherence
- Output: N video chunks (depends on total duration and model)
- Cost: $0.04 per 5s chunk (hailuo) | Time: ~45s per chunk (parallelized)
- Pattern: Parallel generation for reference/continuous chunks within single Celery task

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

### 5. Processing Pattern Evolution

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

### 6. Model Reality Pattern (PR #7)

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

### 7. Progressive Enhancement Pattern

**Low-to-High Fidelity**
- Development: Use wan ($0.09/s, fast, 480p)
- Final: Can switch to higher quality models
- Allows rapid iteration during development
- Model switching via single constant change

## Data Flow Patterns

### 1. Job Queue Pattern (PR #10) ✅ UPDATED
- Web tier submits job to Redis queue
- Returns immediately with video_id
- Worker tier pulls jobs and processes
- **Progress Updates**: Stored in Redis during pipeline (60min TTL)
- **Final State**: Stored in PostgreSQL (start, failure, completion)
- **Status Updates**: Client connects via SSE stream for real-time updates
- **Fallback**: Client automatically falls back to polling if SSE unavailable

### 2. Asset Storage Pattern

**Video Assets (Legacy):**
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

**Reference Assets (PR #1):**
```
{user_id}/assets/
  ├── nike_sneaker.png              # Original image (user's filename preserved)
  ├── nike_sneaker_thumbnail.jpg     # Auto-generated thumbnail (400x400)
  └── nike_sneaker_edges.png        # Preprocessed edges (optional, future)
```
- Flat structure: `{user_id}/assets/{filename}` (no asset_id in path)
- S3 key remains unchanged when user edits asset name (only DB `name` field updates)
- Helper functions: `get_asset_s3_key()`, `get_asset_thumbnail_s3_key()`

### 3. Semantic Search Pattern (PR #3) ✅ NEW

**CLIP Embedding System:**
- **Text Embeddings**: CLIP text encoder converts queries to 512-dim vectors
- **Image Embeddings**: CLIP vision encoder converts images to 512-dim vectors
- **Storage**: pgvector `vector(512)` column in `assets` table
- **Similarity Metric**: Cosine distance (`<=>` operator in PostgreSQL)

**Search Types:**
1. **Text-to-Image Search** (`search_assets_by_text`)
   - Query: "blue energy drink can"
   - Process: Generate text embedding → compare to image embeddings
   - Threshold: 0.25 (25%) minimum similarity
   - Use case: Finding assets by description
   - Performance: Lower scores (0.2-0.5 typical) due to text-to-image gap

2. **Image-to-Image Similarity** (`find_similar_assets`)
   - Query: Reference asset ID
   - Process: Get reference embedding → compare to other image embeddings
   - Threshold: 0.7 (70%) minimum similarity
   - Use case: Finding visually similar assets
   - Performance: Higher scores (0.7-0.95 typical) - CLIP excels at image comparison

3. **Style Consistency** (`recommend_style_consistent_assets`)
   - Query: List of selected asset IDs
   - Process: Calculate centroid embedding → find assets near centroid
   - Use case: Recommending assets that match selected style
   - Performance: Similar to image-to-image (high scores)

**Key Implementation Details:**
- Raw SQL queries for pgvector operations (SQLAlchemy doesn't support vector type directly)
- Similarity score calculation: `1 - (embedding <=> query_embedding)` (cosine similarity)
- Results ordered by cosine distance (ascending = most similar first)
- Filters: `user_id`, `source = 'USER_UPLOAD'`, `embedding IS NOT NULL`
- Enum compatibility: Use `AssetSource.USER_UPLOAD.name` for database enum labels

### 4. Cleanup Pattern
- Keep animatic and chunks during generation
- Delete after final video is complete
- Reduces storage costs
- Keeps only final.mp4 long-term

## Error Handling Patterns

### 1. Enum Compatibility Pattern (PR #3) ✅ NEW
- **Problem**: PostgreSQL enum labels (uppercase) don't match Python enum values (lowercase)
- **Solution**: Use `.name` property for database operations
  - `AssetSource.USER_UPLOAD.name` → `"USER_UPLOAD"` (database enum label)
  - `AssetSource.USER_UPLOAD.value` → `"user_upload"` (Python enum value)
- **Application**: Raw SQL queries, SQLAlchemy ORM filters, asset creation
- **Note**: Model column is `String(20)` but database still uses enum type (migration deferred)

### 2. Retry with Exponential Backoff
- Replicate API calls can fail due to rate limits
- Retry up to 3 times with increasing delays
- If still fails, mark video as failed with clear error

### 3. Partial Recovery
- If single chunk fails, regenerate only that chunk
- Don't restart entire pipeline
- Saves time and cost

### 4. Graceful Degradation
- If music generation fails, continue without audio
- Better to deliver video without music than fail completely

## Integration Patterns

### 1. External API Abstraction
- Wrap all external APIs (Replicate, OpenAI, S3) in service classes
- Centralizes error handling and retry logic
- Makes it easy to swap providers

### 2. Progress Tracking (PR #10) ✅ UPDATED
- **Redis-Based Mid-Pipeline Cache**: All progress updates during pipeline execution stored in Redis (60min TTL)
- **Database Writes**: Only at critical points (start, failure, completion) - 90%+ reduction in DB writes
- **Server-Sent Events (SSE)**: Real-time status updates via SSE stream (`/api/status/:video_id/stream`)
- **Automatic Fallback**: Frontend automatically falls back to GET endpoint polling if SSE fails
- **Presigned URL Caching**: S3 presigned URLs cached in Redis (60min TTL) to avoid regeneration
- **Redis-First Lookup**: Status endpoint checks Redis first, falls back to DB if Redis missing
- **Re-Add to Redis**: If DB entry found but Redis missing, automatically re-adds to Redis with 60min TTL
- **Real-time Feedback**: SSE provides instant updates without polling overhead

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

