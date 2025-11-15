# Phase 3 Tasks - Part B: Implementation

**Owner:** Person handling Phase 3  
**Goal:** Implement reference generation task and integration

---

## PR #13: Phase 3 Task

### Task 13.1: Implement Phase 3 Celery Task

**File:** `backend/app/phases/phase3_references/task.py`

- [ ] Import celery_app from orchestrator
- [ ] Import PhaseOutput from common.schemas
- [ ] Import ReferenceAssetService
- [ ] Import COST_SDXL_IMAGE constant
- [ ] Import time module

### Task 13.2: Implement generate_references Task Function

- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_references(self, video_id, spec)` signature
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Wrap logic in try/except block

### Task 13.3: Implement Success Path

- [ ] Initialize ReferenceAssetService
- [ ] Call service.generate_all_references(video_id, spec)
- [ ] Create PhaseOutput with success status
- [ ] Set video_id, phase="phase3_references"
- [ ] Set output_data with reference URLs
- [ ] Set cost_usd from service.total_cost
- [ ] Calculate duration_seconds
- [ ] Return output.dict()

### Task 13.4: Implement Error Path

- [ ] In except block, create PhaseOutput with failed status
- [ ] Set empty output_data
- [ ] Set cost_usd=0.0
- [ ] Calculate duration_seconds
- [ ] Set error_message=str(e)
- [ ] Return output.dict()

### Task 13.5: Create Unit Tests

**File:** `backend/app/tests/test_phase3/test_references.py`

- [ ] Import pytest
- [ ] Import ReferenceAssetService, AssetHandler
- [ ] Create `test_asset_handler_validation()` - test image validation
- [ ] Create `test_asset_handler_download()` - test asset download
- [ ] Add `@pytest.mark.skipif` for tests requiring API keys
- [ ] Create `test_generate_style_guide()` - test with real API (if key present)
- [ ] Create `test_generate_product_reference()` - test product ref generation

### Task 13.6: Create Manual Test Script

**File:** `backend/test_phase3.py`

- [ ] Add shebang and docstring
- [ ] Import sys and add app to path
- [ ] Import ReferenceAssetService and json
- [ ] Create test_references() function
- [ ] Define test spec with style information
- [ ] Print header
- [ ] Call generate_all_references
- [ ] Print results (style guide URL, product ref URL)
- [ ] Save output to `test_references_output.json`
- [ ] Add exception handling with error printing
- [ ] Add `if __name__ == "__main__"` block

---

## PR #14: Orchestrator Integration

### Task 14.1: Update Pipeline Orchestrator

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Import generate_references task from phase3
- [ ] After Phase 1 success, call `update_progress(video_id, "generating_references", 30)`
- [ ] Call `generate_references.delay(video_id, spec).get(timeout=300)`
- [ ] Check if result3['status'] != "success", raise exception
- [ ] Add result3['cost_usd'] to total_cost
- [ ] Call `update_cost(video_id, "phase3", result3['cost_usd'])`
- [ ] Extract reference_urls from result3['output_data']
- [ ] Pass reference_urls to Phase 4

---

## ✅ PR #13, #14 Checklist

Before merging:
- [ ] Phase 3 task implemented
- [ ] Unit tests pass (or skip if no API keys)
- [ ] Manual test script works
- [ ] Pipeline orchestrator calls Phase 3
- [ ] Reference URLs passed to Phase 4
- [ ] Cost tracking updates database

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

