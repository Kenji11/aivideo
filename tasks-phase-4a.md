# Phase 4 Tasks - Part A: Chunk Generation System

**Owner:** Person handling Phase 4  
**Goal:** Create chunk generation system with image compositing and schemas

---

## PR #15: Phase 4 Schemas

### Task 15.1: Create Phase 4 Schemas

**File:** `backend/app/phases/phase4_chunks/schemas.py`

```python
from pydantic import BaseModel
from typing import Dict, List, Optional

class ChunkSpec(BaseModel):
    """Specification for a single video chunk"""
    video_id: str
    chunk_num: int
    start_time: float
    duration: float
    beat: Dict
    animatic_frame_url: str
    style_guide_url: Optional[str] = None
    product_reference_url: Optional[str] = None
    previous_chunk_last_frame: Optional[str] = None
    prompt: str

class ChunkGenerationOutput(BaseModel):
    """Output from Phase 4"""
    stitched_video_url: str
    chunk_urls: List[str]
    total_cost: float
```

- [ ] Import BaseModel from pydantic
- [ ] Create ChunkSpec model with all chunk parameters
- [ ] Create ChunkGenerationOutput model with stitched URL and chunk URLs

---

## PR #16: Image Compositing Utility

### Task 16.1: Create Image Compositing Function

**File:** `backend/app/phases/phase4_chunks/chunk_generator.py`

```python
from PIL import Image, ImageChops, ImageFilter
import tempfile
from typing import Optional

def create_reference_composite(
    animatic_path: str,
    style_guide_path: Optional[str] = None,
    previous_frame_path: Optional[str] = None,
    animatic_weight: float = 0.7,
    style_weight: float = 0.3,
    temporal_weight: float = 0.7
) -> str:
    """
    Composite multiple reference images into single conditioning image.
    
    Strategy:
    - Chunk 0: animatic (70%) + style_guide (30%)
    - Chunks 1+: previous_frame (70%) + animatic (30%)
    
    Returns path to temporary composite image file.
    """
```

- [ ] Import PIL Image, ImageChops, ImageFilter
- [ ] Import tempfile
- [ ] Create `create_reference_composite()` function
- [ ] Load animatic image as base
- [ ] Resize all images to match animatic dimensions
- [ ] If style_guide provided, blend with animatic_weight/style_weight
- [ ] If previous_frame provided, blend with temporal_weight
- [ ] Save composite to temp file
- [ ] Return temp file path
- [ ] Add error handling for image loading failures

### Task 16.2: Implement Chunk Specification Builder

- [ ] Create `build_chunk_specs(video_id, spec, animatic_urls, reference_urls)` function
- [ ] Calculate chunk count (15 chunks for 30s video, 2s each)
- [ ] Calculate chunk overlap (0.5s overlap between chunks)
- [ ] For each chunk:
  - [ ] Calculate start_time and duration
  - [ ] Map to corresponding beat from spec
  - [ ] Get animatic frame URL for this chunk
  - [ ] Get style_guide_url from reference_urls
  - [ ] Get product_reference_url if available
  - [ ] Build prompt from beat prompt_template (keep short, ~50-100 words)
  - [ ] Create ChunkSpec object
- [ ] Return list of ChunkSpec objects

---

## PR #17: Single Chunk Generator

### Task 17.1: Implement generate_single_chunk Task

**File:** `backend/app/phases/phase4_chunks/chunk_generator.py`

- [ ] Import celery_app from orchestrator
- [ ] Import replicate_client, s3_client
- [ ] Import create_reference_composite function
- [ ] Import ChunkSpec schema
- [ ] Import COST_ZEROSCOPE_VIDEO constant

### Task 17.2: Implement Chunk Generation Logic

- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_single_chunk(self, chunk_spec: dict)` signature
- [ ] Add docstring explaining chunk generation
- [ ] Download animatic frame from S3 to temp file
- [ ] Download style guide if chunk_num == 0
- [ ] Download previous chunk's last frame if chunk_num > 0
- [ ] Call `create_reference_composite()` with appropriate weights
- [ ] Build prompt (keep concise, ~50-100 words max)
- [ ] Call Replicate Zeroscope model:
  - [ ] Model: "anotherjesse/zeroscope-v2-xl:latest"
  - [ ] Input image: composite image
  - [ ] Prompt: chunk prompt
  - [ ] num_frames: 48 (2s at 24fps)
  - [ ] fps: 24
  - [ ] width: 1024
  - [ ] height: 576
- [ ] Download generated video
- [ ] Upload chunk to S3 at `chunks/{video_id}/chunk_{chunk_num:02d}.mp4`
- [ ] Extract last frame from chunk for next chunk's temporal consistency
- [ ] Upload last frame to S3
- [ ] Return chunk S3 URL and last_frame URL
- [ ] Add error handling with retry logic

### Task 17.3: Implement Last Frame Extraction

- [ ] Create `extract_last_frame(video_path: str) -> str` function
- [ ] Use FFmpeg to extract last frame
- [ ] Command: `ffmpeg -i {video_path} -vf "select=eq(n\,47)" -vframes 1 {output_path}`
- [ ] Save frame as PNG
- [ ] Upload to S3 at `chunks/{video_id}/frames/chunk_{chunk_num}_last_frame.png`
- [ ] Return S3 URL of last frame
- [ ] Add error handling

---

## ✅ PR #15, #16, #17 Checklist

Before merging:
- [ ] All Phase 4 schemas defined
- [ ] Image compositing function works correctly
- [ ] Chunk specification builder creates correct specs
- [ ] Single chunk generator implemented
- [ ] Last frame extraction works
- [ ] Chunks uploaded to S3 correctly
- [ ] Cost tracking per chunk

**Test Commands:**
```python
# In Python shell
from app.phases.phase4_chunks.chunk_generator import create_reference_composite

# Test compositing
composite = create_reference_composite(
    animatic_path="test_animatic.png",
    style_guide_path="test_style.png",
    animatic_weight=0.7,
    style_weight=0.3
)
print(f"Composite saved to: {composite}")
```

**Next:** Move to `tasks-phase-4b.md`

