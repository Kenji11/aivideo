# Phase 2 Tasks - Part B: Task Implementation & Integration

**Owner:** Person handling Phase 2  
**Goal:** Implement Phase 2 Celery task and integrate with pipeline

---

## PR #12: Phase 2 Task Implementation

### Task 12.1: Implement Phase 2 Celery Task

**File:** `backend/app/phases/phase2_animatic/task.py`

- [ ] Import celery_app from orchestrator
- [ ] Import PhaseOutput from common.schemas
- [ ] Import AnimaticGenerationService
- [ ] Import time module
- [ ] Import Dict from typing

### Task 12.2: Implement generate_animatic Task Function

- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_animatic(self, video_id, spec)` signature
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Wrap logic in try/except block

### Task 12.3: Implement Success Path

- [ ] Initialize AnimaticGenerationService
- [ ] Call service.generate_frames(video_id, spec)
- [ ] Create PhaseOutput with success status
- [ ] Set video_id, phase="phase2_animatic"
- [ ] Set output_data={"animatic_urls": frame_urls}
- [ ] Set cost_usd=service.total_cost
- [ ] Calculate duration_seconds
- [ ] Set error_message=None
- [ ] Return output.dict()

### Task 12.4: Implement Error Path

- [ ] In except block, create PhaseOutput with failed status
- [ ] Set empty output_data
- [ ] Set cost_usd=0.0
- [ ] Calculate duration_seconds
- [ ] Set error_message=str(e)
- [ ] Return output.dict()

### Task 12.5: Create Manual Test Script

**File:** `backend/test_phase2.py`

- [ ] Add shebang and docstring
- [ ] Import sys and add app to path
- [ ] Import AnimaticGenerationService, generate_animatic_prompt, json

### Task 12.6: Implement test_prompt_generation Function

- [ ] Create `test_prompt_generation()` function
- [ ] Print test header
- [ ] Define test_beats list with 3 different beat types
- [ ] Define style dictionary
- [ ] Loop through test_beats
- [ ] Generate prompt for each beat
- [ ] Print beat name, action, and generated prompt

### Task 12.7: Implement test_full_generation Function

- [ ] Create `test_full_generation()` function
- [ ] Print test header
- [ ] Try to load test_spec_1.json (from Phase 1)
- [ ] If FileNotFoundError, print warning and return
- [ ] Print spec template and beat count
- [ ] Initialize AnimaticGenerationService
- [ ] Define test_video_id
- [ ] Call service.generate_frames(test_video_id, spec)
- [ ] Print success message with frame count and cost
- [ ] Print all frame URLs
- [ ] Save result to test_animatic_result.json
- [ ] Add exception handling with error printing

### Task 12.8: Add Main Block

- [ ] Add `if __name__ == "__main__"` block
- [ ] Call test_prompt_generation()
- [ ] Add commented call to test_full_generation()

---

## PR #13: Update Orchestrator for Phase 2

### Task 13.1: Update Pipeline Imports

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Add import for generate_animatic task from phase2_animatic.task

### Task 13.2: Integrate Phase 2 into Pipeline

- [ ] After Phase 1 success, add `update_progress(video_id, "generating_animatic", 25)`
- [ ] Call `generate_animatic.delay(video_id, result1['output_data']['spec']).get(timeout=300)`
- [ ] Store result as result2
- [ ] Check if result2['status'] != "success", raise exception with error message
- [ ] Add result2['cost_usd'] to total_cost
- [ ] Call `update_cost(video_id, "phase2", result2['cost_usd'])`
- [ ] Update TODO comment to say "Phase 3-6"
- [ ] Update final update_progress call to include animatic_urls parameter
- [ ] Update return dictionary to include animatic_urls and updated cost/time

### Task 13.3: Update Return Statement

- [ ] Add "animatic_urls": result2['output_data']['animatic_urls'] to return dict
- [ ] Update "cost_usd" to use updated total_cost
- [ ] Update "generation_time" to use calculated time

---

## PR #14: Integration Tests

### Task 14.1: Create Integration Test File

**File:** `backend/app/tests/test_integration/test_phase1_and_2.py`

- [ ] Import pytest, uuid, os
- [ ] Import validate_prompt and generate_animatic tasks

### Task 14.2: Implement Integration Test

- [ ] Create `test_phase1_and_phase2_integration()` function
- [ ] Add `@pytest.mark.integration` decorator
- [ ] Add `@pytest.mark.skipif` for API keys check
- [ ] Generate test video_id with uuid
- [ ] Define test prompt and empty assets list

### Task 14.3: Test Phase 1 in Integration

- [ ] Print "Testing Phase 1" message
- [ ] Call validate_prompt(video_id, prompt, assets)
- [ ] Assert result1['status'] == 'success'
- [ ] Assert 'spec' in result1['output_data']
- [ ] Extract spec from output_data
- [ ] Print completion message with template

### Task 14.4: Test Phase 2 in Integration

- [ ] Print "Testing Phase 2" message
- [ ] Call generate_animatic(video_id, spec)
- [ ] Assert result2['status'] == 'success'
- [ ] Assert 'animatic_urls' in result2['output_data']
- [ ] Extract frame_urls from output_data
- [ ] Print completion message with frame count
- [ ] Print total cost (sum of both phases)

### Task 14.5: Verify Integration Results

- [ ] Assert len(frame_urls) == len(spec['beats'])
- [ ] Loop through frame_urls
- [ ] Assert each url starts with 's3://'

---

## ✅ PR #12, #13, #14 Checklist

Before merging:
- [ ] Phase 2 task implemented
- [ ] Manual test script created
- [ ] Orchestrator updated to call Phase 2
- [ ] Integration test written and passing (or skipped if no keys)
- [ ] Both phases work together end-to-end

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