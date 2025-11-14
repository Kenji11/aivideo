# Phase 1 Tasks - Part B: Implementation

**Owner:** Person handling Phase 1  
**Goal:** Implement prompt validation service and task

---

## PR #7: Validation Service

### Task 7.1: Implement PromptValidationService Class

**File:** `backend/app/phases/phase1_validate/service.py`

- [ ] Import necessary dependencies (openai_client, templates, schemas, exceptions)
- [ ] Create PromptValidationService class
- [ ] Add `__init__` method to initialize OpenAI client

### Task 7.2: Implement validate_and_extract Method

- [ ] Create `validate_and_extract(prompt, assets)` method signature
- [ ] Add docstring explaining method purpose
- [ ] Call `_extract_intent(prompt)` to get extracted data
- [ ] Extract template_name with fallback to 'product_showcase'
- [ ] Validate template choice
- [ ] Load template using template loader
- [ ] Call `_merge_with_template(extracted, template)`
- [ ] Add uploaded assets to spec
- [ ] Call `_validate_spec(full_spec)`
- [ ] Return full spec dictionary

### Task 7.3: Implement _extract_intent Method

- [ ] Create `_extract_intent(prompt)` private method
- [ ] Define system prompt for GPT-4 with template descriptions
- [ ] Add JSON structure example in system prompt
- [ ] Call OpenAI API with GPT-4 Turbo
- [ ] Set response_format to json_object
- [ ] Set temperature to 0.3 for consistency
- [ ] Parse JSON response
- [ ] Add try/except for API errors
- [ ] Raise ValidationException on failure

### Task 7.4: Implement _merge_with_template Method

- [ ] Create `_merge_with_template(extracted, template)` private method
- [ ] Copy template as base spec
- [ ] Update template field from extracted data
- [ ] Merge style from extracted if present
- [ ] Merge product from extracted if present
- [ ] Merge audio from extracted if present
- [ ] Enrich beat prompts with extracted data (format prompt_template strings)
- [ ] Return merged spec

### Task 7.5: Implement _validate_spec Method

- [ ] Create `_validate_spec(spec)` private method
- [ ] Define required_fields list
- [ ] Check all required fields are present
- [ ] Raise ValidationException if any missing
- [ ] Validate beats list is not empty
- [ ] Calculate total duration from beats
- [ ] Validate total duration matches spec duration (with 1s tolerance)
- [ ] Raise ValidationException if duration mismatch

---

## PR #8: Phase 1 Task & Tests

### Task 8.1: Implement Phase 1 Celery Task

**File:** `backend/app/phases/phase1_validate/task.py`

- [ ] Import celery_app from orchestrator
- [ ] Import PhaseOutput from common.schemas
- [ ] Import PromptValidationService
- [ ] Import COST_GPT4_TURBO constant
- [ ] Import time module

### Task 8.2: Implement validate_prompt Task Function

- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `validate_prompt(self, video_id, prompt, assets)` signature
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Wrap logic in try/except block

### Task 8.3: Implement Success Path

- [ ] Initialize PromptValidationService
- [ ] Call service.validate_and_extract(prompt, assets)
- [ ] Create PhaseOutput with success status
- [ ] Set video_id, phase="phase1_validate"
- [ ] Set output_data={"spec": spec}
- [ ] Set cost_usd=COST_GPT4_TURBO
- [ ] Calculate duration_seconds
- [ ] Return output.dict()

### Task 8.4: Implement Error Path

- [ ] In except block, create PhaseOutput with failed status
- [ ] Set empty output_data
- [ ] Set cost_usd=0.0
- [ ] Calculate duration_seconds
- [ ] Set error_message=str(e)
- [ ] Return output.dict()

### Task 8.5: Create Unit Tests

**File:** `backend/app/tests/test_phase1/test_validation.py`

- [ ] Import pytest
- [ ] Import PromptValidationService, templates functions, ValidationException
- [ ] Create `test_list_templates()` - verify 3 templates exist
- [ ] Create `test_load_template()` - verify product_showcase loads correctly
- [ ] Create `test_load_invalid_template()` - verify raises ValueError
- [ ] Create `test_validate_spec_missing_fields()` - verify catches missing fields
- [ ] Add `@pytest.mark.skipif` for tests requiring API keys
- [ ] Create `test_validate_prompt()` - test with real API (if key present)

### Task 8.6: Create Manual Test Script

**File:** `backend/test_phase1.py`

- [ ] Add shebang and docstring
- [ ] Import sys and add app to path
- [ ] Import PromptValidationService and json
- [ ] Create test_validation() function
- [ ] Define 3 test prompts (luxury watch, sports shoes, product launch)
- [ ] Print header
- [ ] Loop through test prompts
- [ ] For each: call validate_and_extract, print results
- [ ] Save spec to `test_spec_{i}.json` file
- [ ] Add exception handling with error printing
- [ ] Add `if __name__ == "__main__"` block

---

## PR #9: Orchestrator Integration

### Task 9.1: Implement Celery App Configuration

**File:** `backend/app/orchestrator/celery_app.py`

- [ ] Import Celery from celery
- [ ] Import get_settings
- [ ] Get settings instance
- [ ] Create Celery app with name 'video_gen'
- [ ] Configure broker as settings.redis_url
- [ ] Configure result_backend as settings.redis_url
- [ ] Set task_serializer='json'
- [ ] Set result_serializer='json'
- [ ] Set accept_content=['json']
- [ ] Set timezone='UTC'
- [ ] Set enable_utc=True

### Task 9.2: Implement Pipeline Orchestrator (Phase 1 Only)

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Import celery_app
- [ ] Import validate_prompt task
- [ ] Import update_progress, update_cost functions
- [ ] Import time module
- [ ] Create `@celery_app.task` decorator

### Task 9.3: Implement run_pipeline Task

- [ ] Define `run_pipeline(video_id, prompt, assets)` signature
- [ ] Initialize start_time and total_cost
- [ ] Wrap in try/except block
- [ ] Call `update_progress(video_id, "validating", 10)`
- [ ] Call `validate_prompt.delay(video_id, prompt, assets).get(timeout=60)`
- [ ] Check if result1['status'] != "success", raise exception
- [ ] Add result1['cost_usd'] to total_cost
- [ ] Call `update_cost(video_id, "phase1", result1['cost_usd'])`
- [ ] Add TODO comment for Phase 2-6
- [ ] Call `update_progress` with complete status
- [ ] Return result dictionary with video_id, status, spec, cost
- [ ] In except block, call update_progress with failed status and re-raise

### Task 9.4: Implement Progress Helper

**File:** `backend/app/orchestrator/progress.py`

- [ ] Import SessionLocal, VideoGeneration, VideoStatus
- [ ] Import datetime and Optional

### Task 9.5: Implement update_progress Function

- [ ] Define `update_progress(video_id, status, progress, **kwargs)` signature
- [ ] Create database session with SessionLocal()
- [ ] Wrap in try/finally to close session
- [ ] Query for video by id
- [ ] If not found, create new VideoGeneration record
- [ ] If found, update status and progress
- [ ] Update current_phase from kwargs
- [ ] Update spec, error, total_cost, generation_time from kwargs
- [ ] Set completed_at if status is 'complete'
- [ ] Commit changes

### Task 9.6: Implement update_cost Function

- [ ] Define `update_cost(video_id, phase, cost)` signature
- [ ] Create database session
- [ ] Query for video by id
- [ ] If found, initialize cost_breakdown if null
- [ ] Set cost_breakdown[phase] = cost
- [ ] Sum all costs and update cost_usd
- [ ] Commit changes
- [ ] Close session in finally block

---

## ✅ PR #7, #8, #9 Checklist

Before merging:
- [ ] PromptValidationService implemented and working
- [ ] Phase 1 task implemented
- [ ] Unit tests pass (or skip if no API keys)
- [ ] Manual test script works
- [ ] Celery app configured
- [ ] Pipeline orchestrator calls Phase 1
- [ ] Progress tracking updates database

**Test Commands:**
```bash
# Start services
docker-compose up --build

# Run manual test
docker-compose exec api python test_phase1.py

# Check for generated files
ls test_spec_*.json
```

**Phase 1 is complete!**