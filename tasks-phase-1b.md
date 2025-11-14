# Phase 1 Tasks - Part B: Implementation

**Owner:** Person handling Phase 1  
**Goal:** Implement prompt validation service and task

---

## PR #7: Validation Service

### Task 7.1: Implement PromptValidationService Class

**File:** `backend/app/phases/phase1_validate/service.py`

- [x] Import necessary dependencies (openai_client, templates, schemas, exceptions)
- [x] Create PromptValidationService class
- [x] Add `__init__` method to initialize OpenAI client

### Task 7.2: Implement validate_and_extract Method

- [x] Create `validate_and_extract(prompt, assets)` method signature
- [x] Add docstring explaining method purpose
- [x] Call `_extract_intent(prompt)` to get extracted data
- [x] Extract template_name with fallback to 'product_showcase'
- [x] Validate template choice
- [x] Load template using template loader
- [x] Call `_merge_with_template(extracted, template)`
- [x] Add uploaded assets to spec
- [x] Call `_validate_spec(full_spec)`
- [x] Return full spec dictionary

### Task 7.3: Implement _extract_intent Method

- [x] Create `_extract_intent(prompt)` private method
- [x] Define system prompt for GPT-4 with template descriptions
- [x] Add JSON structure example in system prompt
- [x] Call OpenAI API with GPT-4 Turbo
- [x] Set response_format to json_object
- [x] Set temperature to 0.3 for consistency
- [x] Parse JSON response
- [x] Add try/except for API errors
- [x] Raise ValidationException on failure

### Task 7.4: Implement _merge_with_template Method

- [x] Create `_merge_with_template(extracted, template)` private method
- [x] Copy template as base spec
- [x] Update template field from extracted data
- [x] Merge style from extracted if present
- [x] Merge product from extracted if present
- [x] Merge audio from extracted if present
- [x] Enrich beat prompts with extracted data (format prompt_template strings)
- [x] Return merged spec

### Task 7.5: Implement _validate_spec Method

- [x] Create `_validate_spec(spec)` private method
- [x] Define required_fields list
- [x] Check all required fields are present
- [x] Raise ValidationException if any missing
- [x] Validate beats list is not empty
- [x] Calculate total duration from beats
- [x] Validate total duration matches spec duration (with 1s tolerance)
- [x] Raise ValidationException if duration mismatch

---

## PR #8: Phase 1 Task & Tests

### Task 8.1: Implement Phase 1 Celery Task

**File:** `backend/app/phases/phase1_validate/task.py`

- [x] Import celery_app from orchestrator
- [x] Import PhaseOutput from common.schemas
- [x] Import PromptValidationService
- [x] Import COST_GPT4_TURBO constant
- [x] Import time module

### Task 8.2: Implement validate_prompt Task Function

- [x] Create `@celery_app.task(bind=True)` decorator
- [x] Define `validate_prompt(self, video_id, prompt, assets)` signature
- [x] Add docstring with Args and Returns
- [x] Record start_time
- [x] Wrap logic in try/except block

### Task 8.3: Implement Success Path

- [x] Initialize PromptValidationService
- [x] Call service.validate_and_extract(prompt, assets)
- [x] Create PhaseOutput with success status
- [x] Set video_id, phase="phase1_validate"
- [x] Set output_data={"spec": spec}
- [x] Set cost_usd=COST_GPT4_TURBO
- [x] Calculate duration_seconds
- [x] Return output.dict()

### Task 8.4: Implement Error Path

- [x] In except block, create PhaseOutput with failed status
- [x] Set empty output_data
- [x] Set cost_usd=0.0
- [x] Calculate duration_seconds
- [x] Set error_message=str(e)
- [x] Return output.dict()

### Task 8.5: Create Unit Tests

**File:** `backend/app/tests/test_phase1/test_validation.py`

- [x] Import pytest
- [x] Import PromptValidationService, templates functions, ValidationException
- [x] Create `test_list_templates()` - verify 3 templates exist
- [x] Create `test_load_template()` - verify product_showcase loads correctly
- [x] Create `test_load_invalid_template()` - verify raises ValueError
- [x] Create `test_validate_spec_missing_fields()` - verify catches missing fields
- [x] Add `@pytest.mark.skipif` for tests requiring API keys
- [x] Create `test_validate_prompt()` - test with real API (if key present)

### Task 8.6: Create Manual Test Script

**File:** `backend/test_phase1.py`

- [x] Add shebang and docstring
- [x] Import sys and add app to path
- [x] Import PromptValidationService and json
- [x] Create test_validation() function
- [x] Define 3 test prompts (luxury watch, sports shoes, product launch)
- [x] Print header
- [x] Loop through test prompts
- [x] For each: call validate_and_extract, print results
- [x] Save spec to `test_spec_{i}.json` file
- [x] Add exception handling with error printing
- [x] Add `if __name__ == "__main__"` block

---

## PR #9: Orchestrator Integration

### Task 9.1: Implement Celery App Configuration

**File:** `backend/app/orchestrator/celery_app.py`

- [x] Import Celery from celery
- [x] Import get_settings
- [x] Get settings instance
- [x] Create Celery app with name 'video_gen'
- [x] Configure broker as settings.redis_url
- [x] Configure result_backend as settings.redis_url
- [x] Set task_serializer='json'
- [x] Set result_serializer='json'
- [x] Set accept_content=['json']
- [x] Set timezone='UTC'
- [x] Set enable_utc=True

### Task 9.2: Implement Pipeline Orchestrator (Phase 1 Only)

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Import celery_app
- [x] Import validate_prompt task
- [x] Import update_progress, update_cost functions
- [x] Import time module
- [x] Create `@celery_app.task` decorator

### Task 9.3: Implement run_pipeline Task

- [x] Define `run_pipeline(video_id, prompt, assets)` signature
- [x] Initialize start_time and total_cost
- [x] Wrap in try/except block
- [x] Call `update_progress(video_id, "validating", 10)`
- [x] Call `validate_prompt.delay(video_id, prompt, assets).get(timeout=60)`
- [x] Check if result1['status'] != "success", raise exception
- [x] Add result1['cost_usd'] to total_cost
- [x] Call `update_cost(video_id, "phase1", result1['cost_usd'])`
- [x] Add TODO comment for Phase 2-6
- [x] Call `update_progress` with complete status
- [x] Return result dictionary with video_id, status, spec, cost
- [x] In except block, call update_progress with failed status and re-raise

### Task 9.4: Implement Progress Helper

**File:** `backend/app/orchestrator/progress.py`

- [x] Import SessionLocal, VideoGeneration, VideoStatus
- [x] Import datetime and Optional

### Task 9.5: Implement update_progress Function

- [x] Define `update_progress(video_id, status, progress, **kwargs)` signature
- [x] Create database session with SessionLocal()
- [x] Wrap in try/finally to close session
- [x] Query for video by id
- [x] If not found, create new VideoGeneration record
- [x] If found, update status and progress
- [x] Update current_phase from kwargs
- [x] Update spec, error, total_cost, generation_time from kwargs
- [x] Set completed_at if status is 'complete'
- [x] Commit changes

### Task 9.6: Implement update_cost Function

- [x] Define `update_cost(video_id, phase, cost)` signature
- [x] Create database session
- [x] Query for video by id
- [x] If found, initialize cost_breakdown if null
- [x] Set cost_breakdown[phase] = cost
- [x] Sum all costs and update cost_usd
- [x] Commit changes
- [x] Close session in finally block

---

## ✅ PR #7, #8, #9 Checklist

Before merging:
- [x] PromptValidationService implemented and working
- [x] Phase 1 task implemented
- [x] Unit tests pass (or skip if no API keys)
- [x] Manual test script works
- [x] Celery app configured
- [x] Pipeline orchestrator calls Phase 1
- [x] Progress tracking updates database

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