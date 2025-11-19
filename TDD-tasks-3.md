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

- [x] Review `generate_storyboard` function implementation
- [x] Trace how beats are extracted from spec
- [x] Identify where image count is determined
- [x] Check for any hardcoded image counts or fixed loops
- [x] Document current behavior with examples

### Task 7.2: Fix Image Generation to Match Beat Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [x] Ensure loop iterates over `spec['beats']` directly
- [x] Remove any fixed image count logic (e.g., always generating 5 images)
- [x] Verify beat extraction: `beats = spec.get('beats', [])`
- [x] Ensure loop uses `enumerate(beats)` to get correct beat_index
- [x] Add logging to show beat count vs image count

### Task 7.3: Add Validation for Image Count

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [x] After generation loop, verify `len(storyboard_images) == len(beats)`
- [x] Raise ValueError if counts don't match
- [x] Log validation success/failure
- [x] Include beat count and image count in error message

### Task 7.4: Add Beat Count Validation and Truncation

**Goal:** Prevent Phase 1 from generating too many beats for the target duration

**File:** `backend/app/phases/phase1_validate/validation.py`

- [x] Add validation function: `validate_and_fix_beat_count(spec: dict) -> dict`
- [x] Calculate maximum beats: `max_beats = ceil(duration / 5)` (5s minimum beat length)
- [x] If `len(beats) > max_beats`: truncate beats to fit duration
- [x] Recalculate start times after truncation
- [x] Log WARNING when truncation occurs with details
- [x] Save truncation events to `backend/logs/beat_truncation.log` with timestamp, video_id, original count, truncated count
- [x] Call validation function in `build_full_spec()` before returning spec

### Task 7.5: Testing and Verification

- [x] Test with 1 beat (should generate 1 image)
- [x] Test with 3 beats (should generate 3 images)
- [x] Test with 5 beats (should generate 5 images)
- [x] Test with 7 beats (should generate 7 images)
- [x] Verify each image is correctly mapped to its beat
- [x] Verify beat_index in storyboard_images matches beat order
- [x] Test truncation: manually create spec with 10 beats for 15s duration (should truncate to 3)
- [x] Verify truncation log file is created when truncation occurs

---

## PR #8: Non-Blocking Orchestration with Celery Chains

**Goal:** Refactor orchestrator to use Celery Chains for non-blocking pipeline execution, enabling true concurrent video processing

**Current Issue:**
- **Blocking Orchestrator Problem**: The orchestrator uses `.get()` calls that block worker threads
- Worker with `--concurrency=4` can only handle 4 videos at once, even though worker is idle waiting for subtasks
- Each phase waits for the previous phase to complete before starting, holding worker threads hostage
- Sequential storyboard image generation is slow and inefficient (can be parallelized)

**The Problem (Current State):**
```python
# Current implementation (BAD - blocks worker)
@celery_app.task
def orchestrate_video(video_id):
    # Phase 1
    result1 = phase1_task.delay(video_id)
    plan = result1.get()  # ❌ BLOCKS worker thread waiting
    
    # Phase 2
    result2 = phase2_task.delay(video_id, plan)
    storyboard = result2.get()  # ❌ BLOCKS again
    
    # Phase 3
    result3 = phase3_task.delay(video_id, storyboard)
    chunks = result3.get()  # ❌ BLOCKS again
    
    # etc...
```

**Result:** Worker with `--concurrency=4` can only handle 4 videos at once, even though the worker is just sitting idle waiting for subtasks.

**The Solution: Celery Chains**
- Non-blocking orchestration using Celery's native workflow primitives
- Orchestrator dispatches entire pipeline as chain and returns immediately
- Worker thread freed to handle more videos concurrently
- Each phase automatically starts when previous phase completes

**Example Implementation:**
```python
from celery import chain

@celery_app.task
def orchestrate_video(video_id):
    """
    Dispatch entire pipeline as chain - returns immediately.
    Worker thread freed to handle more videos.
    """
    workflow = chain(
        phase1_planning.s(video_id),
        phase2_storyboard.s(),
        phase3_chunks.s(),
        phase4_stitch.s(),
        phase5_music.s()
    ).apply_async()
    
    # Returns immediately - worker thread freed!
    return workflow.id
```

**Investigation Needed:**
- Review current blocking orchestrator implementation in `pipeline.py`
- Identify all `.get()` calls that block worker threads
- Review current sequential storyboard generation implementation
- Identify dependencies between beat image generations
- Determine optimal parallelization strategy (Celery groups for beats, chains for phases)
- Consider rate limiting and cost implications

**Files to Review:**
- `backend/app/orchestrator/pipeline.py` (main orchestrator with blocking calls)
- `backend/app/phases/phase2_storyboard/task.py` (main generation loop)
- `backend/app/phases/phase2_storyboard/image_generation.py` (individual image generation)
- `backend/app/orchestrator/celery_app.py` (Celery configuration)

### Task 8.1: Investigate Current Blocking Orchestrator

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Review `run_pipeline` function implementation (note: function is `run_pipeline`, not `orchestrate_video_generation`)
- [x] Identify all `.apply()` calls that block worker threads (found 5 blocking points, one per phase)
- [x] Document current execution flow showing blocking points (see `backend/docs/pr8-investigation.md`)
- [x] Document worker thread utilization (worker threads spend most time idle waiting for API calls)
- [x] Review Phase 2 storyboard sequential generation loop (found in `task.py` lines 58-86)
- [x] Identify where `generate_beat_image` is called sequentially (sequential loop in Phase 2)
- [x] Check for any dependencies between beat generations (no dependencies - can be parallelized)

**Documentation**: See `backend/docs/pr8-investigation.md` for detailed analysis.

### Task 8.2: Design Non-Blocking Orchestration Strategy

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Design Celery Chain workflow for entire pipeline
- [x] Map phase dependencies (Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5)
- [x] Design chain structure: `chain(phase1.s(), phase2.s(), phase3.s(), phase4.s(), phase5.s())`
- [x] Plan how to pass data between chain links (each phase receives previous phase's PhaseOutput dict)
- [x] Design chain structure for orchestrator (parallelization within phases is out of scope)
- [x] Design error handling for chain failures and partial failures (each phase returns PhaseOutput with status)
- [x] Plan progress tracking mechanism for chain execution (each phase updates progress independently)

**Documentation**: See `backend/docs/pr8-design.md` for complete design specification.

---

## PR #9: Parallel Chunk Generation with Pipelined Chains

**Goal:** Enable parallel chunk generation with streaming execution - followers start immediately when their predecessor completes

**Current Issue:**
- Phase 4 generates chunks sequentially (slow)
- Chunks with reference images could be generated in parallel
- Chunks using last frames need to wait for their predecessor, but could start immediately when ready
- Current approach would force all Wave 1 chunks to finish before ANY Wave 2 chunk starts (inefficient)

**The Solution:**
- Use **pipelined chains** - each beat sequence (reference → follower) runs as an independent chain
- All chains run in parallel via `chord`
- Followers start immediately when their predecessor finishes (no waiting for other sequences)
- Phase 4 dynamically builds chain structure based on beat configuration

**Benefits:**
- **Maximum parallelism**: All reference chunks start together, followers start as soon as their predecessor finishes
- **Streaming execution**: No rigid wave boundaries - work flows continuously
- **Faster completion**: Follower chunks don't wait for slowest reference chunk in unrelated sequence
- **Worker threads remain non-blocking**: Returns chord signature, Celery handles waiting
- **Simpler mental model**: Each sequence is independent

**Execution Pattern Example:**
```
6 beats: [0-ref, 1-follow, 2-ref, 3-follow, 4-ref, 5-follow]

Sequence Chains (all run in parallel):
- Chain A: Chunk 0 (ref) → Chunk 1 (last frame)
- Chain B: Chunk 2 (ref) → Chunk 3 (last frame)  
- Chain C: Chunk 4 (ref) → Chunk 5 (last frame)

Timeline:
0s:  [Chunk 0] [Chunk 2] [Chunk 4]  ← All reference chunks start
5s:  [Chunk 0] [Chunk 2] [✓ Chunk 4 done → Chunk 5 starts immediately]
7s:  [Chunk 0] [✓ Chunk 2 done → Chunk 3 starts immediately] [Chunk 5]
10s: [✓ Chunk 0 done → Chunk 1 starts immediately] [Chunk 3] [Chunk 5]
12s: [Chunk 1] [✓ Chunk 3 done] [✓ Chunk 5 done]
15s: [✓ Chunk 1 done]

Compare to rigid waves (would wait until 10s to start ANY follower)
```

**Pipelined Chain Pattern Example:**
```python
from celery import chain, chord

# Individual chunk generation tasks
@celery_app.task
def generate_chunk_with_reference(beat, video_id):
    """Generate chunk from reference image."""
    chunk_result = generate_chunk(beat['reference_image'], video_id, beat['beat_index'])
    last_frame_path = extract_and_save_last_frame(chunk_result['url'])
    
    return {
        **chunk_result,
        'beat_index': beat['beat_index'],
        'last_frame_path': last_frame_path
    }

@celery_app.task
def generate_chunk_with_last_frame(prev_chunk_result, next_beat, video_id):
    """Generate chunk using last frame from previous chunk (receives prev result via chain)."""
    chunk_result = generate_chunk(
        prev_chunk_result['last_frame_path'],
        video_id,
        next_beat['beat_index']
    )
    
    return {
        **chunk_result,
        'beat_index': next_beat['beat_index']
    }

# Phase 4 orchestrator (dynamically builds chains)
@celery_app.task
def phase4_chunks(phase3_result):
    """Build pipelined chains - each beat sequence runs independently."""
    beats = phase3_result['beats']
    video_id = phase3_result['video_id']
    
    chains = []
    i = 0
    
    while i < len(beats):
        beat = beats[i]
        
        if not beat.get('reference_image'):
            raise ValueError(f"Beat {i} must have reference_image")
        
        # Start chain with reference beat
        beat_chain = [generate_chunk_with_reference.s(beat, video_id)]
        
        # Add follower beat if it exists and uses last frame
        if i + 1 < len(beats) and not beats[i + 1].get('reference_image'):
            beat_chain.append(
                generate_chunk_with_last_frame.s(beats[i + 1], video_id)
            )
            i += 2  # Skip next beat (included in chain)
        else:
            i += 1  # Just this beat
        
        chains.append(chain(*beat_chain))
    
    # All chains run in parallel, collect results when done
    return chord(chains)(finalize_phase4.s(phase3_result)).apply_async()

@celery_app.task
def finalize_phase4(chain_results, phase3_result):
    """Collect and merge all chunk results from parallel chains."""
    all_chunks = []
    for result in chain_results:
        # Each chain returns 1 or 2 chunks
        if isinstance(result, list):
            all_chunks.extend(result)
        else:
            all_chunks.append(result)
    
    all_chunks.sort(key=lambda x: x['beat_index'])
    return {**phase3_result, 'chunks': all_chunks}

# Main pipeline (stays simple - Phase 4 handles complexity internally)
workflow = chain(
    phase1_planning.s(video_id, prompt),
    phase2_storyboards.s(),
    phase3_references.s(),
    phase4_chunks.s(),  # Returns chord of chains (auto-waits)
    phase5_stitch.s(),
    phase6_music.s()
).apply_async()
```

**Files to Review:**
- `backend/app/phases/phase4_chunks_storyboard/task.py` (main chunk generation logic)
- `backend/app/orchestrator/pipeline.py` (orchestrator with chain pattern)
- `backend/app/orchestrator/celery_app.py` (Celery configuration)

### Task 9.1: Investigate Current Phase 4 Implementation

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Review current sequential chunk generation loop
- [ ] Identify how reference images are used vs last frames
- [ ] Understand beat sequence structure (reference → follower patterns)
- [ ] Document how beats are marked with `reference_image` field
- [ ] Trace how last frames are extracted and passed to next chunk
- [ ] Confirm chunks are saved to DB with proper ordering
- [ ] Identify where chunks are currently generated in sequence

### Task 9.2: Design Pipelined Chain Pattern

**Files:** `backend/app/phases/phase4_chunks_storyboard/task.py`, `backend/app/orchestrator/pipeline.py`

- [ ] Design beat sequence identification logic (reference → follower pairing)
- [ ] Design chain structure: `chain(ref_chunk, follower_chunk)` for each sequence
- [ ] Plan data flow: reference task extracts last frame → passes to follower via chain
- [ ] Design chord-of-chains structure for parallel sequence execution
- [ ] Plan how to handle beats that are all references (no followers)
- [ ] Plan error handling for partial failures in individual chains
- [ ] Design progress tracking for streaming execution

**Key Questions:**
- [ ] How to iterate through beats and identify sequences?
- [ ] How to pass last frame from reference task to follower task in chain?
- [ ] How to collect results from chains of varying lengths (1 or 2 chunks)?
- [ ] How to ensure beat_index ordering is preserved?

### Task 9.3: Create Individual Chunk Generation Tasks

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Create `generate_chunk_with_reference` task
  - Input: beat dict, video_id
  - Extract reference_image from beat
  - Call video generation API with reference
  - Save chunk to DB with beat_index
  - **Extract and save last frame** for potential follower
  - Return chunk metadata (id, url, beat_index, last_frame_path)

- [ ] Create `generate_chunk_with_last_frame` task
  - Input: **prev_chunk_result** (from chain), next_beat dict, video_id
  - Extract last_frame_path from prev_chunk_result
  - Call video generation API with last frame
  - Save chunk to DB with beat_index
  - Return chunk metadata (id, url, beat_index)

- [ ] Ensure both tasks are idempotent (can retry safely)
- [ ] Add proper error handling and logging
- [ ] Test that chain passes prev_chunk_result correctly to follower

### Task 9.4: Create Phase 4 Orchestrator with Dynamic Chain Building

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Create `phase4_chunks` task
  - Input: phase3_result (contains beats and storyboard data)
  - Parse beats array to identify sequences
  - Build list of chains (one per sequence)
  - Wrap all chains in chord for parallel execution
  - Return chord AsyncResult (Celery auto-waits)

- [ ] Implement beat sequence parsing logic:
  ```python
  chains = []
  i = 0
  while i < len(beats):
      # Check if beat has reference
      if beat.get('reference_image'):
          # Start chain with reference
          chain_tasks = [generate_chunk_with_reference.s(beat, video_id)]
          
          # Check if next beat is follower (no reference)
          if i+1 < len(beats) and not beats[i+1].get('reference_image'):
              # Add follower to chain
              chain_tasks.append(generate_chunk_with_last_frame.s(beats[i+1], video_id))
              i += 2  # Skip next beat
          else:
              i += 1  # Just this beat
          
          chains.append(chain(*chain_tasks))
      else:
          # Error: beat without reference and not following a reference
          raise ValueError(f"Beat {i} missing reference_image")
  ```

- [ ] Test chain building logic with various beat configurations

### Task 9.5: Create Finalize Callback

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Create `finalize_phase4` task
  - Input: chain_results (list of results, each 1 or 2 chunks), phase3_result
  - Flatten results: each chain returns either single chunk or 2 chunks
  - Handle both single results and lists
  - Sort chunks by beat_index
  - Return complete phase4_result with all chunks ordered correctly
  - Log completion and total chunk count

- [ ] Handle result flattening:
  ```python
  all_chunks = []
  for result in chain_results:
      if isinstance(result, list):
          all_chunks.extend(result)
      else:
          all_chunks.append(result)
  
  all_chunks.sort(key=lambda x: x['beat_index'])
  ```

### Task 9.6: Update Orchestrator to Use New Phase 4

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Verify main pipeline structure remains simple:
  ```python
  workflow = chain(
      phase1_planning.s(...),
      phase2_storyboards.s(),
      phase3_references.s(),
      phase4_chunks.s(),  # Returns chord of chains (auto-waits)
      phase5_stitch.s(),
      phase6_music.s()
  ).apply_async()
  ```
- [ ] Remove old sequential `phase4_chunks` implementation
- [ ] Ensure phase4_chunks is imported correctly
- [ ] Test chain execution flows correctly

### Task 9.7: Handle Edge Cases

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Handle case where all beats have reference images (all single-chunk chains)
  - Each sequence is length 1, still runs in parallel
  - No follower chunks
  
- [ ] Handle case where beat without reference is not preceded by reference beat
  - Should raise ValueError with clear message
  - This indicates Phase 1/3 data issue

- [ ] Handle case with single beat (1 sequence, 1 chunk)
  - Still use chord pattern for consistency
  - Chord with single chain works fine

- [ ] Handle case with alternating pattern (ref, follow, ref, follow, ...)
  - Should create N/2 chains

- [ ] Ensure beat_index ordering is preserved in final results
  - Sort by beat_index in finalize_phase4

### Task 9.8: Update Progress Tracking

**Files:** `backend/app/orchestrator/progress.py`, chunk generation tasks

- [ ] Update progress for Phase 4 start
- [ ] Update progress for each reference chunk completion
  - Progress: (completed_refs / total_refs) * 50%
- [ ] Update progress for each follower chunk completion
  - Progress: 50% + (completed_followers / total_followers) * 50%
- [ ] Update progress for Phase 4 completion (100%)
- [ ] Calculate progress percentage accounting for streaming execution
- [ ] Log when individual chains complete

### Task 9.9: Testing and Verification

- [ ] Test with 2 beats (1 ref → 1 follow): 1 chain with 2 tasks
- [ ] Test with 3 beats (ref, follow, ref): 2 chains (first has 2 tasks, second has 1 task)
- [ ] Test with 4 beats (ref, follow, ref, follow): 2 chains, each with 2 tasks
- [ ] Test with 6 beats (alternating): 3 chains, each with 2 tasks, all run in parallel
- [ ] Test with all reference images: N chains, each with 1 task
- [ ] Verify chunks are saved to DB in correct beat_index order
- [ ] Verify follower chunks start immediately when predecessor finishes (check timestamps)
- [ ] Verify follower doesn't wait for unrelated reference chunks to finish
- [ ] Test error handling: if 1 reference chunk fails, does its follower fail gracefully?
- [ ] Test error handling: if 1 chain fails, do other chains continue?
- [ ] Verify progress tracking updates in real-time as chunks complete
- [ ] Test with concurrent video generations to verify true parallelization
- [ ] Compare execution time to sequential approach (should be significantly faster)

**Key Implementation Notes:**
1. **No `.get()` calls** - return chord AsyncResult, let Celery handle waiting
2. **Chain data passing** - follower task receives previous chunk result as first parameter
3. **Beat ordering** - sort by beat_index in finalize callback
4. **Last frame extraction** - happens in reference task, passed via chain to follower
5. **Error isolation** - failure in one chain doesn't block other chains
6. **Dynamic structure** - phase4_chunks builds chain structure at runtime based on beat configuration

---