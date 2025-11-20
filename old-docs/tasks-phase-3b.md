# Phase 3 Tasks - Part B: Implementation

**Owner:** Person handling Phase 3  
**Goal:** Implement reference generation task and integration

---

## PR #13: Phase 3 Task

### Task 13.1: Implement Phase 3 Celery Task

**File:** `backend/app/phases/phase3_references/task.py`

- [x] Import celery_app from orchestrator
- [x] Import PhaseOutput from common.schemas
- [x] Import ReferenceAssetService
- [x] Import COST_SDXL_IMAGE constant
- [x] Import time module

### Task 13.2: Implement generate_references Task Function

- [x] Create `@celery_app.task(bind=True)` decorator
- [x] Define `generate_references(self, video_id, spec)` signature
- [x] Add docstring with Args and Returns
- [x] Record start_time
- [x] Wrap logic in try/except block

### Task 13.3: Implement Success Path

- [x] Initialize ReferenceAssetService
- [x] Call service.generate_all_references(video_id, spec)
- [x] Create PhaseOutput with success status
- [x] Set video_id, phase="phase3_references"
- [x] Set output_data with reference URLs
- [x] Set cost_usd from service.total_cost
- [x] Calculate duration_seconds
- [x] Return output.dict()

### Task 13.4: Implement Error Path

- [x] In except block, create PhaseOutput with failed status
- [x] Set empty output_data
- [x] Set cost_usd=0.0
- [x] Calculate duration_seconds
- [x] Set error_message=str(e)
- [x] Return output.dict()

### Task 13.5: Create Unit Tests

**File:** `backend/app/tests/test_phase3/test_references.py`

- [x] Import pytest
- [x] Import ReferenceAssetService, AssetHandler
- [x] Create `test_asset_handler_validation()` - test image validation
- [x] Create `test_asset_handler_download()` - test asset download
- [x] Add `@pytest.mark.skipif` for tests requiring API keys
- [x] Create `test_generate_style_guide()` - test with real API (if key present)
- [x] Create `test_generate_product_reference()` - test product ref generation

### Task 13.6: Create Manual Test Script

**File:** `backend/test_phase3.py`

- [x] Add shebang and docstring
- [x] Import sys and add app to path
- [x] Import ReferenceAssetService and json
- [x] Create test_references() function
- [x] Define test spec with style information
- [x] Print header
- [x] Call generate_all_references
- [x] Print results (style guide URL, product ref URL)
- [x] Save output to `test_references_output.json`
- [x] Add exception handling with error printing
- [x] Add `if __name__ == "__main__"` block

---

## PR #14: Orchestrator Integration

### Task 14.1: Update Pipeline Orchestrator

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Import generate_references task from phase3
- [x] After Phase 1 success, call `update_progress(video_id, "generating_references", 30)`
- [x] Call `generate_references.delay(video_id, spec).get(timeout=300)`
- [x] Check if result3['status'] != "success", raise exception
- [x] Add result3['cost_usd'] to total_cost
- [x] Call `update_cost(video_id, "phase3", result3['cost_usd'])`
- [x] Extract reference_urls from result3['output_data']
- [x] Pass reference_urls to Phase 4 (ready when Phase 4 is implemented)

---

## ✅ PR #13, #14 Checklist

Before merging:
- [x] Phase 3 task implemented
- [x] Unit tests pass (or skip if no API keys)
- [x] Manual test script works
- [x] Pipeline orchestrator calls Phase 3
- [x] Reference URLs passed to Phase 4 (ready when Phase 4 is implemented)
- [x] Cost tracking updates database

**Test Commands:**
```bash
# Start services
docker-compose up --build

# Run manual test
docker-compose exec api python test_phase3.py

# Check for generated files
ls test_references_output.json
```

**Phase 3 is complete!**

