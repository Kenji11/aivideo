# TDD Implementation Tasks - Part 5: Orchestration & API

**Goal:** Implement pipeline orchestrator and API endpoints

---

## PR #13: Pipeline Orchestrator

### Task 13.1: Create Orchestrator

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Import celery_app
- [ ] Import all 5 phase tasks
- [ ] Import update_progress, update_cost from .progress
- [ ] Import time, logging
- [ ] Create logger instance
- [ ] Create `@celery_app.task` decorator
- [ ] Define `run_pipeline(video_id, prompt, creativity_level=None)` function
- [ ] Add docstring
- [ ] Record start_time
- [ ] Initialize total_cost = 0.0
- [ ] Log pipeline start

### Task 13.2: Implement Phase 1 Execution

**File:** `backend/app/orchestrator/pipeline.py` (continued)

- [ ] Wrap in try/except block
- [ ] Call update_progress(video_id, "planning", 10)
- [ ] Call plan_video_intelligent.delay(...).get(timeout=60)
- [ ] Check if result1['status'] != "success"
- [ ] If failed, raise exception with error message
- [ ] Add cost to total_cost
- [ ] Call update_cost(video_id, "phase1", cost)
- [ ] Extract spec from output_data

### Task 13.3: Implement Phase 2 Execution

**File:** `backend/app/orchestrator/pipeline.py` (continued)

- [ ] Call update_progress(video_id, "storyboarding", 25)
- [ ] Call generate_storyboard.delay(video_id, spec).get(timeout=300)
- [ ] Check if result2['status'] != "success"
- [ ] If failed, raise exception
- [ ] Add cost to total_cost
- [ ] Call update_cost(video_id, "phase2", cost)
- [ ] Extract storyboard from output_data

### Task 13.4: Implement Phase 3 Execution

**File:** `backend/app/orchestrator/pipeline.py` (continued)

- [ ] Call update_progress(video_id, "generating_chunks", 40)
- [ ] Call generate_chunks.delay(video_id, spec, storyboard).get(timeout=600)
- [ ] Check if result3['status'] != "success"
- [ ] If failed, raise exception
- [ ] Add cost to total_cost
- [ ] Call update_cost(video_id, "phase3", cost)
- [ ] Extract chunks from output_data

### Task 13.5: Implement Phase 4 Execution

**File:** `backend/app/orchestrator/pipeline.py` (continued)

- [ ] Call update_progress(video_id, "stitching", 70)
- [ ] Call stitch_chunks.delay(video_id, chunks).get(timeout=60)
- [ ] Check if result4['status'] != "success"
- [ ] If failed, raise exception
- [ ] Add cost to total_cost (should be 0)
- [ ] Call update_cost(video_id, "phase4", cost)
- [ ] Extract stitched_url from output_data

### Task 13.6: Implement Phase 5 Execution

**File:** `backend/app/orchestrator/pipeline.py` (continued)

- [ ] Call update_progress(video_id, "adding_music", 85)
- [ ] Call generate_music.delay(video_id, spec, stitched_url).get(timeout=120)
- [ ] Check if result5['status'] != "success"
- [ ] If failed, raise exception
- [ ] Add cost to total_cost
- [ ] Call update_cost(video_id, "phase5", cost)
- [ ] Extract final_video_url from output_data

### Task 13.7: Implement Completion & Error Handling

**File:** `backend/app/orchestrator/pipeline.py` (continued)

- [ ] Call update_progress with:
  - [ ] video_id, "complete", 100
  - [ ] spec=spec
  - [ ] storyboard_images=storyboard images list
  - [ ] chunk_urls=chunks list
  - [ ] stitched_url=stitched_url
  - [ ] final_video_url=final_video_url
  - [ ] total_cost=total_cost
  - [ ] generation_time=elapsed time
- [ ] Return success dict with all URLs and metadata
- [ ] In except block:
  - [ ] Call update_progress(video_id, "failed", None, error=str(e))
  - [ ] Re-raise exception

### Task 13.8: Update Progress Helper

**File:** `backend/app/orchestrator/progress.py`

- [ ] Update update_progress function to handle new kwargs:
  - [ ] storyboard_images
  - [ ] chunk_urls
  - [ ] stitched_url
  - [ ] final_video_url
- [ ] Set video.storyboard_images if in kwargs
- [ ] Set video.chunk_urls if in kwargs
- [ ] Set video.stitched_url if in kwargs
- [ ] Set video.final_video_url if in kwargs
- [ ] Set video.num_beats = len(spec['beats']) if spec in kwargs
- [ ] Set video.num_chunks if chunk_urls in kwargs

---

## PR #14: API Endpoints

### Task 14.1: Update Generate Endpoint

**File:** `backend/app/api/generate.py`

- [ ] Import run_pipeline from orchestrator
- [ ] Import GenerateRequest, GenerateResponse from schemas
- [ ] Import uuid
- [ ] Create router = APIRouter()
- [ ] Create POST endpoint `/api/generate`
- [ ] Accept GenerateRequest body
- [ ] Generate video_id with uuid.uuid4()
- [ ] Extract creativity_level from request (optional, default None)
- [ ] Call run_pipeline.delay(video_id, prompt, creativity_level)
- [ ] Return GenerateResponse with:
  - [ ] video_id
  - [ ] status="queued"
  - [ ] message="Video generation started"

### Task 14.2: Update Status Endpoint

**File:** `backend/app/api/status.py`

- [ ] Import FastAPI dependencies
- [ ] Import VideoGeneration model
- [ ] Import get_db dependency
- [ ] Create router = APIRouter()
- [ ] Create GET endpoint `/api/status/{video_id}`
- [ ] Query database for video by id
- [ ] If not found, raise 404
- [ ] Return StatusResponse with:
  - [ ] video_id
  - [ ] status
  - [ ] progress
  - [ ] current_phase
  - [ ] estimated_time_remaining (calculate based on phase)
  - [ ] error (if failed)

### Task 14.3: Update Video Endpoint

**File:** `backend/app/api/video.py`

- [ ] Import FastAPI dependencies
- [ ] Import VideoGeneration model
- [ ] Import get_db dependency
- [ ] Create router = APIRouter()
- [ ] Create GET endpoint `/api/video/{video_id}`
- [ ] Query database for video by id
- [ ] If not found, raise 404
- [ ] Return VideoResponse with:
  - [ ] video_id
  - [ ] status
  - [ ] final_video_url
  - [ ] cost_usd
  - [ ] generation_time_seconds
  - [ ] created_at
  - [ ] completed_at
  - [ ] spec (optional, full spec object)
  - [ ] storyboard_images (optional)
  - [ ] chunk_urls (optional)

### Task 14.4: Update Main App

**File:** `backend/app/main.py`

- [ ] Verify all routers are included
- [ ] Verify database initialization on startup
- [ ] Verify CORS is configured
- [ ] Add logging configuration

---

## PR #15: End-to-End Tests

### Task 15.1: Create API Tests

**File:** `backend/app/tests/test_api/test_generate.py`

- [ ] Import TestClient from fastapi.testclient
- [ ] Import app from main
- [ ] Create test_client = TestClient(app)
- [ ] Create `test_generate_endpoint()`:
  - [ ] POST to /api/generate with valid prompt
  - [ ] Assert 200 status
  - [ ] Assert video_id in response
  - [ ] Assert status == "queued"
- [ ] Create `test_generate_with_creativity()`:
  - [ ] POST with creativity_level=0.0
  - [ ] Assert accepted
- [ ] Create `test_generate_invalid_prompt()`:
  - [ ] POST with empty prompt
  - [ ] Assert 422 validation error

### Task 15.2: Create Status API Tests

**File:** `backend/app/tests/test_api/test_status.py`

- [ ] Import TestClient
- [ ] Create `test_status_endpoint()`:
  - [ ] Create test video in database
  - [ ] GET /api/status/{video_id}
  - [ ] Assert 200 status
  - [ ] Assert correct video_id
  - [ ] Assert progress field exists
- [ ] Create `test_status_not_found()`:
  - [ ] GET with fake video_id
  - [ ] Assert 404

### Task 15.3: Create Video API Tests

**File:** `backend/app/tests/test_api/test_video.py`

- [ ] Import TestClient
- [ ] Create `test_video_endpoint()`:
  - [ ] Create completed video in database
  - [ ] GET /api/video/{video_id}
  - [ ] Assert 200 status
  - [ ] Assert final_video_url exists
  - [ ] Assert cost_usd > 0
- [ ] Create `test_video_not_complete()`:
  - [ ] Create in-progress video
  - [ ] GET /api/video/{video_id}
  - [ ] Assert final_video_url is None

### Task 15.4: Create Complete Workflow Test

**File:** `backend/app/tests/test_integration/test_complete_workflow.py`

- [ ] Import pytest, time
- [ ] Import TestClient, run_pipeline
- [ ] Create `@pytest.mark.integration` test
- [ ] Create `test_complete_workflow_via_api()`:
  - [ ] POST to /api/generate
  - [ ] Get video_id
  - [ ] Poll /api/status until complete or failed (max 5 min)
  - [ ] Assert status == "complete"
  - [ ] GET /api/video/{video_id}
  - [ ] Assert final_video_url exists
  - [ ] Assert cost_usd < 0.50
  - [ ] Download final video and verify it exists
  - [ ] Verify video duration matches spec

---

## PR #16: Documentation & Manual Testing

### Task 16.1: Create Manual Test Script

**File:** `backend/test_full_pipeline.py`

- [ ] Add shebang and docstring
- [ ] Import run_pipeline, all constants
- [ ] Create `test_pipeline_15s()` function
- [ ] Create `test_pipeline_30s()` function
- [ ] Create `test_pipeline_all_archetypes()` function (test each archetype)
- [ ] Create `test_pipeline_creativity_levels()` function (test 0.0, 0.5, 1.0)
- [ ] Add main block to run all tests
- [ ] Print results summary (success/fail, cost, time)

### Task 16.2: Update README

**File:** `backend/README.md`

- [ ] Add section on new architecture
- [ ] Add section on beat library (15 beats)
- [ ] Add section on template archetypes (5 archetypes)
- [ ] Add section on creativity control
- [ ] Add API usage examples
- [ ] Add cost breakdown table
- [ ] Add troubleshooting section

### Task 16.3: Create CHANGELOG

**File:** `backend/CHANGELOG.md`

- [ ] Add entry for version 2.0
- [ ] List breaking changes (removed Phase 2 animatic)
- [ ] List new features (beat library, archetypes, LLM agent)
- [ ] List improvements (narrative coherence, cost reduction)

---

## ✅ PR #13, #14, #15, #16 Checklist

Before merging:
- [ ] Pipeline orchestrator executes all 5 phases
- [ ] All API endpoints work correctly
- [ ] Database tracking is accurate
- [ ] Integration tests pass
- [ ] Manual test script works
- [ ] Documentation is complete
- [ ] Full 15s video generation works end-to-end
- [ ] Full 30s video generation works end-to-end
- [ ] All 5 archetypes generate successfully
- [ ] Creativity levels (0.0, 0.5, 1.0) all work

**Pipeline is complete!**