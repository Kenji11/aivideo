# Phase 2 Tasks - Part A: Animatic Prompts & Service Setup

**Owner:** Person handling Phase 2  
**Goal:** Set up animatic generation infrastructure

---

## PR #10: Phase 2 Schemas & Prompt Generation

### Task 10.1: Create Phase 2 Schemas

**File:** `backend/app/phases/phase2_animatic/schemas.py`

- [x] Import BaseModel from pydantic
- [x] Import List and Dict from typing
- [x] Create AnimaticFrameSpec model (frame_num, beat_name, shot_type, action, prompt)
- [x] Create AnimaticGenerationRequest model (video_id, beats, style)
- [x] Create AnimaticGenerationResult model (video_id, frame_urls, total_frames, cost_usd)

### Task 10.2: Create Prompt Generation Utility

**File:** `backend/app/phases/phase2_animatic/prompts.py`

- [x] Import Dict from typing
- [x] Create `generate_animatic_prompt(beat, style)` function signature
- [x] Add docstring explaining animatic characteristics
- [x] Define base_style constant for simple sketches
- [x] Extract shot_type from beat
- [x] Extract action from beat
- [x] Call `_simplify_action(action)` helper
- [x] Compose prompt string with action, shot, and base_style
- [x] Return prompt string

### Task 10.3: Implement Action Simplification

- [x] Create `_simplify_action(action)` helper function
- [x] Add docstring
- [x] Create action_map dictionary with all action mappings:
  - [x] product_reveal → "object in center of frame"
  - [x] feature_highlight → "close-up of object details"
  - [x] usage_scenario → "person holding object"
  - [x] brand_story → "object in environment"
  - [x] final_impression → "object with logo"
  - [x] establish_environment → "wide shot of location"
  - [x] introduce_character → "person standing"
  - [x] use_product → "person interacting with object"
  - [x] show_benefit → "person happy gesture"
  - [x] product_branding → "object with text"
  - [x] dramatic_intro → "bold geometric shapes"
  - [x] show_message → "text centered"
  - [x] visual_emphasis → "object prominent"
  - [x] final_message → "logo and text"
- [x] Return mapped value with fallback to "simple scene composition"

### Task 10.4: Create Negative Prompt Function

- [x] Create `create_negative_prompt()` function
- [x] Return string with negative keywords (detailed, photorealistic, complex, colorful, high quality, rendered, painted, artistic, elaborate, ornate, decorative)

### Task 10.5: Create Unit Tests for Prompts

**File:** `backend/app/tests/test_phase2/test_prompts.py`

- [x] Import pytest
- [x] Import prompt functions from phase2_animatic.prompts
- [x] Create `test_simplify_action()` - test known actions
- [x] Verify product_reveal returns "object in center of frame"
- [x] Verify introduce_character returns "person standing"
- [x] Verify unknown_action returns fallback
- [x] Create `test_create_negative_prompt()` - verify contains key terms
- [x] Create `test_generate_animatic_prompt()` - test full prompt generation
- [x] Define sample beat and style
- [x] Verify prompt contains simplified action, shot type, and sketch style

---

## PR #11: Animatic Generation Service

### Task 11.1: Create AnimaticGenerationService Class

**File:** `backend/app/phases/phase2_animatic/service.py`

- [x] Import replicate_client, s3_client
- [x] Import prompt generation functions
- [x] Import COST_SDXL_IMAGE, S3_ANIMATIC_PREFIX constants
- [x] Import List, Dict, tempfile, requests
- [x] Create AnimaticGenerationService class
- [x] Add `__init__` method to initialize clients and total_cost

### Task 11.2: Implement generate_frames Method

- [x] Create `generate_frames(video_id, spec)` method signature
- [x] Add docstring with Args and Returns
- [x] Extract beats and style from spec
- [x] Initialize empty frame_urls list
- [x] Print starting message with frame count
- [x] Loop through beats with enumerate
- [x] For each beat: print progress message
- [x] Generate prompt using generate_animatic_prompt
- [x] Create negative_prompt using create_negative_prompt
- [x] Call `_generate_single_frame` method
- [x] Append result to frame_urls
- [x] Add COST_SDXL_IMAGE to total_cost
- [x] Print completion message with count and total cost
- [x] Return frame_urls list

### Task 11.3: Implement _generate_single_frame Method

- [x] Create `_generate_single_frame(video_id, frame_num, prompt, negative_prompt)` private method
- [x] Add docstring
- [x] Wrap in try/except block
- [x] Call replicate.run with SDXL model
- [x] Set input parameters:
  - [x] prompt
  - [x] negative_prompt
  - [x] width=512
  - [x] height=512
  - [x] num_inference_steps=20
  - [x] guidance_scale=7.0
  - [x] num_outputs=1
- [x] Extract image_url from output[0]
- [x] Download image data using requests.get
- [x] Save to temporary file with .png suffix
- [x] Construct s3_key with video_id, S3_ANIMATIC_PREFIX, and frame_num
- [x] Upload to S3 using s3.upload_file
- [x] Print success message with frame_num and s3_url
- [x] Return s3_url
- [x] In except block, raise Exception with frame_num and error

---

## ✅ PR #10 & #11 Checklist

Before merging:
- [x] All Phase 2 schemas defined
- [x] Prompt generation utility working
- [x] Unit tests for prompts passing
- [x] AnimaticGenerationService implemented
- [x] Can instantiate service without errors (code structure verified)

**Test Commands:**
```python
# In Python shell
from app.phases.phase2_animatic.prompts import generate_animatic_prompt

beat = {"shot_type": "close_up", "action": "product_reveal"}
style = {"aesthetic": "luxury"}
print(generate_animatic_prompt(beat, style))
```

**Next:** Move to `tasks-phase-2b.md`

---

## PR #12: Temporary S3 Bucket Creation Script

### Task 12.1: Create Temporary Script

**File:** `backend/create_s3_buckets.py` (temporary - will be deleted)

- [x] Import boto3
- [x] Import os (for accessing environment variables)
- [x] Get AWS credentials from environment (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
- [x] Get AWS_REGION from environment (default to us-east-2)
- [x] Create boto3 S3 client with credentials
- [x] Define bucket names: ai-video-assets-dev and ai-video-assets-prod

### Task 12.2: Implement Bucket Creation Logic

- [x] Create function `create_bucket(bucket_name, region)` 
- [x] Check if bucket already exists
- [x] Create bucket if it doesn't exist
- [x] Handle region-specific bucket creation (us-east-2 requires LocationConstraint)
- [x] Print success message with bucket name and region
- [x] Handle errors gracefully (bucket already exists, permission errors, etc.)

### Task 12.3: Add Main Execution

- [x] Create main block that creates both buckets
- [x] Print starting message
- [x] Create dev bucket (ai-video-assets-dev)
- [x] Create prod bucket (ai-video-assets-prod)
- [x] Print completion message
- [x] Add note in script comments that this is temporary and will be deleted

**Note:** This script is temporary and should be deleted after buckets are created.

**Status:** ✅ Buckets created successfully:
- `ai-video-assets-dev` (development)
- `ai-video-assets-prod` (production)
- Region: `us-east-2`
- Script deleted after successful creation