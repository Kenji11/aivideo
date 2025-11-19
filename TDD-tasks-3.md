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

**Goal:** Enable parallel chunk generation with streaming execution - continuous chunks start immediately when their reference image chunk completes

**TERMINOLOGY (Code-First Approach):**
- **Reference Image Chunk**: Chunk that starts a beat, uses storyboard image from Phase 2 (`beat['image_url']`)
- **Continuous Chunk**: Chunk that continues within same beat, uses last frame from previous chunk
- **Chunk Pair**: Reference image chunk + Continuous chunk (for beats spanning 2 chunks)
- **Single-Chunk Beat**: Beat that fits in one chunk (5s beat with 5s chunks)
- **beat_to_chunk_map**: Dictionary mapping chunk indices → beat indices (identifies which chunks start beats)

**SCOPE LIMITATIONS:**
- Beats can span 1 or 2 chunks only (5s or 10s beats with 5s chunks)
- No 15s+ beats in this PR (would need 3+ chunk chains)
- Pairs only: `chain(ref_image, continuous)` - max 2 tasks per chain

**NEW FUNCTIONS (Added to `task.py`):**
- `generate_chunk_reference_image()` - Celery task for reference image chunks
- `generate_chunk_continuous()` - Celery task for continuous chunks
- `generate_chunks_parallel()` - Main orchestrator function (replaces sequential service)
- `finalize_chunks()` - Celery task callback to collect chain results

**NO NEW FILES** - All changes in existing files

**Current Issue:**
- Phase 4 generates chunks sequentially in `service.py` (slow)
- Reference image chunks are independent and could run in parallel
- Continuous chunks must wait for their reference chunk, but could start immediately when ready
- Current sequential approach wastes time: Chunk 3 waits for Chunk 1 to complete even though they're independent

**The Solution:**
- Use **pipelined chains** - each chunk pair (reference_image → continuous) runs as independent chain
- All chains run in parallel via `chord`
- Continuous chunks start immediately when their reference chunk finishes (no waiting for unrelated chunks)
- Main orchestrator (`generate_chunks_parallel()`) dynamically builds chains based on `beat_to_chunk_map`

**Benefits:**
- **Maximum parallelism**: All reference image chunks start together, continuous chunks start immediately when ready
- **Streaming execution**: No waiting for unrelated chunks - work flows continuously
- **Faster completion**: Continuous chunks don't wait for unrelated reference chunks
- **Non-blocking**: Main task waits on chord (blocks on chord.get(), but all chunk work happens in parallel)
- **Simpler mental model**: Each pair is independent

**Execution Pattern Example:**
```
4 chunks from 2 beats: [Beat 0: 10s, Beat 1: 10s] with 5s chunks
Chunks: [0-ref, 1-cont, 2-ref, 3-cont]

Chains (all run in parallel):
- Chain A: Chunk 0 (ref image, Beat 0) → Chunk 1 (continuous, Beat 0)
- Chain B: Chunk 2 (ref image, Beat 1) → Chunk 3 (continuous, Beat 1)

Timeline:
0s:  [Chunk 0] [Chunk 2]  ← Both reference image chunks start in parallel
5s:  [✓ Chunk 0 done → Chunk 1 starts] [Chunk 2]
7s:  [Chunk 1] [✓ Chunk 2 done → Chunk 3 starts]  ← Chunk 3 starts even though Chunk 1 still running
10s: [✓ Chunk 1 done] [Chunk 3]
12s: [✓ Chunk 3 done]

Sequential would be: Chunk 0 → Chunk 1 → Chunk 2 → Chunk 3 (15s+)
Parallel is: (Chunk 0 → Chunk 1) || (Chunk 2 → Chunk 3) (~12s, 20% faster)
```

**Pipelined Chain Pattern Example (Updated Terminology):**
```python
from celery import chain, chord

# Individual chunk generation tasks (in task.py)
@celery_app.task
def generate_chunk_reference_image(chunk_spec_dict):
    """Generate chunk using storyboard image from Phase 2."""
    chunk_spec = ChunkSpec(**chunk_spec_dict)
    
    # Use storyboard image from beat['image_url']
    chunk_result = generate_single_chunk_with_storyboard.apply([chunk_spec_dict, beat_to_chunk_map])
    
    return {
        'chunk_url': chunk_result['chunk_url'],
        'last_frame_url': chunk_result['last_frame_url'],
        'chunk_num': chunk_spec.chunk_num,
        'cost': chunk_result['cost']
    }

@celery_app.task
def generate_chunk_continuous(prev_result, chunk_spec_dict):
    """Generate chunk using last frame from previous chunk (receives prev result via chain)."""
    chunk_spec = ChunkSpec(**chunk_spec_dict)
    
    # Update chunk spec with last frame from previous chunk
    chunk_spec.previous_chunk_last_frame = prev_result['last_frame_url']
    
    # Generate continuous chunk
    result = generate_single_chunk_continuous(chunk_spec)
    
    # CRITICAL: Return list containing BOTH chunks (chains only return last task's result)
    return [
        prev_result,  # Reference image chunk (from chain input)
        {
            'chunk_url': result['chunk_url'],
            'chunk_num': chunk_spec.chunk_num,
            'cost': result['cost']
        }
    ]

# Phase 4 parallel orchestrator (in task.py)
def generate_chunks_parallel(video_id, spec, reference_urls, user_id):
    """Build pipelined chains - each chunk pair runs independently."""
    # Build chunk specs and beat_to_chunk_map
    chunk_specs, beat_to_chunk_map = build_chunk_specs_with_storyboard(
        video_id, spec, reference_urls, user_id
    )
    
    chains = []
    i = 0
    
    while i < len(chunk_specs):
        # Check if this chunk starts a beat (has storyboard image)
        if i in beat_to_chunk_map:
            # Reference image chunk - start chain
            chain_tasks = [generate_chunk_reference_image.s(chunk_specs[i].dict())]
            
            # Check if next chunk continues same beat (no storyboard)
            if i + 1 < len(chunk_specs) and (i + 1) not in beat_to_chunk_map:
                # Continuous chunk - add to chain
                chain_tasks.append(generate_chunk_continuous.s(chunk_specs[i + 1].dict()))
                i += 2  # Skip next chunk
            else:
                i += 1  # Single-chunk beat
            
            chains.append(chain(*chain_tasks))
        else:
            raise PhaseException(f"Chunk {i} is orphaned (no storyboard and not paired)")
    
    # All chains run in parallel, finalize collects results
    chord_result = chord(chains)(finalize_chunks.s(video_id, spec)).apply_async()
    
    # Wait for all chains to complete
    final_result = chord_result.get()
    
    return final_result

@celery_app.task
def finalize_chunks(chain_results, video_id, spec):
    """Collect and merge chunk results from all parallel chains."""
    all_chunks = []
    total_cost = 0.0
    
    for result in chain_results:
        # Single-chunk chain returns dict, pair chain returns list [ref, cont]
        if isinstance(result, list):
            for chunk in result:
                all_chunks.append(chunk)
                total_cost += chunk['cost']
        else:
            all_chunks.append(result)
            total_cost += result['cost']
    
    # Sort by chunk_num to maintain order
    all_chunks.sort(key=lambda x: x['chunk_num'])
    
    chunk_urls = [chunk['chunk_url'] for chunk in all_chunks]
    
    return {'chunk_urls': chunk_urls, 'total_cost': total_cost}

# Main Phase 4 task (in task.py) - NO CHANGE to external interface
@celery_app.task
def generate_chunks(self, phase3_output, user_id, model):
    # ... validation ...
    
    # NEW: Call parallel generation
    chunk_results = generate_chunks_parallel(video_id, spec, reference_urls, user_id)
    
    # Rest stays the same (stitching, DB updates, etc.)
    # ...
```

**Files to Review:**
- `backend/app/phases/phase4_chunks_storyboard/task.py` (main chunk generation logic)
- `backend/app/orchestrator/pipeline.py` (orchestrator with chain pattern)
- `backend/app/orchestrator/celery_app.py` (Celery configuration)

### Task 9.1: Investigate Current Phase 4 Implementation

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [x] Review current sequential chunk generation loop (found in `service.py` lines 156-221)
- [x] Identify how storyboard images are used vs last frames
  - **Storyboard images**: Used for chunks that START a beat (from `beat['image_url']`)
  - **Last frames**: Used for chunks that CONTINUE within same beat (from previous chunk's last frame)
- [x] Understand beat sequence structure (chunk pairs)
  - **Reference Image Chunk**: Chunk starting a beat, uses `beat['image_url']` from Phase 2
  - **Continuous Chunk**: Chunk continuing within beat, uses last frame from previous chunk
  - **Chunk Pair**: Reference image chunk → Continuous chunk (for beats spanning 2 chunks)
- [x] Document how beats are marked with storyboard images
  - Field: `beat['image_url']` contains S3 URL of storyboard image from Phase 2
  - Mapping: `beat_to_chunk_map` dictionary maps chunk indices → beat indices (which chunks start beats)
  - Example: `{0: 0, 2: 1, 4: 2}` means Chunk 0 starts Beat 0, Chunk 2 starts Beat 1, etc.
- [x] Trace how last frames are extracted and passed to next chunk
  - Extracted in `chunk_generator.py::extract_last_frame()` using FFmpeg
  - Stored in `last_frame_urls` list in service
  - Passed to next chunk via `chunk_spec.previous_chunk_last_frame` field
- [x] Confirm chunks are saved to DB with proper ordering
  - Chunks generated sequentially (in order), so ordering is automatic
  - No explicit DB save in chunk generation (happens in Phase 4 task.py after stitching)
- [x] Identify where chunks are currently generated in sequence
  - Location: `service.py` lines 156-221 (sequential for loop with `.apply()` calls)
  - Each chunk waits for previous to complete before starting next

### Task 9.2: Design Pipelined Chain Pattern

**Files:** `backend/app/phases/phase4_chunks_storyboard/task.py`, `backend/app/orchestrator/pipeline.py`

**Terminology Cleanup Required:**
- [ ] Rename terms in code comments/docstrings for consistency:
  - "Reference chunk" → "Reference Image Chunk" (to avoid confusion with Phase 3 reference images)
  - "Follower" → "Continuous Chunk" (matches existing code terminology)
  - Clarify: Reference Image = storyboard from Phase 2 (`beat['image_url']`)
  - Clarify: Continuous = uses last frame from previous chunk in same beat

**Design Tasks:**
- [ ] Design chunk pair identification logic using `beat_to_chunk_map`
  - Iterate through chunks, check if chunk is in `beat_to_chunk_map` (starts beat)
  - If next chunk is NOT in map, it's a continuous chunk (forms a pair)
  - Build chains dynamically: `chain(ref_image_chunk, continuous_chunk)` for pairs
- [ ] Design chain structure for chunk pairs:
  ```python
  # For beat spanning 2 chunks (e.g., 10s beat with 5s chunks):
  chain(
      generate_chunk_reference_image.s(chunk_spec_0),  # Uses beat['image_url']
      generate_chunk_continuous.s(chunk_spec_1)         # Receives last_frame_url from previous
  )
  ```
- [ ] Plan data flow between chain tasks:
  - Reference image task returns: `{'chunk_url': ..., 'last_frame_url': ..., 'chunk_num': ...}`
  - Continuous task receives this dict as first parameter via chain
  - Continuous task extracts `last_frame_url` and uses it for generation
- [ ] Design chord-of-chains structure for parallel execution:
  ```python
  chord(
      [chain1, chain2, chain3, ...]  # All chains run in parallel
  )(finalize_chunks.s())              # Callback collects results
  ```
- [ ] Plan handling of single-chunk beats (no continuous chunk):
  - Create single-task chain: `chain(generate_chunk_reference_image.s(chunk_spec))`
  - Still participates in chord with other chains
- [ ] Plan error handling:
  - Each chain is isolated - failure in one doesn't block others
  - Failed chains return error dict: `{'error': 'message', 'chunk_num': ...}`
  - Finalize callback checks for errors and reports them
- [ ] Design progress tracking:
  - Track completion of reference image chunks: X% of total progress
  - Track completion of continuous chunks: remaining % of total progress
  - Update progress in each task completion

**Key Design Decisions (RESOLVED):**
- ✅ Iterate through chunks (not beats), use `beat_to_chunk_map` to identify pairs
- ✅ Pass last frame via chain: first task returns dict with `last_frame_url`, second task receives it
- ✅ Collect results: finalize callback receives list of results (1 or 2 per chain), flattens and sorts
- ✅ Preserve ordering: finalize sorts by `chunk_num` before returning

### Task 9.3: Create Individual Chunk Generation Tasks

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

**Note:** These tasks will wrap existing functions from `chunk_generator.py`:
- `generate_single_chunk_with_storyboard()` - Already a Celery task, handles reference image chunks
- `generate_single_chunk_continuous()` - Currently a helper function, needs to be a Celery task

**Tasks:**

- [ ] Create `generate_chunk_reference_image` task (NEW Celery task in `task.py`)
  - **Purpose**: Generate chunk using storyboard image from Phase 2
  - **Input**: `chunk_spec` dict (ChunkSpec serialized), `beat_to_chunk_map` dict
  - **Process**:
    - Deserialize ChunkSpec
    - Verify `chunk_spec['style_guide_url']` has storyboard image URL (from `beat['image_url']`)
    - Call existing `generate_single_chunk_with_storyboard.apply()` from `chunk_generator.py`
    - Extract last frame from generated chunk (for potential continuous chunk)
    - Upload last frame to S3
  - **Return**: `{'chunk_url': str, 'last_frame_url': str, 'chunk_num': int, 'cost': float}`
  - **Error Handling**: Wrap in try/except, return error dict on failure

- [ ] Create `generate_chunk_continuous` task (NEW Celery task in `task.py`)
  - **Purpose**: Generate chunk using last frame from previous chunk
  - **Input**: `prev_result` dict (from chain - contains `last_frame_url`), `chunk_spec` dict
  - **Process**:
    - Extract `last_frame_url` from `prev_result` (passed by chain)
    - Update `chunk_spec['previous_chunk_last_frame']` with `last_frame_url`
    - Call existing `generate_single_chunk_continuous()` from `chunk_generator.py`
    - NOTE: May need to convert `generate_single_chunk_continuous()` to Celery task OR keep as helper
  - **Return**: **MUST return list containing BOTH chunks** (see Task 9.5 issue)
    ```python
    return [
        prev_result,  # Reference image chunk result (from chain input)
        {'chunk_url': str, 'chunk_num': int, 'cost': float}  # This continuous chunk
    ]
    ```
  - **Rationale**: Chains only return last task's result; to preserve reference chunk data, continuous task must include it
  - **Error Handling**: Wrap in try/except, return error dict on failure

- [ ] Decide: Should `generate_single_chunk_continuous()` be a separate Celery task?
  - **Option A**: Make it a Celery task, call it from `generate_chunk_continuous`
  - **Option B**: Keep it as helper function, call directly from `generate_chunk_continuous`
  - **Recommendation**: Option B (simpler, less overhead) UNLESS we need retry logic

- [ ] Ensure both tasks are idempotent:
  - Check if chunk already exists in S3 before generating
  - Use chunk_num to create unique S3 keys
  - Safe to retry on failure

- [ ] Add proper logging:
  - Log start of each chunk generation with chunk_num and type (reference/continuous)
  - Log completion with timing and cost
  - Log errors with full traceback

- [ ] Test chain data passing:
  - Verify `generate_chunk_continuous` receives `prev_result` as first parameter
  - Verify `last_frame_url` is correctly extracted and used

### Task 9.4: Create Phase 4 Parallel Orchestrator with Dynamic Chain Building

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

**Goal:** Create new `generate_chunks_parallel()` function that builds and executes chunk pairs in parallel using Celery chains and chord.

- [ ] Create `generate_chunks_parallel()` function (NEW - will replace sequential service call)
  - **Signature**: `def generate_chunks_parallel(phase3_output: dict, user_id: str, model: str) -> dict`
  - **Purpose**: Orchestrate parallel chunk generation using chains for chunk pairs
  - **Input**: Same as current `generate_chunks()` task
  - **Process**:
    1. Build chunk specs (reuse existing `build_chunk_specs_with_storyboard()`)
    2. Build `beat_to_chunk_map` (identifies which chunks start beats)
    3. Iterate through chunks, identify pairs using `beat_to_chunk_map`
    4. Build chains for each pair (or single chunk)
    5. Wrap chains in chord with finalize callback
    6. Return chord AsyncResult (let Celery wait for completion)
  - **Return**: PhaseOutput dict (same as current implementation)

- [ ] Implement chunk pair identification logic:
  ```python
  # Iterate through chunks, not beats
  # Use beat_to_chunk_map to identify which chunks start beats
  
  chains = []
  i = 0
  while i < len(chunk_specs):
      chunk_spec = chunk_specs[i]
      
      # Check if this chunk starts a beat (has storyboard image)
      if i in beat_to_chunk_map:
          # This is a reference image chunk
          chain_tasks = [generate_chunk_reference_image.s(chunk_spec.dict())]
          
          # Check if next chunk continues the same beat (no storyboard, continuous)
          if i + 1 < len(chunk_specs) and (i + 1) not in beat_to_chunk_map:
              # Next chunk is continuous (uses last frame from this chunk)
              next_spec = chunk_specs[i + 1]
              chain_tasks.append(generate_chunk_continuous.s(next_spec.dict()))
              i += 2  # Skip next chunk (included in this chain)
          else:
              # Beat only needs one chunk (single-chunk beat)
              i += 1
          
          chains.append(chain(*chain_tasks))
      else:
          # Error: chunk doesn't start a beat and wasn't paired with previous
          raise PhaseException(f"Chunk {i} is orphaned (no storyboard image and not paired)")
  ```

- [ ] Build chord structure:
  ```python
  # All chains run in parallel
  # Finalize callback collects results
  chord_result = chord(chains)(finalize_chunks.s(video_id, spec)).apply_async()
  
  # Wait for chord to complete (blocks until all chains finish)
  final_result = chord_result.get()
  
  # Continue with stitching (sequential, after all chunks complete)
  stitched_url = stitch_chunks(final_result['chunk_urls'])
  ```

- [ ] Handle edge cases:
  - All chunks have storyboard images (no continuous chunks): N single-task chains
  - Single chunk video: 1 single-task chain in chord
  - Mixed pairs and singles: Some 2-task chains, some 1-task chains

- [ ] Test chain building logic:
  - 2 chunks (1 pair): 1 chain with 2 tasks
  - 3 chunks (pair + single): 2 chains (1 with 2 tasks, 1 with 1 task)
  - 4 chunks (2 pairs): 2 chains, each with 2 tasks
  - 5 chunks (2 pairs + single): 3 chains

### Task 9.5: Create Finalize Callback

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

**Goal:** Create callback task that collects results from all parallel chains and prepares data for stitching.

- [ ] Create `finalize_chunks` Celery task (NEW task in `task.py`)
  - **Purpose**: Collect and merge chunk results from all parallel chains
  - **Signature**: `@celery_app.task def finalize_chunks(chain_results: list, video_id: str, spec: dict) -> dict`
  - **Input**: 
    - `chain_results`: List of results from chains (each chain returns 1 or 2 chunk dicts)
    - `video_id`: Video ID for logging
    - `spec`: Video spec (passed through for cost tracking)
  - **Process**:
    1. Flatten results (chains return different structures)
    2. Sort chunks by `chunk_num` to maintain order
    3. Extract chunk URLs in order
    4. Calculate total cost
    5. Check for errors
  - **Return**: `{'chunk_urls': [...], 'total_cost': float, 'chunk_results': [...]}`

- [ ] Handle result flattening logic:
  ```python
  all_chunks = []
  total_cost = 0.0
  
  for result in chain_results:
      # Each chain can return:
      # - Single dict (1-chunk chain): {'chunk_url': ..., 'chunk_num': ..., 'cost': ...}
      # - List of 2 dicts (2-chunk chain): [ref_result, continuous_result]
      #   (continuous task includes ref result - see Task 9.3)
      
      if isinstance(result, list):
          # 2-chunk chain: list of [ref_result, continuous_result]
          for chunk_result in result:
              if 'error' in chunk_result:
                  raise PhaseException(f"Chunk {chunk_result.get('chunk_num', '?')} failed: {chunk_result['error']}")
              all_chunks.append(chunk_result)
              total_cost += chunk_result.get('cost', 0.0)
      elif isinstance(result, dict):
          # 1-chunk chain: single dict
          if 'error' in result:
              raise PhaseException(f"Chunk {result.get('chunk_num', '?')} failed: {result['error']}")
          all_chunks.append(result)
          total_cost += result.get('cost', 0.0)
      else:
          raise PhaseException(f"Unexpected result format: {type(result)}")
  
  # Sort by chunk_num to maintain order
  all_chunks.sort(key=lambda x: x['chunk_num'])
  
  # Extract URLs in order
  chunk_urls = [chunk['chunk_url'] for chunk in all_chunks]
  ```

- [ ] **RESOLVED**: Chain return value issue
  - Solution: Continuous task returns list `[prev_result, current_result]` (see Task 9.3)
  - Single-chunk chains return dict
  - 2-chunk chains return list
  - Finalize handles both formats

- [ ] Error handling:
  - Check each result for 'error' key
  - Raise PhaseException if any chunk failed
  - Include chunk_num in error message for debugging

- [ ] Logging:
  - Log total chunks collected
  - Log total cost
  - Log chunk order verification
  - Log any warnings about missing chunks

### Task 9.6: Update Main Task to Use Parallel Generation

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

**Goal:** Update the main `generate_chunks()` Celery task to call `generate_chunks_parallel()` instead of sequential service.

- [ ] Update `generate_chunks()` task:
  - Keep same signature: `generate_chunks(self, phase3_output: dict, user_id: str, model: str)`
  - Replace call to `chunk_service.generate_all_chunks()` with call to `generate_chunks_parallel()`
  - Maintain same error handling and progress tracking
  - Keep same PhaseOutput return structure
  - Keep same database updates

- [ ] Implementation:
  ```python
  @celery_app.task(bind=True, name="app.phases.phase4_chunks_storyboard.task.generate_chunks")
  def generate_chunks(self, phase3_output: dict, user_id: str, model: str) -> dict:
      # ... validation and setup (same as before) ...
      
      try:
          # Update progress
          update_progress(video_id, "generating_chunks", 50, current_phase="phase4_chunks")
          
          # NEW: Call parallel generation instead of sequential service
          chunk_results = generate_chunks_parallel(
              video_id=video_id,
              spec=spec,
              reference_urls=reference_urls,
              user_id=user_id
          )
          
          # Rest of task remains the same (stitching, DB updates, etc.)
          # ...
      except Exception as e:
          # ... error handling (same as before) ...
  ```

- [ ] No changes needed to:
  - `pipeline.py` orchestrator (already calls `generate_chunks` task)
  - Phase 4 task signature or registration
  - Progress tracking infrastructure
  - Database schema or models

- [ ] Verify backward compatibility:
  - Same inputs (phase3_output, user_id, model)
  - Same outputs (PhaseOutput dict with stitched_video_url, chunk_urls, cost)
  - Same error handling (PhaseException on failure)
  - Same progress updates

### Task 9.7: Handle Edge Cases

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

- [ ] Handle case where all chunks have storyboard images (all single-chunk beats)
  - Result: N single-task chains (one per chunk)
  - No continuous chunks
  - Each chain returns single dict (not list)
  - Finalize correctly handles N single dicts

- [ ] Handle orphaned continuous chunk (no storyboard image and not paired)
  - Detection: Chunk index not in `beat_to_chunk_map` and is chunk 0, OR previous chunk was also continuous
  - Action: Raise PhaseException with clear message
  - Message: "Chunk {i} is orphaned (no storyboard image and not part of a pair)"
  - Indicates: Phase 1 or Phase 2 data corruption

- [ ] Handle single chunk video (1 beat, short duration)
  - Result: 1 single-task chain
  - Chord with single chain works fine (Celery handles this)
  - Finalize receives list with 1 result

- [ ] Handle mixed pattern (some beats need 1 chunk, some need 2)
  - Example: 5s + 10s + 5s beats with 5s chunks = [chunk0 (single), chunk1+chunk2 (pair), chunk3 (single)]
  - Result: 3 chains (2 single-task, 1 double-task)
  - Finalize receives: [dict, list, dict]
  - Correctly flattens to 4 chunks

- [ ] Ensure chunk_num ordering is preserved:
  - Sort by `chunk_num` (not beat_index) in finalize_chunks
  - `chunk_num` directly maps to video timeline position
  - Validation: Check for gaps in chunk_num sequence

### Task 9.8: Update Progress Tracking

**Files:** `backend/app/orchestrator/progress.py`, `backend/app/phases/phase4_chunks_storyboard/task.py`

**Goal:** Add progress tracking to parallel chunk generation tasks.

- [ ] Update progress in `generate_chunk_reference_image` task:
  - After chunk generation completes
  - Calculate: `50 + (completed_reference_chunks / total_reference_chunks) * 10`
  - Range: 50% → 60% for all reference chunks
  - Call: `update_progress(video_id, "generating_chunks", progress, current_phase="phase4_chunks")`

- [ ] Update progress in `generate_chunk_continuous` task:
  - After chunk generation completes
  - Calculate: `60 + (completed_continuous_chunks / total_continuous_chunks) * 10`
  - Range: 60% → 70% for all continuous chunks
  - Call: `update_progress(video_id, "generating_chunks", progress, current_phase="phase4_chunks")`

- [ ] Challenge: How to track global completion counts in distributed tasks?
  - **Option A**: Use Redis counter (increment on each completion)
  - **Option B**: Skip per-chunk progress, only track phase start/end
  - **Option C**: Use Celery task state tracking
  - **Recommended**: Option B (simpler, good enough for v1)

- [ ] Simplified progress tracking (Option B):
  - Phase 4 start: 50% (in main `generate_chunks` task)
  - Chunk generation: 50-70% (no per-chunk updates)
  - After chord completes: 70% (in finalize or after chord.get())
  - After stitching: 90% (existing code)
  - Phase complete: Keep existing

- [ ] Log completion events (instead of progress):
  - Log when each reference chunk completes
  - Log when each continuous chunk completes
  - Include chunk_num, timing, cost in logs
  - Logs provide visibility without complex progress tracking

### Task 9.9: Testing and Verification

**Goal:** Test parallel chunk generation with various beat configurations and verify correctness.

**Test Scenarios (Based on Chunks, Not Beats):**

- [ ] Test with 2 chunks (10s beat): 1 pair = 1 chain with 2 tasks
  - Spec: 1 beat (10s duration), model outputs 5s chunks → 2 chunks needed
  - Expected: 1 chain = `[ref_image_chunk_0, continuous_chunk_1]`
  - Verify: Continuous chunk uses last frame from chunk 0
  - Verify: Final result has 2 chunks in order

- [ ] Test with 3 chunks (5s + 10s beats): 1 single + 1 pair = 2 chains
  - Spec: Beat 0 (5s) + Beat 1 (10s), 5s chunks → 3 chunks (chunk0, chunk1, chunk2)
  - Expected: Chain 0 = `[ref_chunk_0]`, Chain 1 = `[ref_chunk_1, cont_chunk_2]`
  - Verify: Chunk 1 starts Beat 1 (uses storyboard), Chunk 2 continues Beat 1 (uses last frame)
  - Verify: Final result has 3 chunks in order

- [ ] Test with 4 chunks (2x 10s beats): 2 pairs = 2 chains
  - Spec: 2 beats (10s each), 5s chunks → 4 chunks
  - Expected: Chain 0 = `[ref_0, cont_1]`, Chain 1 = `[ref_2, cont_3]`
  - Verify: Both chains run in parallel
  - Verify: Chunk 3 doesn't wait for Chunk 1 to complete

- [ ] Test with 3 single-chunk beats: 3 singles = 3 chains
  - Spec: 3 beats (5s each), 5s chunks → 3 chunks
  - Expected: 3 single-task chains, all run in parallel
  - Verify: No continuous chunks (all use storyboard images)
  - Verify: Finalize receives 3 dicts (not lists)

- [ ] Test with single chunk (short video): 1 single = 1 chain
  - Spec: 1 beat (5s), 5s chunks → 1 chunk
  - Expected: 1 single-task chain
  - Verify: Chord with single chain works
  - Verify: No errors or edge case issues

**Functional Verification:**

- [ ] Verify chunk ordering:
  - After finalize, chunks sorted by chunk_num (0, 1, 2, ...)
  - chunk_urls list matches chunk order
  - No missing chunks (validate chunk_num sequence)

- [ ] Verify storyboard image usage:
  - Reference image chunks use `beat['image_url']` from Phase 2
  - Continuous chunks use last frame from previous chunk
  - Check S3 for last_frame images (should exist for reference chunks with followers)

- [ ] Verify parallel execution (timing test):
  - Generate 4-chunk video (2 pairs)
  - Measure time for parallel vs sequential (use existing sequential code for comparison)
  - Expected: Parallel should be ~40-50% faster for 2 pairs (both pairs start together)
  - Log timestamps to verify pairs execute simultaneously

- [ ] Verify continuous chunks start immediately:
  - In 2-pair scenario, verify Chunk 3 starts when Chunk 2 completes
  - Chunk 3 should NOT wait for Chunk 1 to complete
  - Check log timestamps to confirm

**Error Handling:**

- [ ] Test reference chunk failure:
  - Simulate failure in reference chunk (e.g., invalid storyboard URL)
  - Verify: Chain fails, finalize receives error dict
  - Verify: Other chains continue and complete successfully
  - Verify: Phase 4 reports partial failure

- [ ] Test continuous chunk failure:
  - Simulate failure in continuous chunk (e.g., invalid last frame)
  - Verify: Chain fails after reference succeeds
  - Verify: Reference chunk's work is not lost
  - Verify: Other chains continue

- [ ] Test orphaned chunk detection:
  - Manually create invalid beat_to_chunk_map (chunk not in map, not paired)
  - Verify: PhaseException raised with clear message
  - Verify: Error message includes chunk number

**Integration Testing:**

- [ ] Test full pipeline with parallel chunks:
  - Run Phase 1 → 2 → 3 → 4 (parallel) → 5 → 6
  - Verify: Final video has correct number of chunks
  - Verify: Chunks stitch correctly (no gaps/overlaps)
  - Verify: Total cost matches sum of individual chunk costs

- [ ] Test concurrent video generations:
  - Start 3 videos simultaneously
  - Verify: All 3 videos generate chunks in parallel
  - Verify: No resource contention or deadlocks
  - Verify: All 3 videos complete successfully

**Performance Comparison:**

- [ ] Measure sequential vs parallel for 4-chunk video:
  - Sequential: ~X minutes (current implementation)
  - Parallel: ~Y minutes (new implementation)
  - Expected improvement: 40-50% faster
  - Document: Timing results in PR description

**Key Implementation Notes:**
1. **Chord blocks on `.get()`** - `generate_chunks_parallel()` calls `chord_result.get()` to wait for completion
2. **Chain data passing** - continuous task receives reference result as first parameter from chain
3. **Chunk ordering** - sort by `chunk_num` in finalize callback (not beat_index)
4. **Last frame extraction** - happens in reference task, passed via chain to continuous task
5. **Error isolation** - failure in one chain doesn't block other chains (chord collects all results)
6. **Dynamic structure** - `generate_chunks_parallel()` builds chains at runtime based on `beat_to_chunk_map`
7. **Return value preservation** - continuous task returns list `[ref_result, cont_result]` to preserve both chunks

---

## PR #9 SUMMARY: Terminology & Implementation Plan

### Confirmed Terminology (Code-First):
| Term | Meaning | Field/Structure |
|------|---------|-----------------|
| **Reference Image Chunk** | Chunk that starts a beat | Uses `beat['image_url']` from Phase 2 |
| **Continuous Chunk** | Chunk within same beat | Uses last frame from previous chunk |
| **Chunk Pair** | Ref + Continuous | For 10s beats (2 chunks) |
| **Single-Chunk Beat** | Independent chunk | For 5s beats (1 chunk) |
| **beat_to_chunk_map** | Chunk→Beat mapping | `{0: 0, 2: 1}` = Chunk 0 starts Beat 0, Chunk 2 starts Beat 1 |

### New Functions (All in `task.py`):
1. `generate_chunk_reference_image()` - Celery task, wraps existing storyboard generation
2. `generate_chunk_continuous()` - Celery task, wraps existing continuous generation
3. `generate_chunks_parallel()` - Main orchestrator, builds and executes chains
4. `finalize_chunks()` - Celery task callback, collects and sorts results

### NO Changes To:
- `pipeline.py` (still calls `generate_chunks` task)
- `chunk_generator.py` (existing functions reused)
- Database schema or models
- External API (Phase 4 inputs/outputs unchanged)

### Key Design Decisions:
- ✅ Iterate through chunks (not beats) using `beat_to_chunk_map`
- ✅ Max 2 chunks per chain (pairs only, no 3+ chunk chains in this PR)
- ✅ Continuous task returns list `[ref_result, cont_result]` to preserve both
- ✅ Simplified progress: 50% start, 70% after chord, 90% after stitch
- ✅ Chord blocks on `.get()` in `generate_chunks_parallel()`, then continues to stitching

### Ready to Implement:
All terminology cleaned up, tasks updated, design documented. Ready to proceed with Task 9.3 (Create Individual Chunk Generation Tasks).

---