# TDD Implementation Tasks - Part 3: Storyboard Generation Fixes

**Goal:** Fix storyboard image generation to match beat count and enable parallel generation

---

## PR #7: Fix Storyboard Image Count to Match Beat Count

**Goal:** Ensure storyboard generation creates exactly N images for N beats (e.g., 3 beats = 3 images, not 5)

**Current Issue:**
- Storyboard generation may be creating a fixed number of images (e.g., 5) regardless of actual beat count
- Need to ensure image count matches the number of beats in the spec

**Investigation Needed:**
- Review Phase 2 storyboard generation logic
- Identify where image count is determined
- Verify beat extraction from spec
- Check for any hardcoded image counts

**Files to Review:**
- `backend/app/phases/phase2_storyboard/task.py`
- `backend/app/phases/phase2_storyboard/image_generation.py`
- `backend/app/orchestrator/pipeline.py` (Phase 2 invocation)

### Task 7.1: Investigate Current Storyboard Generation Logic

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Review `generate_storyboard` function implementation
- [ ] Trace how beats are extracted from spec
- [ ] Identify where image count is determined
- [ ] Check for any hardcoded image counts or fixed loops
- [ ] Document current behavior with examples

### Task 7.2: Fix Image Generation to Match Beat Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Ensure loop iterates over `spec['beats']` directly
- [ ] Remove any fixed image count logic (e.g., always generating 5 images)
- [ ] Verify beat extraction: `beats = spec.get('beats', [])`
- [ ] Ensure loop uses `enumerate(beats)` to get correct beat_index
- [ ] Add logging to show beat count vs image count

### Task 7.3: Add Validation for Image Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] After generation loop, verify `len(storyboard_images) == len(beats)`
- [ ] Raise ValueError if counts don't match
- [ ] Log validation success/failure
- [ ] Include beat count and image count in error message

### Task 7.4: Testing and Verification

- [ ] Test with 1 beat (should generate 1 image)
- [ ] Test with 3 beats (should generate 3 images)
- [ ] Test with 5 beats (should generate 5 images)
- [ ] Test with 7 beats (should generate 7 images)
- [ ] Verify each image is correctly mapped to its beat
- [ ] Verify beat_index in storyboard_images matches beat order

---

## PR #8: Enable Parallel Generation for Independent Beats

**Goal:** Generate storyboard images for independent beats in parallel instead of sequentially

**Current Issue:**
- Storyboard images are generated one at a time in a loop
- Each beat image generation is independent and can be parallelized
- Sequential generation is slow and inefficient

**Investigation Needed:**
- Review current sequential generation implementation
- Identify dependencies between beat image generations
- Determine optimal parallelization strategy (Celery groups, async, etc.)
- Consider rate limiting and cost implications

**Files to Review:**
- `backend/app/phases/phase2_storyboard/task.py` (main generation loop)
- `backend/app/phases/phase2_storyboard/image_generation.py` (individual image generation)
- `backend/app/orchestrator/celery_app.py` (Celery configuration)

### Task 8.1: Investigate Current Sequential Implementation

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Review current loop structure in `generate_storyboard`
- [ ] Identify where `generate_beat_image` is called sequentially
- [ ] Document current execution flow
- [ ] Check for any dependencies between beat generations
- [ ] Measure current generation time per beat

### Task 8.2: Design Parallel Generation Strategy

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Choose parallelization approach (Celery group vs async vs threading)
- [ ] Review Celery group/chord patterns for parallel tasks
- [ ] Consider rate limiting for image generation API
- [ ] Design error handling for partial failures
- [ ] Plan progress tracking mechanism

### Task 8.3: Implement Parallel Beat Image Generation

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Convert `generate_beat_image` to Celery task (if not already)
- [ ] Use Celery `group` to create parallel tasks for all beats
- [ ] Execute group and collect results
- [ ] Handle task results and extract image data
- [ ] Maintain beat order in results (use beat_index for sorting)

### Task 8.4: Add Error Handling for Parallel Tasks

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Handle individual task failures gracefully
- [ ] Collect successful and failed beat generations
- [ ] Log which beats succeeded/failed
- [ ] Decide on failure strategy (fail all vs partial success)
- [ ] Return appropriate error messages

### Task 8.5: Add Progress Tracking

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Track progress of parallel tasks
- [ ] Update progress for each completed beat image
- [ ] Log progress updates (e.g., "3/5 beats generated")
- [ ] Use Celery result tracking if available

### Task 8.6: Testing and Performance Measurement

- [ ] Test parallel generation with 3 beats
- [ ] Test parallel generation with 5 beats
- [ ] Test parallel generation with 7 beats
- [ ] Measure time improvement vs sequential generation
- [ ] Verify cost calculation remains accurate (sum of all image costs)
- [ ] Verify all images are generated correctly
- [ ] Test error handling with simulated failures

---

