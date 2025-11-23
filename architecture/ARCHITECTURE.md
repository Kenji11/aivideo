# AI Video Generation Pipeline - Architecture Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Pipeline Flow](#pipeline-flow)
4. [Component Architecture](#component-architecture)
5. [Data Flow](#data-flow)
6. [Storage Architecture](#storage-architecture)
7. [API Architecture](#api-architecture)
8. [Deployment Architecture](#deployment-architecture)

---

## System Overview

**AI Video Generation Pipeline** is an end-to-end system that transforms natural language prompts into professional video advertisements through a 5-phase sequential pipeline.

### Key Characteristics
- **Sequential Pipeline**: 5 phases executed in order
- **Dynamic Storyboard Mapping**: Phase 4 adapts to any number of storyboard images from Phase 2
- **Temporal Coherence**: Last-frame continuation ensures smooth transitions
- **Model Flexibility**: Supports multiple video generation models
- **Cost Tracking**: Real-time cost monitoring per phase
- **Progress Tracking**: Real-time progress updates via polling

### Technology Stack
- **Backend**: FastAPI + Celery + PostgreSQL + Redis
- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **AI Services**: OpenAI (GPT-4), Replicate (Video/Image/Music)
- **Storage**: AWS S3
- **Infrastructure**: AWS (us-east-2)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (React Frontend - Vite)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI WEB SERVER                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ /generate│  │ /status  │  │ /video   │  │ /upload  │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼──────────────┼─────────────┼──────────────┘
        │             │              │             │
        │             │              │             │
        ▼             │              │             │
┌─────────────────────┴──────────────┴─────────────┴──────────────┐
│                    REDIS (Job Queue)                              │
│              Celery Task Queue + Results                          │
└─────────────────────┬────────────────────────────────────────────┘
                       │
                       │ Task Execution
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CELERY WORKER TIER                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Pipeline Orchestrator                        │  │
│  │  Phase 1 → Phase 2 → Phase 4 → Phase 5                   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Phase 1:     │  │ Phase 2:     │  │ Phase 4:     │         │
│  │ Validate     │  │ Storyboard   │  │ Chunks       │         │
│  │ (GPT-4)      │  │ (FLUX Dev)   │  │ (Hailuo/Veo) │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐                                              │
│  │ Phase 5:     │                                              │
│  │ Refine       │                                              │
│  │ (MusicGen)   │                                              │
│  └──────────────┘                                              │
└─────────────────────────────────────────────────────────────────┘
        │                    │                    │
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   OpenAI     │    │   Replicate   │    │   AWS S3     │
│   (GPT-4)    │    │   (Video/    │    │   (Storage)  │
│              │    │    Image/    │    │              │
│              │    │    Music)    │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
                             │
                             │
                             ▼
                    ┌─────────────────┐
                    │   PostgreSQL    │
                    │   (Database)    │
                    └─────────────────┘
```

---

## Pipeline Flow

### Complete Request Lifecycle

```
1. User submits prompt via frontend
   ↓
2. POST /api/generate
   - Creates VideoGeneration record (status: QUEUED)
   - Enqueues run_pipeline task to Celery
   - Returns video_id immediately
   ↓
3. Celery Worker picks up task
   ↓
4. Phase 1: Validation & Planning (5-10s)
   - GPT-4 analyzes prompt
   - Extracts product, style, audio preferences
   - Composes beat sequence from beat library
   - Creates complete spec with beats
   ↓
5. Phase 2: Storyboard Generation (8s per image)
   - Generates 1 FLUX Dev image per beat
   - Uploads to S3: {user_id}/videos/{video_id}/storyboard/beat_{i}.png
   - Updates spec: beat['image_url'] = S3 URL
   ↓
6. Phase 3: DISABLED (skipped)
   ↓
7. Phase 4: Video Chunk Generation (45s per chunk, sequential)
   - Calculates chunk count: ceil(duration / actual_chunk_duration)
   - Maps beats to chunks dynamically
   - For each chunk:
     * If chunk starts beat: Use storyboard image from Phase 2
     * If chunk within beat: Use last-frame from previous chunk
   - Generates chunks sequentially (temporal coherence)
   - Stitches chunks with FFmpeg
   - Uploads stitched video to S3
   ↓
8. Phase 5: Refinement & Audio (2 min, or skipped for Veo)
   - Generates background music (MusicGen)
   - Combines video + audio
   - Uploads final video to S3
   ↓
9. Database updated: status=COMPLETE, final_video_url set
   ↓
10. Frontend polls /api/status/{video_id} every 2s
    - Receives presigned URLs for all assets
    - Displays progress, storyboard images, final video
```

---

## Component Architecture

### Backend Structure

```
backend/app/
├── main.py                    # FastAPI application entry point
├── config.py                  # Environment configuration
├── database.py                # SQLAlchemy setup & session management
│
├── api/                       # REST API Endpoints
│   ├── generate.py            # POST /api/generate - Start video generation
│   ├── status.py             # GET /api/status/{video_id} - Get progress
│   ├── video.py              # GET /api/video/{video_id} - Get video details
│   ├── upload.py             # POST /api/upload - Upload reference assets
│   └── health.py             # GET /health - Health check
│
├── orchestrator/              # Pipeline Orchestration
│   ├── celery_app.py         # Celery configuration
│   ├── pipeline.py           # Main pipeline orchestrator (run_pipeline)
│   ├── progress.py           # Progress tracking utilities
│   └── cost_tracker.py       # Cost tracking utilities
│
├── phases/                    # Phase Implementations
│   ├── phase1_validate/      # Prompt validation & spec generation
│   │   ├── task.py           # Celery task wrapper
│   │   ├── service.py        # PromptValidationService
│   │   ├── validation.py    # Spec validation & beat library integration
│   │   └── prompts.py        # GPT-4 prompt templates
│   │
│   ├── phase2_storyboard/    # Storyboard image generation
│   │   ├── task.py           # Celery task wrapper
│   │   └── image_generation.py  # FLUX Dev image generation
│   │
│   ├── phase3_references/    # DISABLED (kept for compatibility)
│   │
│   ├── phase3_chunks/  # Video chunk generation (ACTIVE)
│   │   ├── task.py           # Celery task wrapper
│   │   ├── service.py        # ChunkGenerationService
│   │   ├── chunk_generator.py # Chunk generation logic
│   │   ├── stitcher.py       # Video stitching with FFmpeg
│   │   └── model_config.py   # Model configuration management
│   │
│   ├── phase4_chunks/        # OLD implementation (fallback)
│   │
│   ├── phase4_refine/        # Audio generation & video refinement
│   │   ├── task.py           # Celery task wrapper
│   │   ├── service.py        # RefinementService
│   │   └── music_generator.py # MusicGen integration
│   │
│   └── phase6_export/        # Export & cleanup (future)
│
├── services/                  # External Service Clients
│   ├── openai.py             # OpenAI GPT-4 client
│   ├── replicate.py          # Replicate API client
│   ├── s3.py                 # AWS S3 client
│   └── ffmpeg.py             # FFmpeg utilities
│
└── common/                    # Shared Code
    ├── models.py             # SQLAlchemy models (VideoGeneration, Asset)
    ├── schemas.py            # Pydantic schemas (PhaseOutput, etc.)
    ├── exceptions.py         # Custom exceptions
    ├── constants.py          # Constants & cost definitions
    ├── beat_library.py       # 15-beat library
    └── template_archetypes.py # Template archetype definitions
```

### Frontend Structure

```
frontend/src/
├── main.tsx                   # React entry point
├── App.tsx                    # Main application component
│
├── components/                 # React Components
│   ├── Header.tsx            # Navigation header
│   ├── StepIndicator.tsx     # Progress step indicator
│   ├── UploadZone.tsx        # Asset upload component
│   ├── ProjectCard.tsx       # Video project card
│   ├── ProcessingSteps.tsx   # Phase progress display
│   └── NotificationCenter.tsx # Notification system
│
├── pages/                     # Page Components
│   ├── Dashboard.tsx         # Main dashboard
│   ├── VideoLibrary.tsx      # Video library view
│   └── ...
│
└── lib/                       # Utilities
    ├── api.ts                # API client functions
    └── types.ts              # TypeScript type definitions
```

---

## Data Flow

### 1. Video Generation Request Flow

```
User Input (Frontend)
  ↓
POST /api/generate
  {
    "prompt": "Create a 30-second Nike ad",
    "title": "Nike Ad",
    "model": "hailuo_fast"
  }
  ↓
FastAPI Handler (generate.py)
  - Creates VideoGeneration record
  - Enqueues run_pipeline.delay()
  - Returns {video_id, status: "queued"}
  ↓
Celery Queue (Redis)
  ↓
Worker picks up task
  ↓
Pipeline Orchestrator (pipeline.py)
```

### 2. Phase Execution Flow

```
run_pipeline()
  ↓
Phase 1: validate_prompt.apply()
  - GPT-4 call
  - Beat composition
  - Spec creation
  - Store in DB: video.spec
  ↓
Phase 2: generate_storyboard.apply()
  - For each beat: FLUX Dev image
  - Upload to S3
  - Update spec: beat['image_url']
  - Store in DB: video.phase_outputs['phase2_storyboard']
  ↓
Phase 4: generate_chunks_storyboard.apply()
  - Build chunk specs (dynamic beat-to-chunk mapping)
  - Sequential chunk generation
  - Stitch chunks
  - Store in DB: video.stitched_url, video.chunk_urls
  ↓
Phase 5: refine_video.apply() [if not Veo]
  - Generate music
  - Combine video + audio
  - Store in DB: video.final_video_url
  ↓
Complete: Update DB status=COMPLETE
```

### 3. Progress Tracking Flow

```
Each Phase
  ↓
update_progress(video_id, status, progress, ...)
  ↓
Database Update (PostgreSQL)
  - video.status = status
  - video.progress = progress
  - video.current_phase = phase_name
  ↓
Frontend Polls /api/status/{video_id} every 2s
  ↓
Status API (status.py)
  - Queries database
  - Converts S3 URLs to presigned URLs
  - Returns StatusResponse
  ↓
Frontend Updates UI
  - Progress bar
  - Phase indicators
  - Storyboard images
  - Video preview
```

---

## Storage Architecture

### S3 Bucket Structure

```
s3://{bucket_name}/
└── {user_id}/
    └── videos/
        └── {video_id}/
            ├── storyboard/
            │   ├── beat_00.png
            │   ├── beat_01.png
            │   └── ...
            ├── chunks/
            │   ├── chunk_00.mp4
            │   ├── chunk_00_last_frame.png
            │   ├── chunk_01.mp4
            │   ├── chunk_01_last_frame.png
            │   └── ...
            ├── stitched.mp4          # Phase 4 output
            └── final.mp4             # Phase 5 output (with audio)
```

### Database Schema

```sql
-- Main video generation record
video_generations:
  - id (UUID, PK)
  - user_id (String)
  - title, description, prompt
  - status (Enum: QUEUED, VALIDATING, ..., COMPLETE, FAILED)
  - progress (Float: 0.0-100.0)
  - current_phase (String)
  - spec (JSON)                    # Phase 1 output
  - phase_outputs (JSON)           # All phase outputs
  - stitched_url (String)          # Phase 4 output
  - final_video_url (String)       # Phase 5 output
  - cost_usd (Float)
  - cost_breakdown (JSON)
  - generation_time_seconds (Float)
  - created_at, completed_at (Timestamp)

-- Asset records
assets:
  - id (UUID, PK)
  - user_id (String)
  - s3_key (String)
  - asset_type (Enum: IMAGE, VIDEO, AUDIO)
  - source (Enum: USER_UPLOAD, SYSTEM_GENERATED)
  - created_at (Timestamp)
```

---

## API Architecture

### REST Endpoints

```
POST   /api/generate
  Request: {prompt, title, description, model, reference_assets}
  Response: {video_id, status: "queued"}

GET    /api/status/{video_id}
  Response: {
    status, progress, current_phase,
    animatic_urls, stitched_video_url, final_video_url,
    current_chunk_index, total_chunks,
    error, cost_usd
  }

GET    /api/video/{video_id}
  Response: Full video details

POST   /api/upload
  Request: Multipart form data (files)
  Response: {asset_ids: [...]}

GET    /health
  Response: {status: "healthy"}
```

### Celery Tasks

```
@celery_app.task
run_pipeline(video_id, prompt, assets, model)
  - Main orchestrator
  - Chains phases sequentially
  - Updates progress & cost

@celery_app.task
validate_prompt(video_id, prompt, assets)
  - Phase 1: GPT-4 validation

@celery_app.task
generate_storyboard(video_id, spec, user_id)
  - Phase 2: FLUX Dev image generation

@celery_app.task
generate_chunks(video_id, spec, animatic_urls, reference_urls, user_id)
  - Phase 4: Video chunk generation

@celery_app.task
refine_video(video_id, stitched_url, spec, user_id)
  - Phase 5: Audio generation & refinement
```

---

## Deployment Architecture

### AWS Infrastructure (us-east-2)

```
┌─────────────────────────────────────────────────────────┐
│                    CloudFront CDN                        │
│              (Global - Frontend + Videos)                │
└───────────────────────┬───────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Application Load Balancer                   │
│                    (ALB - us-east-2)                     │
└───────────────┬───────────────────────┬─────────────────┘
                │                       │
                ▼                       ▼
    ┌──────────────────┐      ┌──────────────────┐
    │  Web Tier       │      │  Worker Tier     │
    │  (EB - FastAPI) │      │  (EB - Celery)   │
    │  t3.small       │      │  t3.medium       │
    └──────────────────┘      └──────────────────┘
                │                       │
                └───────────┬───────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │   RDS        │ │  ElastiCache │ │     S3      │
    │  PostgreSQL   │ │    Redis     │ │   Storage   │
    │  db.t4g.micro│ │  t4g.micro   │ │  (Buckets)  │
    └──────────────┘ └──────────────┘ └──────────────┘
```

### Environment Configuration

```bash
# Backend (.env)
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
REPLICATE_API_TOKEN=r8_...
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=ai-video-assets-prod
AWS_REGION=us-east-2
```

---

## Key Design Decisions

### 1. Sequential Chunk Generation
**Decision**: Generate chunks sequentially (not in parallel)  
**Reason**: Required for last-frame continuation to maintain temporal coherence  
**Trade-off**: Slower (~45s per chunk) but better quality

### 2. Dynamic Storyboard Mapping
**Decision**: Phase 4 dynamically adapts to any number of storyboard images  
**Reason**: Phase 2 creates variable number of images (one per beat)  
**Implementation**: Beat-to-chunk mapping calculated from actual beat start times

### 3. Phase 3 Disabled
**Decision**: Skip Phase 3 (reference generation)  
**Reason**: Phase 2 storyboard images provide sufficient visual reference  
**Benefit**: Faster pipeline, lower cost

### 4. Model Configuration System
**Decision**: Centralized model configuration in `model_config.py`  
**Reason**: Easy model switching, accurate chunk duration tracking  
**Benefit**: Single source of truth for model capabilities

### 5. Presigned URLs
**Decision**: Convert S3 URLs to presigned URLs in status API  
**Reason**: Security (time-limited access) and CDN compatibility  
**Expiration**: 1 hour (3600 seconds)

---

## Performance Characteristics

### Generation Time (30-second video)
- **Phase 1**: ~7 seconds
- **Phase 2**: ~32 seconds (4 images × 8s)
- **Phase 4**: ~5.5 minutes (6 chunks × 45s + stitching)
- **Phase 5**: ~2 minutes (or skipped for Veo)
- **Total**: ~8.4 minutes (hailuo_fast) or ~6.4 minutes (Veo)

### Cost per Video (30-second)
- **Phase 1**: $0.02 (GPT-4)
- **Phase 2**: $0.10 (4 images × $0.025)
- **Phase 4**: $0.24 (6 chunks × $0.04 for hailuo_fast)
- **Phase 5**: $0.15 (MusicGen)
- **Total**: ~$0.51 (hailuo_fast) or ~$0.36 (Veo, no Phase 5)

### Scalability
- **Concurrent Users**: 1 per user (MVP)
- **Queue Capacity**: Unlimited (Redis)
- **Worker Scaling**: Horizontal (add more Celery workers)
- **Database**: Connection pooling (10 connections)

---

## Security Considerations

1. **S3 Access**: Pre-signed URLs only (no public buckets)
2. **API Keys**: Stored in environment variables
3. **Input Validation**: Prompt sanitization in Phase 1
4. **Rate Limiting**: 1 video per user concurrently (MVP)
5. **CORS**: Configured for frontend domain

---

## Monitoring & Observability

### Logging
- Structured logging throughout pipeline
- Phase-level cost and duration tracking
- Error logging with full tracebacks

### Metrics Tracked
- Generation time per phase
- Cost per phase
- Success/failure rates
- Chunk generation times

### Health Checks
- `/health` endpoint for load balancer
- Database connection health
- Redis connection health

---

## Future Enhancements

1. **Parallel Chunk Generation**: Hybrid approach (chunk 0 first, then parallel)
2. **Transition Effects**: Beat boundary transitions (dissolve, zoom)
3. **Upscaling**: 1080p output (currently 720p)
4. **User Authentication**: JWT-based auth system
5. **Video Library**: Persistent storage and management
6. **Batch Processing**: Multiple videos in parallel

---

## Version History

- **v2.0**: Beat-based architecture, storyboard generation, dynamic mapping
- **v1.0**: Template-based system (deprecated)

