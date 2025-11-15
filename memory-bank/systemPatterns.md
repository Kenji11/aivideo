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

**Phase 1: Validation & Spec Extraction**
- Input: Natural language prompt
- Process: GPT-4 extracts structured specification
- Output: JSON spec with template, beats, style, audio
- Cost: $0.01 | Time: 2s

**Phase 2: Animatic Generation**
- Input: Spec from Phase 1
- Process: Generate 15 low-fidelity reference frames (SDXL)
- Output: Structural guides for temporal consistency
- Cost: $0.08 | Time: 30s
- Note: User never sees animatic (internal reference only)

**Phase 3: Reference Assets**
- Input: Spec from Phase 1
- Process: Generate style guide + product references (SDXL)
- Output: Canonical visual references
- Cost: $0.02 | Time: 15s

**Phase 4: Chunked Video Generation**
- Input: Spec + Animatic + References
- Process: Generate 15 × 2s video chunks in parallel (Zeroscope/AnimateDiff)
- Output: 15 video chunks
- Cost: $1.50-$3.00 | Time: 5-8 minutes
- Pattern: Parallel execution using Celery groups

**Phase 5: Refinement**
- Input: Stitched video
- Process: Temporal smoothing, upscaling, color grading, audio sync
- Output: Polished final video
- Cost: $0.15 | Time: 2 minutes

**Phase 6: Export**
- Input: Final video
- Process: Upload to S3, generate pre-signed URLs
- Output: Downloadable video

### 2. Template System Pattern

**Template-Driven Generation**
- Templates define beats (timed action sequences)
- Each beat specifies: start time, duration, shot type, action, camera movement
- Prompts are dynamically constructed from template + user spec
- Transitions are deterministic (no AI involvement)

**Template Structure**:
```json
{
  "name": "product_showcase",
  "beats": [...],
  "transitions": [...],
  "audio": {...},
  "color_grading": {...}
}
```

### 3. Temporal Consistency Pattern

**Last-Frame Continuation (PR #8)** ✅ ACTIVE
- **Chunk 0**: Uses Phase 3 reference image as init_image
- **Chunks 1+**: Use last frame from previous chunk as init_image
- Creates temporal coherence and motion continuity
- Result: "One continuous take" feel, eliminates visual resets
- Trade-off: Requires sequential generation (slower but better quality)

**Animatic-as-Reference** (DISABLED FOR MVP)
- Generate cheap, low-detail structural frames
- Use as ControlNet inputs for video generation
- Ensures character/object consistency across clips
- May re-enable post-MVP for multi-image workflows

### 4. Processing Pattern Evolution

**Current: Sequential Generation (PR #8)**
- Chunks generated one at a time (0, 1, 2, 3, ...)
- Required for last-frame continuation
- Each chunk needs previous chunk's last frame
- Slower but ensures temporal coherence
- Generation time: ~45s × chunk_count

**Future: Hybrid Approach (Planned)**
- Generate chunk 0 first (uses Phase 3 reference)
- Extract last frame from chunk 0
- Generate chunks 1+ in parallel (all use chunk 0's last frame)
- Trade-off: Slightly less coherence but much faster
- Alternative: Batch sequential (0-1-2 sequential, then 3-4-5 parallel, etc.)

**Original: Parallel Generation (Deprecated)**
- All chunks generated simultaneously
- Fast but no temporal continuity between chunks
- Caused visual resets and inconsistency
- Replaced by sequential approach

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

