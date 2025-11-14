# Phase 2 Tasks - Part A: Animatic Prompts & Service Setup

**Owner:** Person handling Phase 2  
**Goal:** Set up animatic generation infrastructure

---

## PR #10: Phase 2 Schemas & Prompt Generation

### Task 10.1: Create Phase 2 Schemas

**File:** `backend/app/phases/phase2_animatic/schemas.py`

- [ ] Import BaseModel from pydantic
- [ ] Import List and Dict from typing
- [ ] Create AnimaticFrameSpec model (frame_num, beat_name, shot_type, action, prompt)
- [ ] Create AnimaticGenerationRequest model (video_id, beats, style)
- [ ] Create AnimaticGenerationResult model (video_id, frame_urls, total_frames, cost_usd)

### Task 10.2: Create Prompt Generation Utility

**File:** `backend/app/phases/phase2_animatic/prompts.py`

- [ ] Import Dict from typing
- [ ] Create `generate_animatic_prompt(beat, style)` function signature
- [ ] Add docstring explaining animatic characteristics
- [ ] Define base_style constant for simple sketches
- [ ] Extract shot_type from beat
- [ ] Extract action from beat
- [ ] Call `_simplify_action(action)` helper
- [ ] Compose prompt string with action, shot, and base_style
- [ ] Return prompt string

### Task 10.3: Implement Action Simplification

- [ ] Create `_simplify_action(action)` helper function
- [ ] Add docstring
- [ ] Create action_map dictionary with all action mappings:
  - [ ] product_reveal → "object in center of frame"
  - [ ] feature_highlight → "close-up of object details"
  - [ ] usage_scenario → "person holding object"
  - [ ] brand_story → "object in environment"
  - [ ] final_impression → "object with logo"
  - [ ] establish_environment → "wide shot of location"
  - [ ] introduce_character → "person standing"
  - [ ] use_product → "person interacting with object"
  - [ ] show_benefit → "person happy gesture"
  - [ ] product_branding → "object with text"
  - [ ] dramatic_intro → "bold geometric shapes"
  - [ ] show_message → "text centered"
  - [ ] visual_emphasis → "object prominent"
  - [ ] final_message → "logo and text"
- [ ] Return mapped value with fallback to "simple scene composition"

### Task 10.4: Create Negative Prompt Function

- [ ] Create `create_negative_prompt()` function
- [ ] Return string with negative keywords (detailed, photorealistic, complex, colorful, high quality, rendered, painted, artistic, elaborate, ornate, decorative)

### Task 10.5: Create Unit Tests for Prompts

**File:** `backend/app/tests/test_phase2/test_prompts.py`

- [ ] Import pytest
- [ ] Import prompt functions from phase2_animatic.prompts
- [ ] Create `test_simplify_action()` - test known actions
- [ ] Verify product_reveal returns "object in center of frame"
- [ ] Verify introduce_character returns "person standing"
- [ ] Verify unknown_action returns fallback
- [ ] Create `test_create_negative_prompt()` - verify contains key terms
- [ ] Create `test_generate_animatic_prompt()` - test full prompt generation
- [ ] Define sample beat and style
- [ ] Verify prompt contains simplified action, shot type, and sketch style

---

## PR #11: Animatic Generation Service

### Task 11.1: Create AnimaticGenerationService Class

**File:** `backend/app/phases/phase2_animatic/service.py`

- [ ] Import replicate_client, s3_client
- [ ] Import prompt generation functions
- [ ] Import COST_SDXL_IMAGE, S3_ANIMATIC_PREFIX constants
- [ ] Import List, Dict, tempfile, requests
- [ ] Create AnimaticGenerationService class
- [ ] Add `__init__` method to initialize clients and total_cost

### Task 11.2: Implement generate_frames Method

- [ ] Create `generate_frames(video_id, spec)` method signature
- [ ] Add docstring with Args and Returns
- [ ] Extract beats and style from spec
- [ ] Initialize empty frame_urls list
- [ ] Print starting message with frame count
- [ ] Loop through beats with enumerate
- [ ] For each beat: print progress message
- [ ] Generate prompt using generate_animatic_prompt
- [ ] Create negative_prompt using create_negative_prompt
- [ ] Call `_generate_single_frame` method
- [ ] Append result to frame_urls
- [ ] Add COST_SDXL_IMAGE to total_cost
- [ ] Print completion message with count and total cost
- [ ] Return frame_urls list

### Task 11.3: Implement _generate_single_frame Method

- [ ] Create `_generate_single_frame(video_id, frame_num, prompt, negative_prompt)` private method
- [ ] Add docstring
- [ ] Wrap in try/except block
- [ ] Call replicate.run with SDXL model
- [ ] Set input parameters:
  - [ ] prompt
  - [ ] negative_prompt
  - [ ] width=512
  - [ ] height=512
  - [ ] num_inference_steps=20
  - [ ] guidance_scale=7.0
  - [ ] num_outputs=1
- [ ] Extract image_url from output[0]
- [ ] Download image data using requests.get
- [ ] Save to temporary file with .png suffix
- [ ] Construct s3_key with video_id, S3_ANIMATIC_PREFIX, and frame_num
- [ ] Upload to S3 using s3.upload_file
- [ ] Print success message with frame_num and s3_url
- [ ] Return s3_url
- [ ] In except block, raise Exception with frame_num and error

---

## ✅ PR #10 & #11 Checklist

Before merging:
- [ ] All Phase 2 schemas defined
- [ ] Prompt generation utility working
- [ ] Unit tests for prompts passing
- [ ] AnimaticGenerationService implemented
- [ ] Can instantiate service without errors

**Test Commands:**
```python
# In Python shell
from app.phases.phase2_animatic.prompts import generate_animatic_prompt

beat = {"shot_type": "close_up", "action": "product_reveal"}
style = {"aesthetic": "luxury"}
print(generate_animatic_prompt(beat, style))
```

**Next:** Move to `tasks-phase-2b.md`