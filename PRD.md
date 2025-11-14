# Product Requirements Document (PRD)
## AI Video Generation Pipeline - Ad Creative MVP

**Version:** 2.0  
**Date:** November 14, 2025  
**Project Duration:** 7 days (MVP in 48 hours)  
**Target:** $5,000 Bounty Competition  
**Region:** us-east-2 (Ohio)

---

## Executive Summary

Build an end-to-end AI video generation pipeline that transforms text prompts into professional 30-second advertisement videos. The system uses a hybrid approach: deterministic templates for structure + generative AI for content, ensuring reliability, consistency, and cost-effectiveness.

**Key Innovation:** Six-phase pipeline that progressively refines from low-fidelity animatics to high-quality final videos, using animatics as motion references to ensure temporal consistency.

**Team Structure:** 3-person team with phase-based vertical slices to minimize merge conflicts and maximize parallel development.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Team Structure & Ownership](#team-structure--ownership)
3. [Technical Architecture](#technical-architecture)
4. [System Components](#system-components)
5. [Pipeline Phases (Detailed)](#pipeline-phases)
6. [Data Models](#data-models)
7. [API Specifications](#api-specifications)
8. [Template System](#template-system)
9. [Deployment Architecture](#deployment-architecture)
10. [Cost Analysis](#cost-analysis)
11. [Development Roadmap](#development-roadmap)
12. [Testing Strategy](#testing-strategy)

---

## 1. Project Overview

### 1.1 Objectives

**MVP (48 hours):**
- Generate 30-second ad videos from text prompts
- Support 3 ad templates (product showcase, lifestyle, announcement)
- Consistent visual style across all clips
- Audio-visual synchronization with generated background music
- Deploy to AWS with working web interface

**Final Submission (7 days):**
- User authentication and project persistence
- Reference asset library with vector database
- Iterative refinement capabilities
- Timeline editing interface
- Multi-format export

### 1.2 Success Criteria

**Judging Criteria (Competition):**
- Output Quality (40%): Visual coherence, A/V sync, creative execution
- Pipeline Architecture (25%): Code quality, system design, error handling
- Cost Effectiveness (20%): <$2/minute generation cost
- User Experience (15%): Ease of use, feedback quality

**Technical Requirements:**
- 1080p resolution, 30 FPS
- Generation time: <10 minutes for 30s video
- 90%+ successful generation rate
- Support 1 concurrent video per user (MVP)

---

## 2. Team Structure & Ownership

### 2.1 Phase-Based Vertical Slices

**Philosophy:** Each team member owns 2 complete phases (backend + frontend), minimizing merge conflicts and enabling parallel development.

### 2.2 Ownership Chart

| Team Member | Backend Phases | Frontend Features | Responsibilities |
|-------------|---------------|-------------------|------------------|
| **Person A** | Phase 1: Prompt Validation<br>Phase 2: Animatic Generation | Generate Form<br>Template Selector<br>Asset Uploader | - OpenAI integration<br>- Template system<br>- SDXL animatic generation |
| **Person B** | Phase 3: Reference Assets<br>Phase 4: Chunk Generation | Progress Indicator<br>Status Polling | - Style guide generation<br>- Parallel chunk execution<br>- Video stitching |
| **Person C** | Phase 5: Refinement<br>Phase 6: Export | Video Player<br>Export Controls | - FFmpeg processing<br>- Music generation<br>- S3 uploads |

### 2.3 Shared Responsibilities (All)

**Day 1 Kickoff (Write Together):**
- `common/schemas.py` - Phase input/output contracts
- `common/models.py` - Database schema
- `orchestrator/pipeline.py` - Main orchestration logic
- `services/` - External API wrappers (skeleton only)

**Ongoing (Code Review):**
- Review each other's PRs
- Integration testing
- Deployment

---

## 3. Technical Architecture

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    End Users                             │
└────────────────────────────────┬────────────────────────┘
                                 │ HTTPS
                                 ↓
┌─────────────────────────────────────────────────────────┐
│                  CloudFront (CDN)                        │
└──────────────┬──────────────────────────────────────────┘
               │                                      
               ↓                                      
┌──────────────────────────┐           ┌─────────────────────────────────┐
│      S3 Bucket           │           │   Application Load Balancer     │
│  (React Frontend)        │           │         (ALB)                   │
│                          │           │   Port 80/443 → 8000            │
│  - index.html            │           └────────────┬────────────────────┘
│  - bundle.js             │                        │
│  - assets/               │                        │ Round-robin
└──────────────────────────┘                        ↓
                            ┌───────────────────────────────────────────────┐
                            │   Elastic Beanstalk - Web Tier Environment    │
                            │          (Auto Scaling Group)                 │
                            │                                               │
                            │  ┌─────────────────┐  ┌─────────────────┐   │
                            │  │   EC2 Instance  │  │   EC2 Instance  │   │
                            │  │   t3.small      │  │   t3.small      │   │
                            │  │  Docker:        │  │  Docker:        │   │
                            │  │  FastAPI        │  │  FastAPI        │   │
                            │  │  (Port 8000)    │  │  (Port 8000)    │   │
                            │  └─────────────────┘  └─────────────────┘   │
                            └───────────────────┬───────────────────────────┘
                                                │
                                                ↓
                            ┌───────────────────────────────────────────────┐
                            │  ElastiCache Redis (t4g.micro)                │
                            │  - Job Queue                                  │
                            │  - Result Storage                             │
                            └───────────────┬───────────────────────────────┘
                                            │
                                            │ Workers pull jobs
                                            ↓
                            ┌───────────────────────────────────────────────┐
                            │  Elastic Beanstalk - Worker Tier Environment  │
                            │                                               │
                            │  ┌─────────────────┐  ┌─────────────────┐   │
                            │  │   EC2 Instance  │  │   EC2 Instance  │   │
                            │  │   t3.medium     │  │   t3.medium     │   │
                            │  │  Docker:        │  │  Docker:        │   │
                            │  │  Celery Worker  │  │  Celery Worker  │   │
                            │  │  Concurrency: 4 │  │  Concurrency: 4 │   │
                            │  └─────────────────┘  └─────────────────┘   │
                            └───────────────┬───────────────────────────────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
                    ↓                       ↓                       ↓
    ┌───────────────────────┐   ┌──────────────────┐   ┌──────────────────┐
    │  RDS PostgreSQL       │   │   S3 Bucket      │   │  External APIs   │
    │  db.t4g.micro         │   │  Video Storage   │   │  - Replicate     │
    │  - Video metadata     │   │  - /animatic/    │   │  - OpenAI        │
    │  - Cost tracking      │   │  - /references/  │   │                  │
    │  - User data          │   │  - /chunks/      │   │                  │
    └───────────────────────┘   │  - /final.mp4    │   └──────────────────┘
                                └──────────────────┘
```

### 3.2 Technology Stack

**Frontend:**
- React 18 with TypeScript
- Vite (build tool)
- Tailwind CSS + shadcn/ui components
- Radix UI primitives
- Deployment: S3 + CloudFront

**Backend:**
- FastAPI (Python 3.11)
- Celery (async task queue)
- Redis (job broker + result backend)
- PostgreSQL (metadata storage)
- Deployment: Elastic Beanstalk (Docker)

**AI/ML Services:**
- OpenAI GPT-4 Turbo (prompt validation)
- Replicate API:
  - SDXL (animatic + reference assets)
  - Zeroscope (video chunks - dev)
  - AnimateDiff (video chunks - final)
  - MusicGen (background music)

**Infrastructure:**
- AWS Elastic Beanstalk (Web + Worker tiers)
- AWS ElastiCache (Redis)
- AWS RDS (PostgreSQL)
- AWS S3 (storage)
- AWS CloudFront (CDN)
- **Region:** us-east-2 (Ohio)

**Development Tools:**
- Docker + Docker Compose (local dev)
- Poetry (Python dependency management)
- Alembic (database migrations)
- Pytest (testing)

---

## 4. System Components

### 4.1 Backend File Structure (Phase-Based Vertical Slices)

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app + router registration
│   ├── config.py                  # Environment configuration
│   ├── database.py                # PostgreSQL connection pool
│   │
│   ├── common/                    # ⚠️ SHARED - Write together, touch rarely
│   │   ├── __init__.py
│   │   ├── models.py              # SQLAlchemy models (VideoGeneration)
│   │   ├── schemas.py             # Shared Pydantic models (PhaseInput/Output)
│   │   ├── exceptions.py          # Custom exceptions
│   │   ├── logging.py             # Logging configuration
│   │   └── constants.py           # Shared constants
│   │
│   ├── services/                  # ⚠️ SHARED - External API wrappers
│   │   ├── __init__.py
│   │   ├── replicate.py           # Replicate API client
│   │   ├── openai.py              # OpenAI API client
│   │   ├── s3.py                  # S3 upload/download
│   │   └── ffmpeg.py              # FFmpeg wrapper
│   │
│   ├── api/                       # ⚠️ SHARED - HTTP endpoints (minimal)
│   │   ├── __init__.py
│   │   ├── generate.py            # POST /api/generate
│   │   ├── status.py              # GET /api/status/:id
│   │   ├── video.py               # GET /api/video/:id
│   │   └── health.py              # GET /health
│   │
│   ├── orchestrator/              # ⚠️ SHARED - Write together on Day 1
│   │   ├── __init__.py
│   │   ├── celery_app.py          # Celery configuration
│   │   ├── pipeline.py            # Main orchestration task
│   │   ├── progress.py            # Update DB progress/status
│   │   └── cost_tracker.py        # Track costs per phase
│   │
│   ├── phases/                    # ⭐ MAIN WORK AREA - Each person owns 2 folders
│   │   ├── __init__.py
│   │   │
│   │   ├── phase1_validate/       # 👤 PERSON A
│   │   │   ├── __init__.py
│   │   │   ├── task.py            # @celery_app.task validate_prompt()
│   │   │   ├── service.py         # Business logic (OpenAI, templates)
│   │   │   ├── schemas.py         # Phase-specific Pydantic models
│   │   │   └── templates/         # JSON template configs
│   │   │       ├── product_showcase.json
│   │   │       ├── lifestyle_ad.json
│   │   │       └── announcement.json
│   │   │
│   │   ├── phase2_animatic/       # 👤 PERSON A
│   │   │   ├── __init__.py
│   │   │   ├── task.py            # @celery_app.task generate_animatic()
│   │   │   ├── service.py         # SDXL calls, S3 uploads
│   │   │   ├── schemas.py
│   │   │   └── prompts.py         # Animatic prompt generation
│   │   │
│   │   ├── phase3_references/     # 👤 PERSON B
│   │   │   ├── __init__.py
│   │   │   ├── task.py            # @celery_app.task generate_references()
│   │   │   ├── service.py         # Style guide generation
│   │   │   ├── schemas.py
│   │   │   └── asset_handler.py   # Handle uploaded assets
│   │   │
│   │   ├── phase4_chunks/         # 👤 PERSON B
│   │   │   ├── __init__.py
│   │   │   ├── task.py            # @celery_app.task generate_chunks()
│   │   │   ├── service.py         # Parallel chunk execution
│   │   │   ├── schemas.py
│   │   │   ├── chunk_generator.py # Single chunk generation
│   │   │   └── stitcher.py        # FFmpeg stitching + transitions
│   │   │
│   │   ├── phase5_refine/         # 👤 PERSON C
│   │   │   ├── __init__.py
│   │   │   ├── task.py            # @celery_app.task refine_video()
│   │   │   ├── service.py         # Orchestrate refinement steps
│   │   │   ├── schemas.py
│   │   │   ├── upscaler.py        # Video upscaling
│   │   │   ├── color_grader.py    # Apply LUTs
│   │   │   ├── music_generator.py # MusicGen integration
│   │   │   └── luts/              # Color grading LUT files
│   │   │       ├── cinematic_warm.cube
│   │   │       ├── modern_vibrant.cube
│   │   │       └── elegant_muted.cube
│   │   │
│   │   └── phase6_export/         # 👤 PERSON C
│   │       ├── __init__.py
│   │       ├── task.py            # @celery_app.task export_video()
│   │       ├── service.py         # S3 upload, cleanup
│   │       ├── schemas.py
│   │       └── cleanup.py         # Delete intermediate files
│   │
│   └── tests/                     # Each person tests their phases
│       ├── conftest.py            # Shared fixtures
│       ├── test_phase1/
│       ├── test_phase2/
│       ├── test_phase3/
│       ├── test_phase4/
│       ├── test_phase5/
│       └── test_phase6/
│
├── alembic/                       # Database migrations
│   ├── versions/
│   └── env.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

### 4.2 Frontend File Structure (Feature-Based)

```
frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   │
│   ├── features/                  # ⭐ MAIN WORK AREA - Each person owns 1 folder
│   │   │
│   │   ├── generate/              # 👤 PERSON A
│   │   │   ├── GeneratePage.tsx   # Main page component
│   │   │   ├── GenerateForm.tsx   # Prompt input form
│   │   │   ├── TemplateSelector.tsx # Template picker
│   │   │   ├── AssetUploader.tsx  # Upload logos/images
│   │   │   ├── useGenerate.ts     # Hook for API call
│   │   │   └── types.ts           # Feature-specific types
│   │   │
│   │   ├── progress/              # 👤 PERSON B
│   │   │   ├── ProgressPage.tsx   # Status page
│   │   │   ├── ProgressIndicator.tsx # Progress bar
│   │   │   ├── PhaseStatus.tsx    # Current phase display
│   │   │   ├── usePolling.ts      # Poll /api/status
│   │   │   └── types.ts
│   │   │
│   │   └── video/                 # 👤 PERSON C
│   │       ├── VideoPage.tsx      # Final video page
│   │       ├── VideoPlayer.tsx    # HTML5 player + controls
│   │       ├── ExportButton.tsx   # Download handler
│   │       ├── useVideoPlayer.ts  # Player controls hook
│   │       └── types.ts
│   │
│   ├── shared/                    # ⚠️ SHARED - Touch rarely
│   │   ├── components/
│   │   │   └── ui/                # shadcn components
│   │   │       ├── button.tsx
│   │   │       ├── input.tsx
│   │   │       ├── card.tsx
│   │   │       └── ...
│   │   │
│   │   ├── lib/
│   │   │   ├── api.ts             # API client
│   │   │   ├── utils.ts           # Helper functions
│   │   │   └── constants.ts
│   │   │
│   │   └── types/
│   │       └── index.ts           # Shared TypeScript types
│   │
│   └── styles/
│       └── globals.css
│
├── public/
├── index.html
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 5. Pipeline Phases (Detailed)

### 5.1 Shared Contracts (Define Together on Day 1)

```python
# common/schemas.py

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime

class PhaseInput(BaseModel):
    """Standard input for every phase task"""
    video_id: str
    spec: Dict  # Full specification from Phase 1
    
class PhaseOutput(BaseModel):
    """Standard output from every phase task"""
    video_id: str
    phase: str  # "phase1_validate", "phase2_animatic", etc.
    status: str  # "success" or "failed"
    output_data: Dict  # Phase-specific results
    cost_usd: float
    duration_seconds: float
    error_message: Optional[str] = None

# Example phase-specific output structures
class Phase1Output(BaseModel):
    spec: Dict  # Validated and enriched spec
    template: str
    
class Phase2Output(BaseModel):
    animatic_urls: List[str]  # S3 URLs for 15 frames
    
class Phase3Output(BaseModel):
    style_guide_url: str
    product_ref_url: Optional[str]
    logo_url: Optional[str]
    
class Phase4Output(BaseModel):
    stitched_video_url: str
    chunk_urls: List[str]  # For debugging
    
class Phase5Output(BaseModel):
    refined_video_url: str
    music_url: str
    
class Phase6Output(BaseModel):
    final_video_url: str
    presigned_download_url: str
```

### 5.2 Database Model (Define Together on Day 1)

```python
# common/models.py

from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class VideoStatus(str, enum.Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    GENERATING_ANIMATIC = "generating_animatic"
    GENERATING_REFERENCES = "generating_references"
    GENERATING_CHUNKS = "generating_chunks"
    REFINING = "refining"
    EXPORTING = "exporting"
    COMPLETE = "complete"
    FAILED = "failed"

class VideoGeneration(Base):
    __tablename__ = "video_generations"
    
    # Primary
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, nullable=True)  # For final submission
    
    # Input
    prompt = Column(String, nullable=False)
    uploaded_assets = Column(JSON, default=[])
    
    # Spec (from Phase 1)
    spec = Column(JSON, nullable=True)
    template = Column(String, nullable=True)
    
    # Status
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.QUEUED)
    progress = Column(Float, default=0.0)  # 0-100
    current_phase = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Phase Outputs (URLs to S3 resources)
    animatic_urls = Column(JSON, default=[])
    reference_urls = Column(JSON, default={})
    chunk_urls = Column(JSON, default=[])
    stitched_url = Column(String, nullable=True)
    refined_url = Column(String, nullable=True)
    final_video_url = Column(String, nullable=True)
    
    # Metadata
    cost_usd = Column(Float, default=0.0)
    cost_breakdown = Column(JSON, default={})  # Per-phase costs
    generation_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
```

### 5.3 Orchestrator (Write Together on Day 1)

```python
# orchestrator/pipeline.py

from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic
from app.phases.phase3_references.task import generate_references
from app.phases.phase4_chunks.task import generate_chunks
from app.phases.phase5_refine.task import refine_video
from app.phases.phase6_export.task import export_video
from app.orchestrator.progress import update_progress, update_cost
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseInput
import time

@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: List[dict]):
    """
    Main orchestration task - chains all 6 phases sequentially.
    Each person implements their phase tasks independently.
    """
    start_time = time.time()
    total_cost = 0.0
    
    try:
        # Phase 1: Validate Prompt (Person A)
        update_progress(video_id, "validating", 10)
        result1 = validate_prompt.delay(video_id, prompt, assets).get(timeout=60)
        if result1.status != "success":
            raise Exception(f"Phase 1 failed: {result1.error_message}")
        total_cost += result1.cost_usd
        update_cost(video_id, "phase1", result1.cost_usd)
        
        # Phase 2: Generate Animatic (Person A)
        update_progress(video_id, "generating_animatic", 25)
        result2 = generate_animatic.delay(video_id, result1.output_data['spec']).get(timeout=300)
        if result2.status != "success":
            raise Exception(f"Phase 2 failed: {result2.error_message}")
        total_cost += result2.cost_usd
        update_cost(video_id, "phase2", result2.cost_usd)
        
        # Phase 3: Generate References (Person B)
        update_progress(video_id, "generating_references", 35)
        result3 = generate_references.delay(video_id, result1.output_data['spec']).get(timeout=300)
        if result3.status != "success":
            raise Exception(f"Phase 3 failed: {result3.error_message}")
        total_cost += result3.cost_usd
        update_cost(video_id, "phase3", result3.cost_usd)
        
        # Phase 4: Generate Chunks (Person B)
        update_progress(video_id, "generating_chunks", 50)
        phase4_input = {
            "video_id": video_id,
            "spec": result1.output_data['spec'],
            "animatic_urls": result2.output_data['animatic_urls'],
            "reference_urls": result3.output_data
        }
        result4 = generate_chunks.delay(**phase4_input).get(timeout=600)
        if result4.status != "success":
            raise Exception(f"Phase 4 failed: {result4.error_message}")
        total_cost += result4.cost_usd
        update_cost(video_id, "phase4", result4.cost_usd)
        
        # Phase 5: Refine Video (Person C)
        update_progress(video_id, "refining", 80)
        phase5_input = {
            "video_id": video_id,
            "stitched_url": result4.output_data['stitched_video_url'],
            "spec": result1.output_data['spec']
        }
        result5 = refine_video.delay(**phase5_input).get(timeout=300)
        if result5.status != "success":
            raise Exception(f"Phase 5 failed: {result5.error_message}")
        total_cost += result5.cost_usd
        update_cost(video_id, "phase5", result5.cost_usd)
        
        # Phase 6: Export (Person C)
        update_progress(video_id, "exporting", 95)
        result6 = export_video.delay(video_id, result5.output_data['refined_video_url']).get(timeout=180)
        if result6.status != "success":
            raise Exception(f"Phase 6 failed: {result6.error_message}")
        total_cost += result6.cost_usd
        update_cost(video_id, "phase6", result6.cost_usd)
        
        # Success!
        generation_time = time.time() - start_time
        update_progress(
            video_id, 
            "complete", 
            100,
            final_url=result6.output_data['final_video_url'],
            total_cost=total_cost,
            generation_time=generation_time
        )
        
        return {
            "video_id": video_id,
            "status": "complete",
            "final_video_url": result6.output_data['final_video_url'],
            "cost_usd": total_cost,
            "generation_time_seconds": generation_time
        }
        
    except Exception as e:
        update_progress(video_id, "failed", None, error=str(e))
        raise
```

---

### Phase 1: Prompt Validation (Person A)

**Location:** `phases/phase1_validate/`

**Objective:** Convert natural language prompt into structured specification.

**Input:**
```python
video_id: str
prompt: str
assets: List[dict]  # [{"type": "logo", "url": "s3://..."}, ...]
```

**Output:**
```python
PhaseOutput(
    video_id="uuid",
    phase="phase1_validate",
    status="success",
    output_data={
        "spec": {
            "template": "product_showcase",
            "duration": 30,
            "resolution": "1080p",
            "fps": 30,
            "style": {
                "aesthetic": "luxury",
                "color_palette": ["gold", "black", "white"],
                "mood": "elegant",
                "lighting": "dramatic"
            },
            "beats": [...],
            "transitions": ["fade", "cut", "fade"],
            "audio": {...}
        }
    },
    cost_usd=0.01,
    duration_seconds=2.5
)
```

**Implementation:**

```python
# phases/phase1_validate/task.py

from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase1_validate.service import PromptValidationService
import time

@celery_app.task
def validate_prompt(video_id: str, prompt: str, assets: List[dict]) -> PhaseOutput:
    """
    Phase 1: Validate prompt and extract structured specification.
    
    Person A is responsible for:
    - OpenAI GPT-4 integration
    - Template loading and validation
    - Spec enrichment
    """
    start_time = time.time()
    
    try:
        service = PromptValidationService()
        spec = service.validate_and_extract(prompt, assets)
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase1_validate",
            status="success",
            output_data={"spec": spec},
            cost_usd=0.01,  # GPT-4 call
            duration_seconds=time.time() - start_time
        )
    except Exception as e:
        return PhaseOutput(
            video_id=video_id,
            phase="phase1_validate",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
```

```python
# phases/phase1_validate/service.py

from app.services.openai import openai_client
from app.phases.phase1_validate.templates import load_template
import json

class PromptValidationService:
    def validate_and_extract(self, prompt: str, assets: List[dict]) -> dict:
        """Extract structured spec from natural language prompt"""
        
        system_prompt = """
        You are a video production assistant. Extract structured specifications from user prompts.
        
        Available templates:
        - product_showcase: Focus on product features and details
        - lifestyle_ad: Show product in real-world context  
        - announcement: Brand message or campaign announcement
        
        Return JSON with:
        {
            "template": "product_showcase",
            "style": {
                "aesthetic": "luxury",
                "color_palette": ["gold", "black"],
                "mood": "elegant",
                "lighting": "dramatic"
            },
            "product": {
                "name": "luxury watch",
                "category": "accessories"
            },
            "audio": {
                "music_style": "orchestral",
                "tempo": "moderate",
                "mood": "sophisticated"
            }
        }
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        extracted_spec = json.loads(response.choices[0].message.content)
        
        # Load template and merge
        template = load_template(extracted_spec['template'])
        full_spec = template.merge_with_user_input(extracted_spec)
        
        # Add uploaded assets
        full_spec['uploaded_assets'] = assets
        
        return full_spec
```

**Template Example:**

```json
// phases/phase1_validate/templates/product_showcase.json
{
  "name": "product_showcase",
  "description": "Highlights product features and details",
  "default_duration": 30,
  "fps": 30,
  "resolution": "1080p",
  
  "beats": [
    {
      "name": "hero_shot",
      "start": 0,
      "duration": 3,
      "shot_type": "close_up",
      "action": "product_reveal",
      "prompt_template": "{product} on {background}, {style} aesthetic, dramatic reveal",
      "camera_movement": "slow_zoom_in"
    },
    {
      "name": "detail_showcase",
      "start": 3,
      "duration": 5,
      "shot_type": "macro",
      "action": "feature_highlight",
      "prompt_template": "extreme close-up of {product} details, {style} lighting",
      "camera_movement": "pan_across"
    },
    {
      "name": "lifestyle_context",
      "start": 8,
      "duration": 7,
      "shot_type": "medium",
      "action": "usage_scenario",
      "prompt_template": "person using {product} in {setting}, {style} aesthetic",
      "camera_movement": "static"
    },
    {
      "name": "brand_moment",
      "start": 15,
      "duration": 10,
      "shot_type": "wide",
      "action": "brand_story",
      "prompt_template": "{product} in elegant setting, {style} aesthetic, cinematic",
      "camera_movement": "slow_dolly"
    },
    {
      "name": "call_to_action",
      "start": 25,
      "duration": 5,
      "shot_type": "close_up",
      "action": "final_impression",
      "prompt_template": "{product} with brand logo, {style} aesthetic",
      "camera_movement": "static"
    }
  ],
  
  "transitions": [
    {"type": "fade", "duration": 0.5},
    {"type": "cut"},
    {"type": "fade", "duration": 0.5},
    {"type": "cut"}
  ],
  
  "audio": {
    "music_style": "elegant orchestral",
    "tempo": "moderate",
    "mood": "sophisticated"
  },
  
  "color_grading": {
    "lut": "cinematic_warm.cube",
    "contrast": 1.1,
    "saturation": 1.05
  }
}
```

---

### Phase 2: Animatic Generation (Person A)

**Location:** `phases/phase2_animatic/`

**Objective:** Generate low-fidelity structural reference frames.

**Input:**
```python
video_id: str
spec: dict  # From Phase 1
```

**Output:**
```python
PhaseOutput(
    video_id="uuid",
    phase="phase2_animatic",
    status="success",
    output_data={
        "animatic_urls": [
            "s3://bucket/videos/uuid/animatic/frame_00.png",
            "s3://bucket/videos/uuid/animatic/frame_01.png",
            # ... 15 frames total
        ]
    },
    cost_usd=0.08,  # 15 frames × $0.0055
    duration_seconds=35.0
)
```

**Implementation:**

```python
# phases/phase2_animatic/task.py

from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase2_animatic.service import AnimaticGenerationService
import time

@celery_app.task
def generate_animatic(video_id: str, spec: dict) -> PhaseOutput:
    """
    Phase 2: Generate low-fidelity animatic frames.
    
    Person A is responsible for:
    - SDXL image generation
    - Animatic prompt engineering
    - S3 uploads
    """
    start_time = time.time()
    
    try:
        service = AnimaticGenerationService()
        animatic_urls = service.generate_frames(video_id, spec)
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="success",
            output_data={"animatic_urls": animatic_urls},
            cost_usd=len(animatic_urls) * 0.0055,
            duration_seconds=time.time() - start_time
        )
    except Exception as e:
        return PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
```

```python
# phases/phase2_animatic/service.py

from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.phases.phase2_animatic.prompts import generate_animatic_prompt

class AnimaticGenerationService:
    def generate_frames(self, video_id: str, spec: dict) -> List[str]:
        """Generate low-res keyframes (1 per 2 seconds)"""
        
        animatic_urls = []
        beats = spec['beats']
        
        # Generate 1 frame per beat (approx every 2 seconds)
        for i, beat in enumerate(beats):
            # Create simple, low-detail prompt
            prompt = generate_animatic_prompt(beat, spec['style'])
            
            # Generate with SDXL (low quality, fast)
            result = replicate_client.run(
                "stability-ai/sdxl:latest",
                input={
                    "prompt": prompt,
                    "negative_prompt": "detailed, photorealistic, complex, colorful, high quality",
                    "width": 512,  # Low res for speed
                    "height": 512,
                    "num_inference_steps": 20,  # Fast
                    "guidance_scale": 7.0
                }
            )
            
            # Upload to S3
            frame_url = s3_client.upload_image(
                result[0],
                bucket="ai-video-assets-prod",
                key=f"videos/{video_id}/animatic/frame_{i:02d}.png"
            )
            
            animatic_urls.append(frame_url)
        
        return animatic_urls
```

```python
# phases/phase2_animatic/prompts.py

def generate_animatic_prompt(beat: dict, style: dict) -> str:
    """
    Create simple, structural prompts for animatic generation.
    Focus on composition and motion, not detail.
    """
    base = f"simple line drawing, minimal detail, sketch style, {beat['shot_type']} shot"
    action = beat['prompt_template'].format(
        product=style.get('product', 'product'),
        background='plain background',
        style='minimalist',
        setting='simple setting'
    )
    
    return f"{action}, {base}"
```

---

### Phase 3: Reference Assets (Person B)

**Location:** `phases/phase3_references/`

**Objective:** Generate canonical visual references for consistency.

**Implementation:**

```python
# phases/phase3_references/task.py

from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase3_references.service import ReferenceAssetService
import time

@celery_app.task
def generate_references(video_id: str, spec: dict) -> PhaseOutput:
    """
    Phase 3: Generate reference assets (style guide, product refs).
    
    Person B is responsible for:
    - Style guide generation
    - Handling uploaded assets
    - Consistency strategy
    """
    start_time = time.time()
    
    try:
        service = ReferenceAssetService()
        references = service.generate_all_references(video_id, spec)
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_references",
            status="success",
            output_data=references,
            cost_usd=service.total_cost,
            duration_seconds=time.time() - start_time
        )
    except Exception as e:
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_references",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
```

---

### Phase 4: Chunk Generation (Person B)

**Location:** `phases/phase4_chunks/`

**Objective:** Generate video chunks with parallel execution and stitching.

**Implementation:**

```python
# phases/phase4_chunks/task.py

from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase4_chunks.service import ChunkGenerationService
from app.phases.phase4_chunks.stitcher import VideoStitcher
import time

@celery_app.task
def generate_chunks(video_id: str, spec: dict, animatic_urls: List[str], reference_urls: dict) -> PhaseOutput:
    """
    Phase 4: Generate and stitch video chunks.
    
    Person B is responsible for:
    - Parallel chunk generation (Celery group)
    - Zeroscope/AnimateDiff integration
    - FFmpeg stitching with transitions
    """
    start_time = time.time()
    
    try:
        # Generate chunks in parallel
        service = ChunkGenerationService()
        chunk_urls = service.generate_all_chunks(
            video_id, 
            spec, 
            animatic_urls, 
            reference_urls
        )
        
        # Stitch chunks together
        stitcher = VideoStitcher()
        stitched_url = stitcher.stitch_with_transitions(
            video_id,
            chunk_urls,
            spec['transitions']
        )
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks",
            status="success",
            output_data={
                "stitched_video_url": stitched_url,
                "chunk_urls": chunk_urls
            },
            cost_usd=service.total_cost,
            duration_seconds=time.time() - start_time
        )
    except Exception as e:
        return PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
```

```python
# phases/phase4_chunks/service.py

from celery import group
from app.phases.phase4_chunks.chunk_generator import generate_single_chunk

class ChunkGenerationService:
    def generate_all_chunks(
        self, 
        video_id: str, 
        spec: dict, 
        animatic_urls: List[str], 
        reference_urls: dict
    ) -> List[str]:
        """Generate all chunks in parallel using Celery group"""
        
        # Create chunk specifications
        chunk_specs = []
        for i, beat in enumerate(spec['beats']):
            chunk_spec = {
                "video_id": video_id,
                "chunk_num": i,
                "beat": beat,
                "animatic_url": animatic_urls[i],
                "style_guide_url": reference_urls['style_guide_url'],
                "style": spec['style']
            }
            chunk_specs.append(chunk_spec)
        
        # Execute in parallel
        chunk_tasks = group([
            generate_single_chunk.s(chunk_spec)
            for chunk_spec in chunk_specs
        ])
        
        result = chunk_tasks.apply_async()
        chunk_urls = result.get(timeout=600)  # 10 min max
        
        self.total_cost = len(chunk_urls) * 0.10  # Zeroscope cost
        
        return chunk_urls

@celery_app.task
def generate_single_chunk(chunk_spec: dict) -> str:
    """Generate a single 2-second video chunk"""
    from app.services.replicate import replicate_client
    from app.services.s3 import s3_client
    
    # Download animatic frame
    animatic_img = s3_client.download_temp(chunk_spec['animatic_url'])
    
    # Generate video chunk
    result = replicate_client.run(
        "anotherjesse/zeroscope-v2-xl:latest",
        input={
            "image": animatic_img,  # Use animatic as structure
            "prompt": chunk_spec['beat']['prompt_template'],
            "num_frames": 48,  # 2s at 24fps
            "fps": 24,
            "width": 1024,
            "height": 576
        }
    )
    
    # Upload chunk
    chunk_url = s3_client.upload_video(
        result,
        bucket="ai-video-assets-prod",
        key=f"videos/{chunk_spec['video_id']}/chunks/chunk_{chunk_spec['chunk_num']:02d}.mp4"
    )
    
    return chunk_url
```

---

### Phase 5: Refinement (Person C)

**Location:** `phases/phase5_refine/`

**Objective:** Polish stitched video (upscale, color grade, add music).

**Implementation:**

```python
# phases/phase5_refine/task.py

from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase5_refine.service import RefinementService
import time

@celery_app.task
def refine_video(video_id: str, stitched_url: str, spec: dict) -> PhaseOutput:
    """
    Phase 5: Refine and polish video.
    
    Person C is responsible for:
    - FFmpeg processing (upscale, color grade)
    - MusicGen integration
    - Audio mixing
    """
    start_time = time.time()
    
    try:
        service = RefinementService()
        refined_url, music_url = service.refine_all(video_id, stitched_url, spec)
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase5_refine",
            status="success",
            output_data={
                "refined_video_url": refined_url,
                "music_url": music_url
            },
            cost_usd=service.total_cost,
            duration_seconds=time.time() - start_time
        )
    except Exception as e:
        return PhaseOutput(
            video_id=video_id,
            phase="phase5_refine",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
```

---

### Phase 6: Export (Person C)

**Location:** `phases/phase6_export/`

**Objective:** Upload final video, cleanup intermediates, generate download URL.

**Implementation:**

```python
# phases/phase6_export/task.py

from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase6_export.service import ExportService
import time

@celery_app.task
def export_video(video_id: str, refined_url: str) -> PhaseOutput:
    """
    Phase 6: Export final video and cleanup.
    
    Person C is responsible for:
    - S3 final upload
    - Cleanup intermediate files
    - Generate presigned download URL
    """
    start_time = time.time()
    
    try:
        service = ExportService()
        final_url, download_url = service.export_and_cleanup(video_id, refined_url)
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase6_export",
            status="success",
            output_data={
                "final_video_url": final_url,
                "presigned_download_url": download_url
            },
            cost_usd=0.0,  # No API costs
            duration_seconds=time.time() - start_time
        )
    except Exception as e:
        return PhaseOutput(
            video_id=video_id,
            phase="phase6_export",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
```

---

## 6. Data Models

*(Same as previous, no changes needed)*

---

## 7. API Specifications

### 7.1 Endpoints

#### POST /api/generate
**Location:** `api/generate.py`

```python
from fastapi import APIRouter, HTTPException
from app.common.schemas import GenerateRequest, GenerateResponse
from app.orchestrator.pipeline import run_pipeline
from app.database import get_db
import uuid

router = APIRouter()

@router.post("/api/generate")
async def generate_video(request: GenerateRequest) -> GenerateResponse:
    """Submit video generation job"""
    
    # Create video record
    video_id = str(uuid.uuid4())
    
    # TODO: Save to DB with status='queued'
    
    # Enqueue job
    run_pipeline.delay(video_id, request.prompt, request.assets)
    
    return GenerateResponse(
        video_id=video_id,
        status="queued",
        message="Video generation started"
    )
```

#### GET /api/status/:video_id
**Location:** `api/status.py`

```python
from fastapi import APIRouter, HTTPException
from app.common.schemas import StatusResponse
from app.database import get_db
from app.common.models import VideoGeneration

router = APIRouter()

@router.get("/api/status/{video_id}")
async def get_status(video_id: str) -> StatusResponse:
    """Poll generation status"""
    
    db = get_db()
    video = db.query(VideoGeneration).filter_by(id=video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return StatusResponse(
        video_id=video.id,
        status=video.status.value,
        progress=video.progress,
        current_phase=video.current_phase,
        estimated_time_remaining=estimate_time(video),  # TODO
        error=video.error_message
    )
```

#### GET /api/video/:video_id
**Location:** `api/video.py`

```python
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from app.common.schemas import VideoResponse
from app.database import get_db
from app.common.models import VideoGeneration
from app.services.s3 import s3_client

router = APIRouter()

@router.get("/api/video/{video_id}")
async def get_video(video_id: str) -> VideoResponse:
    """Get final video metadata"""
    
    db = get_db()
    video = db.query(VideoGeneration).filter_by(id=video_id).first()
    
    if not video:
        raise HTTPException(status_code=404)
    
    if video.status != "complete":
        raise HTTPException(status_code=400, detail="Video not ready")
    
    return VideoResponse(
        video_id=video.id,
        status=video.status.value,
        final_video_url=video.final_video_url,
        cost_usd=video.cost_usd,
        generation_time_seconds=video.generation_time_seconds,
        created_at=video.created_at,
        completed_at=video.completed_at,
        spec=video.spec
    )

@router.get("/api/video/{video_id}/download")
async def download_video(video_id: str):
    """Generate presigned S3 URL for download"""
    
    db = get_db()
    video = db.query(VideoGeneration).filter_by(id=video_id).first()
    
    if not video or video.status != "complete":
        raise HTTPException(status_code=404)
    
    # Generate presigned URL (valid for 1 hour)
    download_url = s3_client.generate_presigned_url(
        video.final_video_url,
        expiration=3600
    )
    
    return RedirectResponse(download_url)
```

---

## 8. Template System

*(Same as previous - 3 JSON templates: product_showcase, lifestyle_ad, announcement)*

---

## 9. Deployment Architecture

### 9.1 Local Development (Docker Compose)

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: videogen
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://dev:devpass@postgres:5432/videogen
      REDIS_URL: redis://redis:6379/0
      REPLICATE_API_TOKEN: ${REPLICATE_API_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      S3_BUCKET: ${S3_BUCKET}
      AWS_REGION: us-east-2
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://dev:devpass@postgres:5432/videogen
      REDIS_URL: redis://redis:6379/0
      REPLICATE_API_TOKEN: ${REPLICATE_API_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      S3_BUCKET: ${S3_BUCKET}
      AWS_REGION: us-east-2
    volumes:
      - ./backend:/app
    command: celery -A app.orchestrator.celery_app worker --loglevel=info --concurrency=4

volumes:
  postgres_data:
```

**Start local development:**
```bash
docker-compose up
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 9.2 AWS Deployment Steps (us-east-2)

#### Step 1: Create S3 Bucket
```bash
aws s3 mb s3://ai-video-assets-prod --region us-east-2
aws s3api put-bucket-cors --bucket ai-video-assets-prod --cors-configuration file://cors.json --region us-east-2
```

#### Step 2: Create RDS PostgreSQL
```bash
aws rds create-db-instance \
  --db-instance-identifier videogen-db \
  --db-instance-class db.t4g.micro \
  --engine postgres \
  --engine-version 15.3 \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 20 \
  --region us-east-2
```

#### Step 3: Create ElastiCache Redis
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id videogen-redis \
  --cache-node-type cache.t4g.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --region us-east-2
```

#### Step 4: Initialize Elastic Beanstalk
```bash
cd backend
eb init -p docker videogen-api --region us-east-2
```

#### Step 5: Create Web Tier Environment
```bash
eb create videogen-web \
  --instance-type t3.small \
  --region us-east-2 \
  --envvars \
    DATABASE_URL=<rds_url> \
    REDIS_URL=<elasticache_url> \
    REPLICATE_API_TOKEN=<token> \
    OPENAI_API_KEY=<key> \
    S3_BUCKET=ai-video-assets-prod \
    AWS_REGION=us-east-2
```

#### Step 6: Create Worker Tier Environment
```bash
eb create videogen-worker \
  --tier worker \
  --instance-type t3.medium \
  --region us-east-2 \
  --envvars \
    DATABASE_URL=<rds_url> \
    REDIS_URL=<elasticache_url> \
    REPLICATE_API_TOKEN=<token> \
    OPENAI_API_KEY=<key> \
    S3_BUCKET=ai-video-assets-prod \
    AWS_REGION=us-east-2
```

#### Step 7: Deploy Frontend to S3 + CloudFront
```bash
cd frontend
npm run build
aws s3 sync dist/ s3://videogen-frontend-prod --region us-east-2
aws cloudfront create-invalidation --distribution-id <id> --paths "/*"
```

---

## 10. Cost Analysis

### 10.1 Infrastructure Costs (Monthly)

| Service | Instance | Region | Monthly Cost |
|---------|----------|--------|--------------|
| ElastiCache Redis | t4g.micro | us-east-2 | $11.52 |
| RDS Postgres | db.t4g.micro | us-east-2 | $13.82 |
| EB Web Tier | t3.small | us-east-2 | $14.98 |
| ALB | - | us-east-2 | $16.20 |
| EB Worker Tier | t3.medium | us-east-2 | $29.95 |
| S3 Storage | - | us-east-2 | $0.50 |
| CloudFront | - | Global | $0.30 |
| Data Transfer | - | us-east-2 | $0.45 |
| **Total** | | | **$87.72/month** |

### 10.2 Per-Video Generation Costs

| Phase | Model | Cost |
|-------|-------|------|
| Phase 1: Validation | GPT-4 Turbo | $0.01 |
| Phase 2: Animatic | SDXL × 15 | $0.08 |
| Phase 3: References | SDXL × 3 | $0.02 |
| Phase 4: Chunks (dev) | Zeroscope × 15 | $1.50 |
| Phase 4: Chunks (final) | AnimateDiff × 15 | $3.00 |
| Phase 5: Music | MusicGen | $0.15 |
| **Total (dev)** | | **$1.76** |
| **Total (final)** | | **$3.26** |

### 10.3 Budget for Competition Week

- Infrastructure (1 week): ~$25
- 90 test videos (Zeroscope): $158
- 10 showcase videos (AnimateDiff): $33
- **Total: ~$216**

---

## 11. Development Roadmap

### Day 1: Kickoff & Foundation (All Together, Then Split)

**Morning (Together - 2 hours):**
- ✅ Review PRD and architecture
- ✅ Write `common/schemas.py` (PhaseInput/Output contracts)
- ✅ Write `common/models.py` (VideoGeneration database model)
- ✅ Write `orchestrator/pipeline.py` skeleton
- ✅ Set up shared `services/` (API client interfaces)
- ✅ Agree on Git workflow (feature branches, PR review)
- ✅ Set up Docker Compose
- ✅ Test: Can everyone run `docker-compose up` successfully?

**Afternoon (Parallel - 6 hours):**

**Person A:**
- Phase 1: Prompt validation
  - Implement `phases/phase1_validate/task.py`
  - Implement `phases/phase1_validate/service.py`
  - Write 3 JSON templates
  - Test with mock prompt inputs
- Start Phase 2: Animatic generation
  - Implement `phases/phase2_animatic/task.py`
  - Implement `phases/phase2_animatic/service.py`

**Person B:**
- Phase 3: Reference assets
  - Implement `phases/phase3_references/task.py`
  - Implement `phases/phase3_references/service.py`
  - Test with mock spec inputs
- Start Phase 4: Chunk generation
  - Implement `phases/phase4_chunks/task.py`
  - Implement parallel execution logic

**Person C:**
- Phase 5: Refinement
  - Implement `phases/phase5_refine/task.py`
  - Implement FFmpeg upscaling/color grading
  - Integrate MusicGen
- Phase 6: Export
  - Implement `phases/phase6_export/task.py`
  - Implement S3 upload and cleanup

**End of Day 1 Goal:** Each person has their 2 phases working in isolation with mock inputs.

---

### Day 2: Integration & MVP

**Morning (Integration - 3 hours):**
- Wire up orchestrator with real phase tasks
- Deploy to AWS (Elastic Beanstalk + RDS + ElastiCache + S3)
- Test end-to-end pipeline with 1 simple prompt
- Debug integration issues

**Afternoon (Frontend - 5 hours):**

**Person A:**
- `features/generate/` - Generate form, template selector
- Connect to POST /api/generate

**Person B:**
- `features/progress/` - Status polling, progress indicator
- Connect to GET /api/status/:id

**Person C:**
- `features/video/` - Video player, export button
- Connect to GET /api/video/:id

**End of Day 2 Goal:** Working MVP - prompt to video, deployed, accessible via URL.

---

### Day 3-5: Testing & Polish

**All Together:**
- Generate 50+ test videos with different prompts
- Fix bugs (each person owns bugs in their phases)
- Optimize parallel chunk generation
- Improve error handling and retries
- Add cost tracking and logging
- Implement rate limiting

**Quality Improvements:**
- Fine-tune prompts for better output
- Test A/V sync accuracy
- Optimize transitions
- Validate 1080p 30fps output

---

### Day 6-7: Final Submission Prep

**Quality:**
- Switch to AnimateDiff for 10 showcase videos
- Perfect color grading and audio mixing
- Generate final demo videos

**Documentation:**
- README with setup instructions
- Architecture documentation
- Cost breakdown report
- API documentation

**Demo Video:**
- Record 5-7 minute walkthrough
- Show live generation
- Explain architecture
- Showcase different templates

**Submission:**
- GitHub repo (clean, organized)
- Deployed URL
- 3+ sample videos
- Technical deep dive document

---

## 12. Testing Strategy

### 12.1 Unit Tests (Each Person Tests Their Phases)

```python
# tests/test_phase1/test_validation.py (Person A)
def test_prompt_validation():
    result = validate_prompt("uuid", "Create a luxury watch ad", [])
    assert result.status == "success"
    assert result.output_data['spec']['template'] in ['product_showcase', 'lifestyle_ad']

# tests/test_phase4/test_chunks.py (Person B)
def test_chunk_generation():
    chunk_spec = {...}
    chunk_url = generate_single_chunk(chunk_spec)
    assert chunk_url.startswith('s3://')
```

### 12.2 Integration Tests

```python
# tests/test_integration.py (Write Together)
@pytest.mark.integration
def test_end_to_end_generation():
    """Test full pipeline from prompt to final video"""
    
    response = client.post("/api/generate", json={
        "prompt": "Create a sleek ad for luxury watches"
    })
    video_id = response.json()['video_id']
    
    # Poll until complete
    timeout = 600
    start = time.time()
    while time.time() - start < timeout:
        status = client.get(f"/api/status/{video_id}").json()
        if status['status'] == 'complete':
            break
        time.sleep(5)
    
    # Verify
    video = client.get(f"/api/video/{video_id}").json()
    assert video['status'] == 'complete'
    assert video['cost_usd'] < 2.0
```

---

## 13. Git Workflow

### 13.1 Branch Strategy

```bash
# Main branches
main          # Production-ready code
develop       # Integration branch

# Feature branches (one per person per phase)
feature/phase1-validate        # Person A
feature/phase2-animatic        # Person A
feature/phase3-references      # Person B
feature/phase4-chunks          # Person B
feature/phase5-refine          # Person C
feature/phase6-export          # Person C

# Frontend features
feature/generate-form          # Person A
feature/progress-indicator     # Person B
feature/video-player           # Person C
```

### 13.2 Daily Workflow

```bash
# Morning: Pull latest
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/phase1-validate

# Work on your phase (no conflicts!)
# ... edit files in phases/phase1_validate/ only ...

# Commit frequently
git add phases/phase1_validate/
git commit -m "feat(phase1): implement prompt validation"

# Push when ready
git push origin feature/phase1-validate

# Create PR → develop
# Request review from teammates
# Merge after approval

# Afternoon: Repeat for your second phase
```

### 13.3 Merge Conflict Avoidance

**Golden Rule:** Each person ONLY edits files in their assigned folders.

**Allowed to edit:**
- Person A: `phases/phase1_validate/`, `phases/phase2_animatic/`, `features/generate/`
- Person B: `phases/phase3_references/`, `phases/phase4_chunks/`, `features/progress/`
- Person C: `phases/phase5_refine/`, `phases/phase6_export/`, `features/video/`

**Shared files (need approval from all):**
- `common/schemas.py`
- `common/models.py`
- `orchestrator/pipeline.py`
- `services/*`

---

## 14. Success Metrics

### 14.1 Technical Metrics

- ✅ Generation success rate: >90%
- ✅ Average generation time: <8 minutes for 30s video
- ✅ Cost per video: <$2.00 (MVP with Zeroscope)
- ✅ Output quality: 1080p 30fps, no visible artifacts
- ✅ A/V sync accuracy: <100ms drift

### 14.2 Competition Metrics

- ✅ Output Quality (40%): Professional, coherent, on-brand
- ✅ Architecture (25%): Clean code, scalable, well-documented
- ✅ Cost (20%): Optimized, transparent tracking
- ✅ UX (15%): Intuitive, responsive, good feedback

---

## Appendices

### A. Environment Variables

```bash
# .env
DATABASE_URL=postgresql://user:pass@localhost:5432/videogen
REDIS_URL=redis://localhost:6379/0
REPLICATE_API_TOKEN=r8_xxx...
OPENAI_API_KEY=sk-xxx...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=xxx...
S3_BUCKET=ai-video-assets-prod
AWS_REGION=us-east-2
```

### B. Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### C. Useful Commands

```bash
# Local development
docker-compose up -d
docker-compose logs -f worker

# Deploy to EB
eb deploy videogen-web
eb deploy videogen-worker

# Check worker status
celery -A app.orchestrator.celery_app inspect active

# Run tests
pytest tests/

# Database migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

---

**End of PRD v2.0**

---

This PRD is now optimized for 3-person parallel development with:
1. ✅ Phase-based vertical slices (zero merge conflicts)
2. ✅ Clear ownership boundaries
3. ✅ Shared contracts defined upfront
4. ✅ us-east-2 region specified
5. ✅ Detailed Day 1 kickoff plan
6. ✅ Git workflow for collaboration

**Ready to start building!** 🚀