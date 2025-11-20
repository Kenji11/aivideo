# Phase 2 Tasks - Part B: Task Implementation & Integration

**Owner:** Person handling Phase 2  
**Goal:** Implement Phase 2 Celery task and integrate with pipeline

---

## PR #12: Phase 2 Task Implementation

### Task 12.1: Implement Phase 2 Celery Task

**File:** `backend/app/phases/phase2_animatic/task.py`

- [x] Import celery_app from orchestrator
- [x] Import PhaseOutput from common.schemas
- [x] Import AnimaticGenerationService
- [x] Import time module
- [x] Import Dict from typing

### Task 12.2: Implement generate_animatic Task Function

- [x] Create `@celery_app.task(bind=True)` decorator
- [x] Define `generate_animatic(self, video_id, spec)` signature
- [x] Add docstring with Args and Returns
- [x] Record start_time
- [x] Wrap logic in try/except block

### Task 12.3: Implement Success Path

- [x] Initialize AnimaticGenerationService
- [x] Call service.generate_frames(video_id, spec)
- [x] Create PhaseOutput with success status
- [x] Set video_id, phase="phase2_animatic"
- [x] Set output_data={"animatic_urls": frame_urls}
- [x] Set cost_usd=service.total_cost
- [x] Calculate duration_seconds
- [x] Set error_message=None
- [x] Return output.dict()

### Task 12.4: Implement Error Path

- [x] In except block, create PhaseOutput with failed status
- [x] Set empty output_data
- [x] Set cost_usd=0.0
- [x] Calculate duration_seconds
- [x] Set error_message=str(e)
- [x] Return output.dict()

### Task 12.5: Create Manual Test Script

**File:** `backend/test_phase2.py`

- [x] Add shebang and docstring
- [x] Import sys and add app to path
- [x] Import AnimaticGenerationService, generate_animatic_prompt, json

### Task 12.6: Implement test_prompt_generation Function

- [x] Create `test_prompt_generation()` function
- [x] Print test header
- [x] Define test_beats list with 3 different beat types
- [x] Define style dictionary
- [x] Loop through test_beats
- [x] Generate prompt for each beat
- [x] Print beat name, action, and generated prompt

### Task 12.7: Implement test_full_generation Function

- [x] Create `test_full_generation()` function
- [x] Print test header
- [x] Try to load test_spec_1.json (from Phase 1)
- [x] If FileNotFoundError, print warning and return
- [x] Print spec template and beat count
- [x] Initialize AnimaticGenerationService
- [x] Define test_video_id
- [x] Call service.generate_frames(test_video_id, spec)
- [x] Print success message with frame count and cost
- [x] Print all frame URLs
- [x] Save result to test_animatic_result.json
- [x] Add exception handling with error printing

### Task 12.8: Add Main Block

- [x] Add `if __name__ == "__main__"` block
- [x] Call test_prompt_generation()
- [x] Add commented call to test_full_generation()

---

## PR #13: Update Orchestrator for Phase 2

### Task 13.1: Update Pipeline Imports

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Add import for generate_animatic task from phase2_animatic.task

### Task 13.2: Integrate Phase 2 into Pipeline

- [x] After Phase 1 success, add `update_progress(video_id, "generating_animatic", 25)`
- [x] Call `generate_animatic.delay(video_id, result1['output_data']['spec']).get(timeout=300)`
- [x] Store result as result2
- [x] Check if result2['status'] != "success", raise exception with error message
- [x] Add result2['cost_usd'] to total_cost
- [x] Call `update_cost(video_id, "phase2", result2['cost_usd'])`
- [x] Update TODO comment to say "Phase 3-6"
- [x] Update final update_progress call to include animatic_urls parameter
- [x] Update return dictionary to include animatic_urls and updated cost/time

### Task 13.3: Update Return Statement

- [x] Add "animatic_urls": result2['output_data']['animatic_urls'] to return dict
- [x] Update "cost_usd" to use updated total_cost
- [x] Update "generation_time" to use calculated time

---

## PR #14: Integration Tests

### Task 14.1: Create Integration Test File

**File:** `backend/app/tests/test_integration/test_phase1_and_2.py`

- [x] Import pytest, uuid, os
- [x] Import validate_prompt and generate_animatic tasks

### Task 14.2: Implement Integration Test

- [x] Create `test_phase1_and_phase2_integration()` function
- [x] Add `@pytest.mark.integration` decorator
- [x] Add `@pytest.mark.skipif` for API keys check
- [x] Generate test video_id with uuid
- [x] Define test prompt and empty assets list

### Task 14.3: Test Phase 1 in Integration

- [x] Print "Testing Phase 1" message
- [x] Call validate_prompt(video_id, prompt, assets)
- [x] Assert result1['status'] == 'success'
- [x] Assert 'spec' in result1['output_data']
- [x] Extract spec from output_data
- [x] Print completion message with template

### Task 14.4: Test Phase 2 in Integration

- [x] Print "Testing Phase 2" message
- [x] Call generate_animatic(video_id, spec)
- [x] Assert result2['status'] == 'success'
- [x] Assert 'animatic_urls' in result2['output_data']
- [x] Extract frame_urls from output_data
- [x] Print completion message with frame count
- [x] Print total cost (sum of both phases)

### Task 14.5: Verify Integration Results

- [x] Assert len(frame_urls) == len(spec['beats'])
- [x] Loop through frame_urls
- [x] Assert each url starts with 's3://'

---

## ✅ PR #12, #13, #14 Checklist

Before merging:
- [x] Phase 2 task implemented
- [x] Manual test script created
- [x] Orchestrator updated to call Phase 2
- [x] Integration test written and passing (or skipped if no keys)
- [x] Both phases work together end-to-end

**Test Commands:**
```bash
# Start services
docker-compose up --build

# Test Phase 1 first
docker-compose exec api python test_phase1.py

# Test Phase 2
docker-compose exec api python test_phase2.py

# Test via API (if implemented)
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a luxury watch ad", "assets": []}'

# Poll status
curl http://localhost:8000/api/status/{video_id}
```

**Phase 2 is complete!** Both Phase 1 and Phase 2 are now working together in the pipeline.

---

## Next Steps

Once both people complete their phases:
- [ ] Merge all feature branches into `develop`
- [ ] Test end-to-end pipeline together
- [ ] Verify database records are created correctly
- [ ] Check S3 uploads work (animatic frames)
- [ ] Review code together
- [ ] Plan Phase 3-6 implementation or hand off to additional team members
- [ ] Begin deployment to AWS planning