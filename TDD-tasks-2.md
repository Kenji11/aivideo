# TDD Implementation Tasks - Part 2: Phase 1 Testing & Phase 2

**Goal:** Test Phase 1 thoroughly and implement Phase 2 storyboard generation

---

## PR #4: Phase 1 Unit Tests

### Task 4.1: Create Test Fixtures

**File:** `backend/app/tests/fixtures/test_prompts.py`

- [ ] Create file `test_prompts.py`
- [ ] Define `TEST_PROMPTS` list with 5 test cases:
  - [ ] TP1: "15s Nike sneakers energetic urban"
  - [ ] TP2: "30s luxury watch elegant sophisticated"
  - [ ] TP3: "20s iPhone minimalist clean modern"
  - [ ] TP4: "Create an ad for family car with emotional story"
  - [ ] TP5: "Smart thermostat features demo 25 seconds"
- [ ] Each test case should have:
  - [ ] id, prompt, expected_archetype, expected_duration, expected_beats (range)

### Task 4.2: Create Validation Tests

**File:** `backend/app/tests/test_phase1/test_validation.py`

- [ ] Import pytest
- [ ] Import validate_spec, build_full_spec from phase1_planning
- [ ] Import BEAT_LIBRARY from common
- [ ] Create `test_validate_spec_correct_sum()`:
  - [ ] Create valid spec with 3 beats (5+5+5=15)
  - [ ] Call validate_spec
  - [ ] Assert no exception raised
- [ ] Create `test_validate_spec_incorrect_sum()`:
  - [ ] Create spec with beats summing to 20 but duration=15
  - [ ] Assert ValueError raised with "sum" in message
- [ ] Create `test_validate_spec_invalid_duration()`:
  - [ ] Create spec with beat duration of 7 seconds
  - [ ] Assert ValueError raised with "5, 10, or 15" in message
- [ ] Create `test_validate_spec_unknown_beat_id()`:
  - [ ] Create spec with beat_id="fake_beat"
  - [ ] Assert ValueError raised with "Unknown beat_id" in message
- [ ] Create `test_validate_spec_no_beats()`:
  - [ ] Create spec with empty beats list
  - [ ] Assert ValueError raised with "at least one beat" in message

### Task 4.3: Create Beat Library Tests

**File:** `backend/app/tests/test_common/test_beat_library.py`

- [ ] Import BEAT_LIBRARY, OPENING_BEATS, MIDDLE_PRODUCT_BEATS, MIDDLE_DYNAMIC_BEATS, CLOSING_BEATS
- [ ] Create `test_beat_library_size()`:
  - [ ] Assert len(BEAT_LIBRARY) == 15
- [ ] Create `test_all_beats_have_required_fields()`:
  - [ ] Loop through BEAT_LIBRARY.values()
  - [ ] Assert each has: beat_id, duration, shot_type, action, prompt_template, camera_movement, typical_position, compatible_products, energy_level
- [ ] Create `test_all_beat_durations_valid()`:
  - [ ] Loop through BEAT_LIBRARY.values()
  - [ ] Assert duration in [5, 10, 15]
- [ ] Create `test_opening_beats_count()`:
  - [ ] Assert len(OPENING_BEATS) == 5
- [ ] Create `test_middle_product_beats_count()`:
  - [ ] Assert len(MIDDLE_PRODUCT_BEATS) == 5
- [ ] Create `test_middle_dynamic_beats_count()`:
  - [ ] Assert len(MIDDLE_DYNAMIC_BEATS) == 3
- [ ] Create `test_closing_beats_count()`:
  - [ ] Assert len(CLOSING_BEATS) == 2

### Task 4.4: Create Integration Test (with LLM)

**File:** `backend/app/tests/test_phase1/test_integration.py`

- [ ] Import pytest, os
- [ ] Import plan_video_intelligent from phase1_planning.task
- [ ] Import TEST_PROMPTS from fixtures
- [ ] Create `@pytest.mark.integration` decorator
- [ ] Create `@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"))` decorator
- [ ] Create `test_plan_video_with_llm()`:
  - [ ] Use TP1 from TEST_PROMPTS
  - [ ] Call plan_video_intelligent with test video_id, prompt, creativity=0.5
  - [ ] Assert result['status'] == 'success'
  - [ ] Assert 'spec' in result['output_data']
  - [ ] Extract spec
  - [ ] Assert spec['duration'] == 15
  - [ ] Assert len(spec['beats']) >= 3
  - [ ] Assert spec['template'] in TEMPLATE_ARCHETYPES
  - [ ] Assert sum of beat durations == 15
- [ ] Create `test_plan_video_strict_mode()`:
  - [ ] Use TP2 with creativity=0.0
  - [ ] Verify beat sequence closely matches archetype template
- [ ] Create `test_plan_video_creative_mode()`:
  - [ ] Use TP2 with creativity=1.0
  - [ ] Verify beat sequence may differ from template

---

## PR #5: Phase 2 Structure & Implementation

### Task 5.1: Create Phase 2 Directory Structure

- [ ] Create directory `backend/app/phases/phase2_storyboard/`
- [ ] Create `__init__.py` in phase2_storyboard
- [ ] Create `task.py` in phase2_storyboard
- [ ] Create `image_generation.py` in phase2_storyboard

### Task 5.2: Implement Image Generation Helper

**File:** `backend/app/phases/phase2_storyboard/image_generation.py`

- [ ] Import replicate_client, s3_client
- [ ] Import COST_SDXL_IMAGE from constants
- [ ] Import tempfile, requests, logging
- [ ] Create logger instance
- [ ] Create `generate_beat_image(video_id, beat, style, product) -> tuple[str, str]` function
- [ ] Add docstring explaining function returns (image_url, prompt_used)
- [ ] Extract base_prompt from beat['prompt_template']
- [ ] Extract colors from style['color_palette'], join with commas
- [ ] Extract lighting from style['lighting']
- [ ] Compose full_prompt with:
  - [ ] base_prompt
  - [ ] color palette
  - [ ] lighting
  - [ ] "cinematic composition"
  - [ ] "high quality professional photography"
  - [ ] "1280x720 aspect ratio"
  - [ ] shot_type framing
- [ ] Create negative_prompt with:
  - [ ] "blurry, low quality, distorted, deformed, ugly, amateur"
  - [ ] "watermark, text, signature, letters, words"
  - [ ] "multiple subjects, cluttered, busy, messy, chaotic"
- [ ] Log prompt (first 100 chars)

### Task 5.3: Implement SDXL Generation Call

**File:** `backend/app/phases/phase2_storyboard/image_generation.py` (continued)

- [ ] Call replicate_client.run with:
  - [ ] model="stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
  - [ ] input.prompt = full_prompt
  - [ ] input.negative_prompt = negative_prompt
  - [ ] input.width = 1280
  - [ ] input.height = 720
  - [ ] input.num_inference_steps = 30
  - [ ] input.guidance_scale = 7.5
  - [ ] input.scheduler = "K_EULER"
- [ ] Extract image_url from output[0]
- [ ] Download image with requests.get
- [ ] Save to temp file with .png suffix
- [ ] Construct s3_key: `videos/{video_id}/storyboard/{beat['beat_id']}.png`
- [ ] Upload to S3 with s3_client.upload_file
- [ ] Log upload success
- [ ] Return (s3_url, full_prompt)

### Task 5.4: Implement Phase 2 Task

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Import celery_app
- [ ] Import PhaseOutput from common.schemas
- [ ] Import generate_beat_image from .image_generation
- [ ] Import COST_SDXL_IMAGE from constants
- [ ] Import time, logging
- [ ] Create logger instance
- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_storyboard(self, video_id, spec)` function
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Extract beats, style, product from spec
- [ ] Log start message with video_id and beat count

### Task 5.5: Implement Storyboard Generation Loop

**File:** `backend/app/phases/phase2_storyboard/task.py` (continued)

- [ ] Wrap in try/except block
- [ ] Initialize empty storyboard_images list
- [ ] Initialize total_cost = 0.0
- [ ] Loop through beats with enumerate:
  - [ ] Log progress (i+1/total, beat_id)
  - [ ] Call generate_beat_image(video_id, beat, style, product)
  - [ ] Append result to storyboard_images with:
    - [ ] beat_id, beat_name, start, duration
    - [ ] image_url, shot_type, prompt_used
  - [ ] Add COST_SDXL_IMAGE to total_cost
- [ ] Log completion with count and cost

### Task 5.6: Implement Success/Failure Paths

**File:** `backend/app/phases/phase2_storyboard/task.py` (continued)

- [ ] Create PhaseOutput with:
  - [ ] video_id
  - [ ] phase="phase2_storyboard"
  - [ ] status="success"
  - [ ] output_data={"storyboard_images": storyboard_images}
  - [ ] cost_usd=total_cost
  - [ ] duration_seconds
  - [ ] error_message=None
- [ ] Return output.dict()
- [ ] In except block:
  - [ ] Log error
  - [ ] Create PhaseOutput with status="failed"
  - [ ] Set error_message
  - [ ] cost_usd=0.0
  - [ ] Return output.dict()

---

## PR #6: Phase 2 Tests

### Task 6.1: Create Phase 2 Unit Tests

**File:** `backend/app/tests/test_phase2/test_storyboard.py`

- [ ] Import pytest, os
- [ ] Import generate_storyboard from phase2_storyboard.task
- [ ] Create mock spec with 3 beats
- [ ] Create `test_storyboard_structure()`:
  - [ ] Call generate_storyboard with mock spec
  - [ ] Assert 'storyboard_images' in output_data
  - [ ] Assert len(storyboard_images) == 3
  - [ ] Verify each has required fields
- [ ] Create `test_storyboard_cost_calculation()`:
  - [ ] Call with 3 beats
  - [ ] Assert cost_usd == 3 * COST_SDXL_IMAGE
- [ ] Create `@pytest.mark.integration` test with real SDXL call (if API key present):
  - [ ] Generate 1 storyboard image
  - [ ] Verify S3 URL returned
  - [ ] Verify image is 1280x720

### Task 6.2: Create Integration Test (Phase 1 + 2)

**File:** `backend/app/tests/test_integration/test_phase1_and_2.py`

- [ ] Import pytest, os
- [ ] Import plan_video_intelligent, generate_storyboard
- [ ] Create `@pytest.mark.integration` decorator
- [ ] Create `@pytest.mark.skipif` for API keys
- [ ] Create `test_phase1_to_phase2()`:
  - [ ] Call Phase 1 with "15s Nike sneakers energetic"
  - [ ] Assert Phase 1 success
  - [ ] Extract spec
  - [ ] Call Phase 2 with spec
  - [ ] Assert Phase 2 success
  - [ ] Assert storyboard_images count == beat count
  - [ ] Assert all images have S3 URLs
  - [ ] Assert total cost = Phase1 cost + Phase2 cost

---

## ✅ PR #4, #5, #6 Checklist

Before merging:
- [ ] All Phase 1 unit tests pass
- [ ] All Phase 2 unit tests pass
- [ ] Integration test (Phase 1+2) passes with API keys
- [ ] Storyboard images are 1280x720
- [ ] S3 uploads work correctly
- [ ] Cost calculation is accurate

**Next:** Move to `TDD-tasks-3.md` for Phase 3 implementation