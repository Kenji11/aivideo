Perfect. Let me give you the cost breakdown first, then generate the PRD.

---

## AWS Cost Breakdown for MVP

### **ElastiCache Redis:**
**t4g.micro (ARM-based, cheapest):**
- Memory: 0.5 GB
- vCPUs: 2
- Cost: **$0.016/hour = $11.52/month**
- Sufficient for: Job queue + result storage for MVP

**t3.micro (x86-based, slightly more):**
- Memory: 0.5 GB
- vCPUs: 2
- Cost: **$0.017/hour = $12.24/month**

**For MVP: t4g.micro is perfect ($11.52/month)**

---

### **RDS Postgres:**
**db.t4g.micro:**
- Memory: 1 GB
- vCPUs: 2
- Storage: 20 GB SSD
- Cost: **$0.016/hour = $11.52/month**
- Storage: **$0.115/GB-month = $2.30/month for 20GB**
- **Total: $13.82/month**

**For MVP: db.t4g.micro is perfect**

---

### **Elastic Beanstalk (Web Tier):**
**t3.small (minimum recommended for FastAPI):**
- Memory: 2 GB
- vCPUs: 2
- Cost: **$0.0208/hour = $14.98/month**

**Application Load Balancer:**
- Cost: **$16.20/month** (flat rate)
- Data processing: **$0.008/GB** (minimal for API calls)

**Total Web Tier: ~$31/month**

---

### **Elastic Beanstalk (Worker Tier):**
**Option A: Single t3.medium (4 workers):**
- Memory: 4 GB
- vCPUs: 2
- Cost: **$0.0416/hour = $29.95/month**

**Option B: Two t3.small (8 workers):**
- Cost: **2 × $14.98 = $29.96/month**

**For MVP: 1x t3.medium is fine ($29.95/month)**

---

### **S3 Storage:**
**Video outputs (assume 100 videos during dev/testing):**
- 100 videos × 100 MB = 10 GB
- Storage: **$0.023/GB-month = $0.23/month**
- PUT requests: **$0.005/1000 = negligible**
- GET requests: **$0.0004/1000 = negligible**

**Total S3: ~$0.50/month** (including some buffer)

---

### **S3 + CloudFront (Frontend):**
- S3 hosting: **~$0.10/month** (tiny React app)
- CloudFront: **$0.085/GB** for first 10 TB
- Assume 1000 page loads × 2 MB = 2 GB
- CloudFront cost: **$0.17/month**

**Total Frontend: ~$0.30/month**

---

### **Data Transfer (Egress):**
**From S3/EB to internet:**
- First 100 GB/month: **$0.09/GB**
- Assume 50 videos downloaded × 100 MB = 5 GB
- Cost: **$0.45/month**

---

### **Total AWS Infrastructure Cost (Monthly):**

| Service | Instance Type | Cost/Month |
|---------|---------------|------------|
| ElastiCache Redis | t4g.micro | $11.52 |
| RDS Postgres | db.t4g.micro + 20GB | $13.82 |
| EB Web Tier | t3.small | $14.98 |
| Application Load Balancer | - | $16.20 |
| EB Worker Tier | t3.medium | $29.95 |
| S3 Storage | - | $0.50 |
| S3 + CloudFront (Frontend) | - | $0.30 |
| Data Transfer | - | $0.45 |
| **TOTAL** | | **~$87.72/month** |

**Add buffer for unexpected usage: ~$100/month**

---

### **API Costs (Per Video):**

| Service | Model | Cost |
|---------|-------|------|
| Prompt Validation | GPT-4 Turbo | $0.01 |
| Animatic (15 keyframes) | SDXL | $0.08 |
| Reference Assets (3 images) | SDXL | $0.02 |
| Video Chunks (15×2s) | Zeroscope (dev) | $1.50 |
| Video Chunks (15×2s) | AnimateDiff (final) | $3.00 |
| Background Music | MusicGen | $0.15 |
| **TOTAL PER VIDEO** | | **$1.76 (dev)** |
| **TOTAL PER VIDEO** | | **$3.26 (final)** |

**For 100 test videos during development:**
- With Zeroscope: **$176**
- Switch to AnimateDiff for final 10 showcase videos: **$32.60**
- **Total API costs during project: ~$200-$250**

---

### **Grand Total for MVP (One Week):**
- AWS Infrastructure: **$25** (1 week ≈ $100/month ÷ 4)
- API costs (development): **$200-$250**
- **Total: $225-$275 for the week**

**This is very reasonable.** You're well under $500 for the entire MVP development + showcase.

---

## Cost Optimization Notes:

1. **Use Zeroscope for ALL development** (save $1.50/video)
2. **Only use AnimateDiff for final 10 showcase videos** (when quality matters)
3. **Delete intermediate chunks immediately** after stitching (save S3 costs)
4. **Terminate infrastructure after showcase** (save $100/month)
5. **Use EB auto-scaling**: Scale down to 0 workers when queue is empty (save compute)

---

Now generating the full PRD...

---

# Product Requirements Document (PRD)
## AI Video Generation Pipeline - Ad Creative MVP

**Version:** 1.0  
**Date:** November 14, 2025  
**Project Duration:** 7 days (MVP in 48 hours)  
**Target:** $5,000 Bounty Competition

---

## Executive Summary

Build an end-to-end AI video generation pipeline that transforms text prompts into professional 30-second advertisement videos. The system uses a hybrid approach: deterministic templates for structure + generative AI for content, ensuring reliability, consistency, and cost-effectiveness.

**Key Innovation:** Six-phase pipeline that progressively refines from low-fidelity animatics to high-quality final videos, using animatics as motion references to ensure temporal consistency.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technical Architecture](#technical-architecture)
3. [System Components](#system-components)
4. [Pipeline Phases (Detailed)](#pipeline-phases)
5. [Data Models](#data-models)
6. [API Specifications](#api-specifications)
7. [Template System](#template-system)
8. [Deployment Architecture](#deployment-architecture)
9. [Cost Analysis](#cost-analysis)
10. [Development Roadmap](#development-roadmap)
11. [Testing Strategy](#testing-strategy)

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

## 2. Technical Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                        │
│              (React 18 + Tailwind + shadcn)             │
│                   Deployed on S3                         │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS
                       ↓
┌─────────────────────────────────────────────────────────┐
│                  CloudFront (CDN)                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│         Application Load Balancer (ALB)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│    Elastic Beanstalk - Web Tier (FastAPI in Docker)    │
│                                                          │
│  POST /api/generate     - Submit video generation       │
│  GET  /api/status/:id   - Check generation status       │
│  GET  /api/video/:id    - Get final video URL           │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
               ↓                      ↓
┌──────────────────────┐   ┌─────────────────────────────┐
│  ElastiCache Redis   │   │      RDS PostgreSQL         │
│   (Job Queue +       │   │  (Video metadata, costs,    │
│    Result Store)     │   │   user data)                │
└──────────┬───────────┘   └─────────────────────────────┘
           │
           │ Workers pull jobs
           ↓
┌─────────────────────────────────────────────────────────┐
│  Elastic Beanstalk - Worker Tier (Celery in Docker)    │
│                                                          │
│  - 4-8 concurrent workers                               │
│  - Parallel chunk generation (15 chunks per video)      │
│  - Calls to Replicate API (Zeroscope, SDXL, MusicGen)  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────┐
│              S3 Bucket (Video Storage)                   │
│                                                          │
│  /videos/:video_id/animatic/frame_*.png                 │
│  /videos/:video_id/references/style_guide.png           │
│  /videos/:video_id/chunks/chunk_*.mp4                   │
│  /videos/:video_id/final.mp4                            │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

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

**Development Tools:**
- Docker + Docker Compose (local dev)
- Poetry (Python dependency management)
- Alembic (database migrations)
- Pytest (testing)

---

## 3. System Components

### 3.1 FastAPI Application Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Environment configuration
│   ├── database.py             # PostgreSQL connection
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── generate.py         # POST /generate endpoint
│   │   ├── status.py           # GET /status/:id endpoint
│   │   └── video.py            # GET /video/:id endpoint
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── pipeline.py         # Main video generation orchestration
│   │   ├── phase1_validate.py  # Prompt validation
│   │   ├── phase2_animatic.py  # Animatic generation
│   │   ├── phase3_references.py # Reference asset generation
│   │   ├── phase4_chunks.py    # Video chunk generation
│   │   ├── phase5_refine.py    # Refinement passes
│   │   └── phase6_export.py    # Export handling
│   ├── services/
│   │   ├── __init__.py
│   │   ├── replicate_client.py # Replicate API wrapper
│   │   ├── openai_client.py    # OpenAI API wrapper
│   │   ├── s3_client.py        # S3 upload/download
│   │   └── ffmpeg_service.py   # Video processing
│   └── templates/
│       ├── product_showcase.json
│       ├── lifestyle_ad.json
│       └── announcement.json
├── tests/
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── docker-compose.yml
```

### 3.2 React Application Structure

```
frontend/
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── components/
│   │   ├── GenerateForm.tsx    # Prompt input + template selection
│   │   ├── VideoPlayer.tsx     # HTML5 player with controls
│   │   ├── ProgressIndicator.tsx # Generation status display
│   │   ├── ExportButton.tsx    # Download handler
│   │   └── ui/                 # shadcn components
│   ├── hooks/
│   │   ├── useVideoGeneration.ts # API polling logic
│   │   └── useVideoPlayer.ts   # Player controls logic
│   ├── lib/
│   │   ├── api.ts              # API client
│   │   └── utils.ts            # Helpers
│   └── types/
│       └── index.ts            # TypeScript interfaces
├── public/
├── index.html
├── package.json
├── tailwind.config.js
└── vite.config.ts
```

---

## 4. Pipeline Phases (Detailed)

### Phase 1: Prompt Validation & Spec Extraction

**Objective:** Convert natural language prompt into structured specification.

**Input:**
```json
{
  "prompt": "Create a sleek ad for luxury watches with gold aesthetics",
  "assets": [
    {"type": "logo", "url": "s3://..."},
    {"type": "product_image", "url": "s3://..."}
  ]
}
```

**Process:**
1. Send prompt to GPT-4 Turbo with structured output schema
2. Extract: duration, style, tone, product, action beats, template selection
3. Validate against template constraints
4. Return structured spec or request clarification

**Output:**
```json
{
  "video_id": "uuid-1234",
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
  "product": {
    "name": "luxury watch",
    "category": "accessories"
  },
  "beats": [
    {"start": 0, "duration": 3, "action": "product_reveal", "shot": "close_up"},
    {"start": 3, "duration": 5, "action": "detail_showcase", "shot": "macro"},
    {"start": 8, "duration": 7, "action": "lifestyle_context", "shot": "medium"},
    {"start": 15, "duration": 10, "action": "brand_story", "shot": "wide"},
    {"start": 25, "duration": 5, "action": "call_to_action", "shot": "close_up"}
  ],
  "transitions": ["fade", "cut", "fade", "cut"],
  "audio": {
    "music_style": "orchestral",
    "tempo": "slow",
    "mood": "sophisticated"
  },
  "uploaded_assets": ["s3://logo.png", "s3://product.jpg"]
}
```

**Model:** OpenAI GPT-4 Turbo  
**Cost:** ~$0.01 per validation  
**Time:** ~2 seconds

**Implementation:**
```python
# app/tasks/phase1_validate.py
from app.services.openai_client import openai_client
from app.templates import load_template

@celery_app.task
def validate_and_extract_spec(prompt: str, assets: List[dict]) -> dict:
    """Phase 1: Validate prompt and extract structured spec"""
    
    system_prompt = """
    You are a video production assistant. Extract structured specifications from user prompts.
    
    Available templates:
    - product_showcase: Focus on product features and details
    - lifestyle_ad: Show product in real-world context
    - announcement: Brand message or campaign announcement
    
    Return JSON with: template, style, beats, audio preferences.
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    spec = json.loads(response.choices[0].message.content)
    
    # Validate against template
    template = load_template(spec['template'])
    validated_spec = template.validate_and_merge(spec)
    
    # Add uploaded assets
    validated_spec['uploaded_assets'] = assets
    
    return validated_spec
```

---

### Phase 2: Animatic Generation

**Objective:** Generate low-fidelity structural reference frames for temporal consistency.

**Input:** Spec from Phase 1

**Process:**
1. Extract keyframes (1 per 2 seconds = 15 frames for 30s video)
2. Generate simple, low-detail images using SDXL with "sketch" style
3. Store in S3: `/videos/:video_id/animatic/frame_00.png` through `frame_14.png`
4. These frames become ControlNet inputs for Phase 4

**Output:** List of S3 URLs for animatic frames

**Why This Matters:**
- Animatic frames define motion/composition cheaply
- Phase 4 uses these as structural references (via ControlNet)
- Ensures temporal consistency (character at frame 0 matches frame 14)
- User does NOT see animatic in MVP (internal reference only)

**Model:** SDXL (Replicate)  
**Cost:** $0.0055 × 15 frames = $0.08 per video  
**Time:** ~30 seconds

**Prompt Strategy:**
```python
# Low-detail, structural prompts
prompts = [
    "simple line drawing of luxury watch close-up, minimal detail, sketch style",
    "simple line drawing of watch mechanism macro view, minimal detail",
    "simple line drawing of person wearing watch, minimal detail",
    # ... etc for each beat
]
```

**Implementation:**
```python
# app/tasks/phase2_animatic.py
from app.services.replicate_client import replicate_client
from app.services.s3_client import s3_client

@celery_app.task
def generate_animatic(video_id: str, spec: dict) -> List[str]:
    """Phase 2: Generate low-fidelity animatic frames"""
    
    animatic_frames = []
    
    for i, beat in enumerate(spec['beats']):
        # Create simple, low-detail prompt
        prompt = f"simple line drawing of {beat['action']}, minimal detail, sketch style, {beat['shot']} shot"
        
        # Generate with SDXL
        result = replicate_client.run(
            "stability-ai/sdxl:latest",
            input={
                "prompt": prompt,
                "negative_prompt": "detailed, photorealistic, complex, colorful",
                "width": 512,  # Low res for speed
                "height": 512,
                "num_inference_steps": 20  # Fast generation
            }
        )
        
        # Upload to S3
        frame_url = s3_client.upload_image(
            result[0],
            key=f"videos/{video_id}/animatic/frame_{i:02d}.png"
        )
        
        animatic_frames.append(frame_url)
    
    return animatic_frames
```

---

### Phase 3: Reference Asset Generation

**Objective:** Create canonical visual references for consistency.

**Input:** Spec from Phase 1

**Process:**
1. Generate style guide image (defines overall aesthetic)
2. Generate character/object references if needed
3. Use uploaded assets (logos, product images) if provided
4. Store in S3: `/videos/:video_id/references/`

**Output:**
```json
{
  "style_guide": "s3://videos/uuid/references/style_guide.png",
  "product_reference": "s3://videos/uuid/references/product.png",
  "logo": "s3://videos/uuid/references/logo.png"
}
```

**Model:** SDXL (Replicate)  
**Cost:** $0.0055 × 3 images = $0.02 per video  
**Time:** ~15 seconds

**Implementation:**
```python
# app/tasks/phase3_references.py

@celery_app.task
def generate_references(video_id: str, spec: dict) -> dict:
    """Phase 3: Generate reference assets for consistency"""
    
    references = {}
    
    # 1. Generate style guide
    style_prompt = f"{spec['style']['aesthetic']} aesthetic, {', '.join(spec['style']['color_palette'])}, {spec['style']['lighting']} lighting, professional photography"
    
    style_guide = replicate_client.run(
        "stability-ai/sdxl:latest",
        input={
            "prompt": style_prompt,
            "width": 1024,
            "height": 1024
        }
    )
    
    references['style_guide'] = s3_client.upload_image(
        style_guide[0],
        key=f"videos/{video_id}/references/style_guide.png"
    )
    
    # 2. Use uploaded assets if provided
    if spec.get('uploaded_assets'):
        references['uploaded'] = spec['uploaded_assets']
    
    # 3. Generate product reference if no upload
    if 'product_image' not in spec.get('uploaded_assets', []):
        product_prompt = f"{spec['product']['name']}, {style_prompt}"
        product_ref = replicate_client.run("stability-ai/sdxl:latest", input={"prompt": product_prompt})
        references['product'] = s3_client.upload_image(product_ref[0], key=f"videos/{video_id}/references/product.png")
    
    return references
```

---

### Phase 4: Chunked Video Generation

**Objective:** Generate video chunks with temporal consistency using animatic + references.

**Input:**
- Spec from Phase 1
- Animatic frames from Phase 2
- Reference assets from Phase 3

**Process:**
1. Divide 30s video into 2s chunks (15 chunks total)
2. For each chunk:
   - Use corresponding animatic frame as ControlNet/structure input
   - Include style guide in prompt
   - Generate with Zeroscope (dev) or AnimateDiff (final)
3. Apply 0.5s overlap between chunks (chunk 1: 0-2s, chunk 2: 1.5-3.5s)
4. Generate chunks in parallel using Celery `group()`
5. Store in S3: `/videos/:video_id/chunks/chunk_00.mp4` through `chunk_14.mp4`

**Transitions:** Apply deterministically from template (no model involvement)

**Model:** Zeroscope (MVP) or AnimateDiff (final)  
**Cost:** $0.10 × 15 = $1.50 (Zeroscope) or $0.20 × 15 = $3.00 (AnimateDiff)  
**Time:** ~5-8 minutes (parallel execution)

**Chunk Specification:**
```python
chunk_spec = {
    "chunk_num": 0,
    "start_time": 0.0,
    "duration": 2.0,
    "animatic_frame": "s3://videos/uuid/animatic/frame_00.png",
    "style_guide": "s3://videos/uuid/references/style_guide.png",
    "prompt": "luxury watch close-up with gold accents, dramatic lighting",
    "negative_prompt": "blurry, low quality, distorted",
    "previous_chunk_frames": None  # Or last 12 frames from previous chunk
}
```

**Implementation:**
```python
# app/tasks/phase4_chunks.py
from celery import group

@celery_app.task
def generate_video_chunks(video_id: str, spec: dict, animatic_frames: List[str], references: dict) -> List[str]:
    """Phase 4: Generate video chunks in parallel"""
    
    # Create chunk specifications
    chunk_specs = []
    for i, beat in enumerate(spec['beats']):
        chunk_spec = {
            "video_id": video_id,
            "chunk_num": i,
            "start_time": beat['start'],
            "duration": min(2.0, beat['duration']),  # 2s max per chunk
            "animatic_frame": animatic_frames[i],
            "style_guide": references['style_guide'],
            "prompt": f"{beat['action']}, {spec['style']['aesthetic']} style, {beat['shot']} shot",
            "fps": 30,
            "frames": 48  # 2s × 24fps (we'll interpolate to 30fps later)
        }
        chunk_specs.append(chunk_spec)
    
    # Execute chunks in parallel
    chunk_tasks = group([
        generate_single_chunk.s(chunk_spec)
        for chunk_spec in chunk_specs
    ])
    
    result = chunk_tasks.apply_async()
    chunk_urls = result.get(timeout=600)  # 10 min timeout
    
    return chunk_urls

@celery_app.task
def generate_single_chunk(chunk_spec: dict) -> str:
    """Generate a single video chunk"""
    
    # Download animatic frame for ControlNet
    animatic_image = s3_client.download_image(chunk_spec['animatic_frame'])
    
    # Generate video chunk with Zeroscope (img2vid)
    result = replicate_client.run(
        "anotherjesse/zeroscope-v2-xl:latest",
        input={
            "image": animatic_image,  # Use animatic as structural reference
            "prompt": chunk_spec['prompt'],
            "num_frames": chunk_spec['frames'],
            "fps": chunk_spec['fps'],
            "width": 1024,
            "height": 576
        }
    )
    
    # Upload chunk to S3
    chunk_url = s3_client.upload_video(
        result,
        key=f"videos/{chunk_spec['video_id']}/chunks/chunk_{chunk_spec['chunk_num']:02d}.mp4"
    )
    
    return chunk_url
```

**Stitching with Transitions:**
```python
# app/services/ffmpeg_service.py
import subprocess

def stitch_chunks_with_transitions(chunk_urls: List[str], transitions: List[str], output_path: str):
    """Stitch video chunks with deterministic transitions"""
    
    # Download all chunks
    chunk_files = [s3_client.download_video(url) for url in chunk_urls]
    
    # Build FFmpeg filter chain
    filter_parts = []
    for i, (chunk, transition) in enumerate(zip(chunk_files, transitions)):
        if transition == "cut":
            # Direct concatenation
            filter_parts.append(f"[{i}:v]")
        elif transition == "fade":
            # 0.5s crossfade
            filter_parts.append(f"[{i}:v][{i+1}:v]xfade=transition=fade:duration=0.5:offset={i*2-0.25}[v{i}];")
    
    # Execute FFmpeg
    cmd = [
        "ffmpeg",
        *[f"-i {chunk}" for chunk in chunk_files],
        "-filter_complex", "".join(filter_parts),
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        output_path
    ]
    
    subprocess.run(cmd, check=True)
    
    return output_path
```

---

### Phase 5: Refinement

**Objective:** Polish the stitched video for professional quality.

**Input:** Stitched video from Phase 4

**Process:**
1. **Temporal Smoothing:** Fix jitter at chunk boundaries using optical flow
2. **Upscaling:** If generated at lower res, upscale to 1080p
3. **Color Grading:** Apply LUT based on template aesthetic
4. **Audio Sync:** Generate background music and sync to video
5. **Final Encode:** Compress to target file size with high quality

**Tools:**
- FFmpeg (temporal smoothing, upscaling, color grading)
- Real-ESRGAN (optional AI upscaling)
- MusicGen (background music)

**Cost:** $0.15 (MusicGen)  
**Time:** ~2 minutes

**Implementation:**
```python
# app/tasks/phase5_refine.py

@celery_app.task
def refine_video(video_id: str, stitched_video_url: str, spec: dict) -> str:
    """Phase 5: Refine and polish video"""
    
    video_path = s3_client.download_video(stitched_video_url)
    
    # 1. Temporal smoothing (optical flow interpolation)
    smoothed = ffmpeg_service.apply_optical_flow(video_path)
    
    # 2. Upscale to 1080p if needed
    if spec['resolution'] == '1080p':
        upscaled = ffmpeg_service.upscale_video(smoothed, width=1920, height=1080)
    else:
        upscaled = smoothed
    
    # 3. Color grading (apply LUT)
    lut_file = f"luts/{spec['style']['aesthetic']}.cube"
    graded = ffmpeg_service.apply_lut(upscaled, lut_file)
    
    # 4. Generate background music
    music_url = generate_background_music.delay(video_id, spec['audio']).get()
    music_path = s3_client.download_audio(music_url)
    
    # 5. Mix audio
    final_video = ffmpeg_service.add_audio(graded, music_path, volume=0.3)
    
    # 6. Final encode
    encoded = ffmpeg_service.encode_final(
        final_video,
        codec='libx264',
        preset='medium',
        crf=23,
        audio_codec='aac',
        audio_bitrate='192k'
    )
    
    # Upload final video
    final_url = s3_client.upload_video(
        encoded,
        key=f"videos/{video_id}/final.mp4"
    )
    
    # Clean up intermediates
    s3_client.delete_prefix(f"videos/{video_id}/chunks/")
    s3_client.delete_prefix(f"videos/{video_id}/animatic/")
    
    return final_url

@celery_app.task
def generate_background_music(video_id: str, audio_spec: dict) -> str:
    """Generate background music with MusicGen"""
    
    prompt = f"{audio_spec['music_style']} music, {audio_spec['tempo']} tempo, {audio_spec['mood']} mood, 30 seconds"
    
    result = replicate_client.run(
        "meta/musicgen:latest",
        input={
            "prompt": prompt,
            "duration": 30,
            "model_version": "stereo-large"
        }
    )
    
    music_url = s3_client.upload_audio(
        result,
        key=f"videos/{video_id}/music.mp3"
    )
    
    return music_url
```

---

### Phase 6: Preview & Export

**Objective:** Provide user with playback controls and download capability.

**Frontend Implementation:**
```tsx
// src/components/VideoPlayer.tsx
import React, { useRef, useState } from 'react';

interface VideoPlayerProps {
  videoUrl: string;
  onExport: () => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({ videoUrl, onExport }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  
  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };
  
  const handleSkip = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime += seconds;
    }
  };
  
  return (
    <div className="video-player-container">
      <video
        ref={videoRef}
        src={videoUrl}
        className="w-full rounded-lg shadow-lg"
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />
      
      <div className="controls flex gap-4 mt-4">
        <button onClick={() => handleSkip(-10)}>-10s</button>
        <button onClick={handlePlayPause}>
          {isPlaying ? 'Pause' : 'Play'}
        </button>
        <button onClick={() => handleSkip(10)}>+10s</button>
        <button onClick={onExport} className="ml-auto">
          Export MP4
        </button>
      </div>
    </div>
  );
};
```

**Export Implementation:**
```python
# app/api/video.py
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()

@router.get("/api/video/{video_id}/download")
async def download_video(video_id: str):
    """Generate pre-signed S3 URL for download"""
    
    video = db.query(VideoGeneration).filter_by(id=video_id).first()
    
    if not video or video.status != 'complete':
        raise HTTPException(status_code=404)
    
    # Generate pre-signed URL (valid for 1 hour)
    download_url = s3_client.generate_presigned_url(
        video.final_video_url,
        expiration=3600
    )
    
    return RedirectResponse(download_url)
```

---

## 5. Data Models

### 5.1 Database Schema (PostgreSQL)

```python
# app/models.py
from sqlalchemy import Column, String, Float, DateTime, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class VideoStatus(str, enum.Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    GENERATING_ANIMATIC = "generating_animatic"
    GENERATING_REFERENCES = "generating_references"
    GENERATING_CHUNKS = "generating_chunks"
    REFINING = "refining"
    COMPLETE = "complete"
    FAILED = "failed"

class VideoGeneration(Base):
    __tablename__ = "video_generations"
    
    id = Column(String, primary_key=True)  # UUID
    user_id = Column(String, nullable=True)  # For final submission (auth)
    
    # Input
    prompt = Column(String, nullable=False)
    uploaded_assets = Column(JSON, default=[])
    
    # Spec
    spec = Column(JSON, nullable=True)
    template = Column(String, nullable=True)
    
    # Status
    status = Column(Enum(VideoStatus), default=VideoStatus.QUEUED)
    progress = Column(Float, default=0.0)  # 0-100
    error_message = Column(String, nullable=True)
    
    # Outputs
    animatic_frames = Column(JSON, default=[])
    reference_assets = Column(JSON, default={})
    chunk_urls = Column(JSON, default=[])
    final_video_url = Column(String, nullable=True)
    
    # Metadata
    cost_usd = Column(Float, default=0.0)
    generation_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Cost breakdown (for analytics)
    cost_breakdown = Column(JSON, default={
        "prompt_validation": 0.0,
        "animatic": 0.0,
        "references": 0.0,
        "chunks": 0.0,
        "music": 0.0,
        "total": 0.0
    })
```

### 5.2 Pydantic Schemas (API)

```python
# app/schemas.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=10, max_length=1000)
    assets: List[Dict[str, str]] = Field(default=[])
    
class GenerateResponse(BaseModel):
    video_id: str
    status: str
    message: str

class StatusResponse(BaseModel):
    video_id: str
    status: str
    progress: float
    current_phase: str
    estimated_time_remaining: Optional[int]
    error: Optional[str]

class VideoResponse(BaseModel):
    video_id: str
    status: str
    final_video_url: Optional[str]
    cost_usd: float
    generation_time_seconds: float
    created_at: datetime
    completed_at: Optional[datetime]
    spec: Dict
```

---

## 6. API Specifications

### 6.1 Endpoints

#### POST /api/generate
**Request:**
```json
{
  "prompt": "Create a sleek ad for luxury watches with gold aesthetics",
  "assets": [
    {"type": "logo", "url": "https://..."}
  ]
}
```

**Response (202 Accepted):**
```json
{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Video generation started"
}
```

#### GET /api/status/:video_id
**Response:**
```json
{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "generating_chunks",
  "progress": 65.0,
  "current_phase": "Phase 4: Generating video chunks (10/15 complete)",
  "estimated_time_remaining": 180
}
```

#### GET /api/video/:video_id
**Response:**
```json
{
  "video_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "complete",
  "final_video_url": "https://s3.amazonaws.com/bucket/videos/uuid/final.mp4",
  "cost_usd": 1.76,
  "generation_time_seconds": 420,
  "created_at": "2025-11-14T10:00:00Z",
  "completed_at": "2025-11-14T10:07:00Z",
  "spec": { ... }
}
```

#### GET /api/video/:video_id/download
**Response:** Redirect to pre-signed S3 URL

---

## 7. Template System

### 7.1 Template Structure

```json
// templates/product_showcase.json
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

### 7.2 Other Templates

**templates/lifestyle_ad.json:**
- Focus on real-world usage
- More cuts, dynamic pacing
- Upbeat music
- Bright, vibrant color grading

**templates/announcement.json:**
- Text-heavy (brand message)
- Minimal product shots
- Bold graphics
- Dramatic music

---

## 8. Deployment Architecture

### 8.1 Local Development (Docker Compose)

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
    volumes:
      - ./backend:/app
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

volumes:
  postgres_data:
```

**Start local development:**
```bash
docker-compose up
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### 8.2 AWS Deployment Steps

#### Step 1: Create S3 Bucket
```bash
aws s3 mb s3://videogen-outputs-prod
aws s3api put-bucket-cors --bucket videogen-outputs-prod --cors-configuration file://cors.json
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
  --vpc-security-group-ids sg-xxxxx \
  --db-subnet-group-name default
```

#### Step 3: Create ElastiCache Redis
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id videogen-redis \
  --cache-node-type cache.t4g.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --security-group-ids sg-xxxxx
```

#### Step 4: Initialize Elastic Beanstalk
```bash
cd backend
eb init -p docker videogen-api --region us-east-1
```

#### Step 5: Create Web Tier Environment
```bash
eb create videogen-web \
  --instance-type t3.small \
  --envvars \
    DATABASE_URL=<rds_url> \
    REDIS_URL=<elasticache_url> \
    REPLICATE_API_TOKEN=<token> \
    OPENAI_API_KEY=<key> \
    S3_BUCKET=videogen-outputs-prod
```

#### Step 6: Create Worker Tier Environment
```bash
eb create videogen-worker \
  --tier worker \
  --instance-type t3.medium \
  --envvars \
    DATABASE_URL=<rds_url> \
    REDIS_URL=<elasticache_url> \
    REPLICATE_API_TOKEN=<token> \
    OPENAI_API_KEY=<key> \
    S3_BUCKET=videogen-outputs-prod
```

#### Step 7: Deploy Frontend to S3 + CloudFront
```bash
cd frontend
npm run build
aws s3 sync dist/ s3://videogen-frontend-prod
aws cloudfront create-invalidation --distribution-id <id> --paths "/*"
```

---

## 9. Cost Analysis

### 9.1 Infrastructure Costs (Monthly)

| Service | Instance | Monthly Cost |
|---------|----------|--------------|
| ElastiCache Redis | t4g.micro | $11.52 |
| RDS Postgres | db.t4g.micro | $13.82 |
| EB Web Tier | t3.small | $14.98 |
| ALB | - | $16.20 |
| EB Worker Tier | t3.medium | $29.95 |
| S3 Storage | - | $0.50 |
| CloudFront | - | $0.30 |
| Data Transfer | - | $0.45 |
| **Total** | | **$87.72/month** |

### 9.2 Per-Video Generation Costs

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

### 9.3 Budget for Competition Week

- Infrastructure (1 week): ~$25
- 90 test videos (Zeroscope): $158
- 10 showcase videos (AnimateDiff): $33
- **Total: ~$216**

**Well under budget. Leaves room for experimentation and retries.**

---

## 10. Development Roadmap

### Day 1-2: MVP (48 hours)

**Backend:**
- ✅ FastAPI skeleton with Celery + Redis
- ✅ Phase 1: Prompt validation (GPT-4)
- ✅ Phase 2: Animatic generation (SDXL)
- ✅ Phase 3: Reference assets (SDXL)
- ✅ Phase 4: Chunked generation (Zeroscope)
- ✅ Phase 5: Basic refinement (FFmpeg stitching + music)
- ✅ Phase 6: S3 upload + download endpoint
- ✅ Database models + basic API endpoints

**Frontend:**
- ✅ Generate form (prompt input + template selector)
- ✅ Status polling (progress indicator)
- ✅ Video player (HTML5 with basic controls)
- ✅ Download button

**Deployment:**
- ✅ Docker Compose for local dev
- ✅ Deploy to Elastic Beanstalk (Web + Worker)
- ✅ S3 + CloudFront for frontend

**Deliverable:** Working end-to-end pipeline generating 30s ads

---

### Day 3-5: Polish & Testing

**Backend:**
- ✅ Improve error handling and retries
- ✅ Add all 3 templates (product showcase, lifestyle, announcement)
- ✅ Optimize parallel chunk generation
- ✅ Add cost tracking and logging
- ✅ Implement rate limiting (1 video per user)

**Frontend:**
- ✅ Better UI/UX (loading states, error messages)
- ✅ Template preview/selection interface
- ✅ Asset upload functionality
- ✅ Cost display (optional)

**Testing:**
- ✅ Generate 50+ test videos with different prompts
- ✅ Validate quality, consistency, A/V sync
- ✅ Stress test (multiple concurrent users)
- ✅ Cost optimization (ensure <$2/minute)

---

### Day 6-7: Final Submission Prep

**Quality:**
- ✅ Switch to AnimateDiff for 10 showcase videos
- ✅ Fine-tune prompts for best quality
- ✅ Perfect A/V sync and color grading
- ✅ Ensure 1080p 30fps output

**Documentation:**
- ✅ README with setup instructions
- ✅ Architecture documentation
- ✅ Cost breakdown report
- ✅ API documentation

**Demo Video:**
- ✅ Record 5-7 minute walkthrough
- ✅ Show live generation
- ✅ Explain architecture
- ✅ Showcase different templates

**Submission:**
- ✅ GitHub repo (clean, organized)
- ✅ Deployed URL (working API + web interface)
- ✅ 3+ sample videos (different styles)
- ✅ Technical deep dive document

---

### Post-Competition (If Pursuing Further)

- User authentication and accounts
- Reference asset library with vector DB
- Iterative refinement ("make it more energetic")
- Timeline editing interface
- Multi-format export (vertical, square)
- Music video category
- Advanced templates
- Cost optimizations (model fine-tuning)

---

## 11. Testing Strategy

### 11.1 Unit Tests

```python
# tests/test_phase1_validate.py
def test_prompt_validation():
    result = validate_and_extract_spec("Create a luxury watch ad")
    assert result['template'] in ['product_showcase', 'lifestyle_ad', 'announcement']
    assert result['duration'] == 30
    assert 'beats' in result

# tests/test_phase4_chunks.py
def test_chunk_generation():
    chunk_spec = {...}
    chunk_url = generate_single_chunk(chunk_spec)
    assert chunk_url.startswith('s3://')
    
    # Verify video properties
    video = download_video(chunk_url)
    assert video.duration == 2.0
    assert video.fps == 30
```

### 11.2 Integration Tests

```python
# tests/test_full_pipeline.py
@pytest.mark.integration
def test_end_to_end_generation():
    """Test full pipeline from prompt to final video"""
    
    # Submit generation
    response = client.post("/api/generate", json={
        "prompt": "Create a sleek ad for luxury watches"
    })
    video_id = response.json()['video_id']
    
    # Poll until complete (with timeout)
    timeout = 600  # 10 minutes
    start = time.time()
    while time.time() - start < timeout:
        status = client.get(f"/api/status/{video_id}").json()
        if status['status'] == 'complete':
            break
        time.sleep(5)
    
    # Verify final video
    video = client.get(f"/api/video/{video_id}").json()
    assert video['status'] == 'complete'
    assert video['final_video_url'] is not None
    assert video['cost_usd'] < 2.0  # Under $2/minute target
    
    # Download and verify video properties
    video_file = download_video(video['final_video_url'])
    assert video_file.duration == 30
    assert video_file.resolution == (1920, 1080)
    assert video_file.fps == 30
```

### 11.3 Load Testing

```python
# tests/test_load.py
import concurrent.futures

def test_concurrent_users():
    """Test 5 concurrent video generations"""
    
    prompts = [
        "Luxury watch ad",
        "Sports car commercial",
        "Skincare product showcase",
        "Tech gadget announcement",
        "Fashion brand campaign"
    ]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(generate_video, prompt)
            for prompt in prompts
        ]
        
        results = [f.result() for f in futures]
    
    # All should complete successfully
    assert all(r['status'] == 'complete' for r in results)
```

---

## 12. Risk Mitigation

### 12.1 Known Risks

**Risk: API rate limits (Replicate)**
- Mitigation: Implement exponential backoff + retry logic
- Fallback: Queue jobs and process serially if parallel fails

**Risk: Video quality issues (temporal drift, artifacts)**
- Mitigation: Use animatic as structural reference (ControlNet)
- Fallback: Motion-first pipeline (Phase 2 alternative)

**Risk: Generation timeout (>10 minutes)**
- Mitigation: Optimize chunk size (2s), use faster models for dev
- Fallback: Reduce video length or chunk count

**Risk: Cost overruns**
- Mitigation: Track costs in real-time, alert if exceeding budget
- Fallback: Switch to cheaper models (Zeroscope vs AnimateDiff)

**Risk: Concurrent user overload**
- Mitigation: Rate limiting (1 video per user), queue system
- Fallback: Auto-scale workers based on queue depth

---

## 13. Success Metrics

### 13.1 Technical Metrics

- ✅ Generation success rate: >90%
- ✅ Average generation time: <8 minutes for 30s video
- ✅ Cost per video: <$2.00 (MVP with Zeroscope)
- ✅ Output quality: 1080p 30fps, no visible artifacts
- ✅ A/V sync accuracy: <100ms drift

### 13.2 Competition Metrics

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
S3_BUCKET=videogen-outputs-prod
S3_REGION=us-east-1
```

### B. FFmpeg Installation (for workers)

```dockerfile
# Dockerfile
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
celery -A app.tasks.celery_app inspect active

# Monitor costs
aws ce get-cost-and-usage --time-period Start=2025-11-14,End=2025-11-21 --granularity DAILY --metrics UnblendedCost
```

---

**End of PRD**

---

This PRD is comprehensive and ready for implementation. You have:
1. ✅ Clear architecture (Docker + EB + Celery + Redis)
2. ✅ Detailed phase-by-phase implementation
3. ✅ Cost breakdowns ($216 total for competition week)
4. ✅ All 6 phases specified (animatic as AI reference, not user approval)
5. ✅ Deployment steps for AWS
6. ✅ Template system with JSON configs
7. ✅ API specs and data models
8. ✅ Testing strategy
9. ✅ Development roadmap (48-hour MVP, then polish)

**Next steps:** Start building! Begin with Docker Compose setup, then Phase 1 (prompt validation), then iterate through phases. Let me know when you're ready to dive into implementation details for any specific component.