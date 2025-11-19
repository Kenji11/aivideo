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

## PR #9: Parallel Chunk Generation with LangChain RunnableParallel

**Goal:** Enable parallel chunk generation using LangChain's RunnableParallel for I/O-bound Replicate API calls, while keeping Celery for overall pipeline orchestration

**TERMINOLOGY (Code-First Approach):**
- **Reference Image Chunk**: Chunk that starts a beat, uses storyboard image from Phase 2 (`beat['image_url']`)
- **Continuous Chunk**: Chunk that continues within same beat, uses last frame from previous chunk
- **Chunk Pair**: Reference image chunk + Continuous chunk (for beats spanning 2 chunks)
- **Single-Chunk Beat**: Beat that fits in one chunk (5s beat with 5s chunks)
- **beat_to_chunk_map**: Dictionary mapping chunk indices → beat indices (identifies which chunks start beats)

**SCOPE LIMITATIONS:**
- Beats can span 1 or 2 chunks only (5s or 10s beats with 5s chunks)
- No 15s+ beats in this PR (would need 3+ chunk parallelization)
- Two-phase execution: Reference chunks first (parallel), then continuous chunks (parallel)

**TECHNOLOGY STACK:**
- **LangChain RunnableParallel**: For parallel chunk generation (I/O-bound, thread-safe)
- **Celery**: Still used for overall pipeline (Phases 1-6), NOT for chunk parallelism
- **Threads/Async**: LangChain uses threads/async under the hood for I/O-bound API calls

**NEW FUNCTIONS (Added to `task.py`):**
- `generate_chunk_reference_image()` - Helper function for reference image chunks
- `generate_chunk_continuous()` - Helper function for continuous chunks
- `generate_chunks_parallel()` - Main orchestrator using LangChain RunnableParallel

**NEW DEPENDENCY:**
- `langchain-core` - For RunnableParallel (lightweight, no full LangChain needed)

**NO NEW FILES** - All changes in existing files

**Current Issue:**
- Phase 4 generates chunks sequentially in `service.py` (slow)
- Reference image chunks are independent and could run in parallel
- Continuous chunks must wait for their reference chunk, but could start immediately when ready
- Current sequential approach wastes time: Chunk 3 waits for Chunk 1 to complete even though they're independent

**The Solution:**
- Use **LangChain RunnableParallel** for two-phase parallel execution:
  1. **Phase 1**: Run all reference image chunks in parallel (independent, can all start together)
  2. **Phase 2**: Run all continuous chunks in parallel (each uses last_frame from its reference chunk)
- No complex Celery chain logic - simple parallel execution within single Celery task
- LangChain handles threading/async for I/O-bound Replicate API calls
- Main orchestrator (`generate_chunks_parallel()`) builds RunnableParallel dynamically based on `beat_to_chunk_map`

**Benefits:**
- **Maximum parallelism**: All reference image chunks start together, all continuous chunks start together after Phase 1
- **Simpler than Celery chains**: No chain/chord complexity, just parallel function calls
- **Thread-safe for I/O**: LangChain uses threads/async for I/O-bound operations (Replicate API calls)
- **Faster completion**: Parallel execution reduces total time significantly
- **Keep Celery for pipeline**: Still use Celery for Phases 1-6 orchestration, only use LangChain for chunk parallelism
- **No extra infrastructure**: Runs in same process/worker, no additional workers needed

**Execution Pattern Example:**
```
4 chunks from 2 beats: [Beat 0: 10s, Beat 1: 10s] with 5s chunks
Chunks: [0-ref, 1-cont, 2-ref, 3-cont]

Two-Phase Parallel Execution:
- Phase 1 (Parallel): Chunk 0 (ref image) || Chunk 2 (ref image)
- Phase 2 (Parallel): Chunk 1 (continuous, uses Chunk 0's last_frame) || Chunk 3 (continuous, uses Chunk 2's last_frame)

Timeline:
0s:  [Chunk 0] [Chunk 2]  ← Phase 1: Both reference image chunks start in parallel (RunnableParallel)
5s:  [✓ Chunk 0 done] [✓ Chunk 2 done]  ← Both complete, extract last frames
5s:  [Chunk 1] [Chunk 3]  ← Phase 2: Both continuous chunks start in parallel (RunnableParallel)
10s: [✓ Chunk 1 done] [✓ Chunk 3 done]  ← All chunks complete

Sequential would be: Chunk 0 → Chunk 1 → Chunk 2 → Chunk 3 (15s+)
Parallel is: (Chunk 0 || Chunk 2) → (Chunk 1 || Chunk 3) (~10s, 33% faster)
```

**LangChain RunnableParallel Pattern Example:**
```python
from langchain_core.runnables import RunnableParallel
from app.phases.phase4_chunks_storyboard.chunk_generator import (
    generate_single_chunk_with_storyboard,
    generate_single_chunk_continuous
)
from app.phases.phase4_chunks_storyboard.schemas import ChunkSpec

# Helper functions (in task.py)
def generate_chunk_reference_image(chunk_spec: ChunkSpec, beat_to_chunk_map: dict) -> dict:
    """Generate chunk using storyboard image from Phase 2."""
    # Call existing generator function (synchronous, will be called in parallel)
    chunk_result = generate_single_chunk_with_storyboard(
        chunk_spec.dict(),
        beat_to_chunk_map
    )
    
    return {
        'chunk_url': chunk_result['chunk_url'],
        'last_frame_url': chunk_result['last_frame_url'],
        'chunk_num': chunk_spec.chunk_num,
        'cost': chunk_result['cost']
    }

def generate_chunk_continuous(chunk_spec: ChunkSpec, ref_result: dict) -> dict:
    """Generate chunk using last frame from reference chunk."""
    # Update chunk spec with last frame from reference chunk
    chunk_spec.previous_chunk_last_frame = ref_result['last_frame_url']
    
    # Call existing generator function (synchronous, will be called in parallel)
    result = generate_single_chunk_continuous(chunk_spec)
    
    return {
        'chunk_url': result['chunk_url'],
        'chunk_num': chunk_spec.chunk_num,
        'cost': result['cost']
    }

# Phase 4 parallel orchestrator (in task.py)
def generate_chunks_parallel(video_id: str, spec: dict, reference_urls: dict, user_id: str) -> dict:
    """Generate chunks in parallel using LangChain RunnableParallel."""
    from app.phases.phase4_chunks_storyboard.chunk_generator import build_chunk_specs_with_storyboard
    
    # Build chunk specs and beat_to_chunk_map
    chunk_specs, beat_to_chunk_map = build_chunk_specs_with_storyboard(
        video_id, spec, reference_urls, user_id
    )
    
    # Separate reference and continuous chunks
    ref_chunks = []  # List of (chunk_spec, chunk_num) tuples
    cont_chunks = []  # List of (chunk_spec, ref_chunk_num) tuples
    
    for i, chunk_spec in enumerate(chunk_specs):
        if i in beat_to_chunk_map:
            # Reference image chunk
            ref_chunks.append((chunk_spec, i))
        else:
            # Continuous chunk - find its reference chunk (previous chunk in same beat)
            # Find the reference chunk that this continuous chunk belongs to
            ref_chunk_num = None
            for j in range(i - 1, -1, -1):
                if j in beat_to_chunk_map:
                    ref_chunk_num = j
                    break
            
            if ref_chunk_num is None:
                raise PhaseException(f"Chunk {i} is orphaned (no reference chunk found)")
            
            cont_chunks.append((chunk_spec, ref_chunk_num))
    
    # Phase 1: Generate all reference image chunks in parallel
    if ref_chunks:
        # Build RunnableParallel dict with proper closure capture
        ref_parallel_dict = {}
        for chunk_spec, chunk_num in ref_chunks:
            # Create closure to capture chunk_spec and chunk_num
            def make_ref_generator(cs, cn):
                return lambda x: generate_chunk_reference_image(cs, beat_to_chunk_map)
            
            ref_parallel_dict[f'chunk_{chunk_num}'] = make_ref_generator(chunk_spec, chunk_num)
        
        ref_parallel = RunnableParallel(ref_parallel_dict)
        
        # Invoke parallel execution (blocks until all complete)
        ref_results = ref_parallel.invoke({})
        
        # Convert results to dict keyed by chunk_num
        ref_results_by_num = {}
        for key, result in ref_results.items():
            chunk_num = int(key.split('_')[1])
            ref_results_by_num[chunk_num] = result
    else:
        ref_results_by_num = {}
    
    # Phase 2: Generate all continuous chunks in parallel
    if cont_chunks:
        # Build RunnableParallel dict with proper closure capture
        cont_parallel_dict = {}
        for chunk_spec, ref_chunk_num in cont_chunks:
            # Create closure to capture chunk_spec and ref_chunk_num
            def make_cont_generator(cs, ref_num):
                return lambda x: generate_chunk_continuous(cs, ref_results_by_num[ref_num])
            
            cont_parallel_dict[f'chunk_{chunk_spec.chunk_num}'] = make_cont_generator(chunk_spec, ref_chunk_num)
        
        cont_parallel = RunnableParallel(cont_parallel_dict)
        
        # Invoke parallel execution (blocks until all complete)
        cont_results = cont_parallel.invoke({})
        
        # Convert results to dict keyed by chunk_num
        cont_results_by_num = {}
        for key, result in cont_results.items():
            chunk_num = int(key.split('_')[1])
            cont_results_by_num[chunk_num] = result
    else:
        cont_results_by_num = {}
    
    # Merge and sort all chunks by chunk_num
    all_chunks = []
    all_chunks.extend(ref_results_by_num.values())
    all_chunks.extend(cont_results_by_num.values())
    all_chunks.sort(key=lambda x: x['chunk_num'])
    
    # Extract URLs and calculate total cost
    chunk_urls = [chunk['chunk_url'] for chunk in all_chunks]
    total_cost = sum(chunk['cost'] for chunk in all_chunks)
    
    return {
        'chunk_urls': chunk_urls,
        'total_cost': total_cost
    }

# Main Phase 4 task (in task.py) - NO CHANGE to external interface
@celery_app.task(bind=True, name="app.phases.phase4_chunks_storyboard.task.generate_chunks")
def generate_chunks(self, phase3_output: dict, user_id: str, model: str) -> dict:
    # ... validation (same as before) ...
    
    try:
        # Update progress
        update_progress(video_id, "generating_chunks", 50, current_phase="phase4_chunks")
        
        # NEW: Call parallel generation using LangChain
        chunk_results = generate_chunks_parallel(
            video_id=video_id,
            spec=spec,
            reference_urls=reference_urls,
            user_id=user_id
        )
        
        # Rest stays the same (stitching, DB updates, etc.)
        # ...
```

**Files to Review:**
- `backend/app/phases/phase4_chunks_storyboard/task.py` (main chunk generation logic)
- `backend/app/orchestrator/pipeline.py` (orchestrator with chain pattern)
- `backend/app/orchestrator/celery_app.py` (Celery configuration)

### Task 9.0: Refactor Celery Tasks - Remove Task Decorators from Chunk Generation Functions

**Goal:** Convert all chunk generation functions from Celery tasks to regular functions, except `generate_chunks` which must remain a Celery task (called from pipeline chain).

**Rationale:** Since we're using LangChain RunnableParallel for parallelism within a single Celery task, individual chunk generation functions should NOT be Celery tasks. This avoids nested task calls and the "Never call result.get() within a task!" violation.

**Files to Modify:**
- `backend/app/phases/phase4_chunks_storyboard/chunk_generator.py`
- `backend/app/phases/phase4_chunks_storyboard/service.py`
- `backend/app/phases/phase4_chunks_storyboard/task.py` (if any helper functions are tasks)

**Tasks:**

- [ ] **Task 9.0.1: Identify All Celery Tasks in Phase 4**
  - Search for all `@celery_app.task` decorators in `phase4_chunks_storyboard/` directory
  - List all functions that are currently Celery tasks
  - Verify that `generate_chunks` in `task.py` is the ONLY function that should remain a Celery task
  - Document which functions need to be converted

- [ ] **Task 9.0.2: Convert `generate_single_chunk_with_storyboard` to Regular Function**
  - **File:** `backend/app/phases/phase4_chunks_storyboard/chunk_generator.py`
  - Remove `@celery_app.task(bind=True, ...)` decorator
  - Remove `self` parameter (first parameter)
  - Change signature from `def generate_single_chunk_with_storyboard(self, chunk_spec: dict, beat_to_chunk_map: dict = None)` to `def generate_single_chunk_with_storyboard(chunk_spec: dict, beat_to_chunk_map: dict = None)`
  - Keep all function logic exactly the same
  - Update docstring to remove references to Celery task

- [ ] **Task 9.0.3: Update All Callers of `generate_single_chunk_with_storyboard`**
  - **File:** `backend/app/phases/phase4_chunks_storyboard/service.py`
  - Find all calls using `.apply()` or `.apply().get()`
  - Replace with direct function calls
  - Change `generate_single_chunk_with_storyboard.apply(args=[...])` to `generate_single_chunk_with_storyboard(...)`
  - Change `result.result` access to direct return value
  - Update error handling if needed (direct calls raise exceptions, not task failures)

- [ ] **Task 9.0.4: Verify `generate_single_chunk_continuous` is Already Regular Function**
  - **File:** `backend/app/phases/phase4_chunks_storyboard/chunk_generator.py`
  - Confirm it does NOT have `@celery_app.task` decorator
  - Verify it can be called directly (no `.apply()` needed)
  - If it's a task, convert it following Task 9.0.2 pattern

- [ ] **Task 9.0.5: Check for Other Celery Tasks in Phase 4**
  - Search for any other `@celery_app.task` decorators in phase 4 files
  - Verify none are needed for LangChain parallel execution
  - Convert any found tasks to regular functions (except `generate_chunks`)

- [ ] **Task 9.0.6: Update Imports and Dependencies**
  - Remove any Celery-related imports that are no longer needed in `chunk_generator.py`
  - Ensure `celery_app` import is only in `task.py` (for `generate_chunks`)
  - Verify all imports are correct after refactoring

- [ ] **Task 9.0.7: Test Direct Function Calls**
  - Verify functions can be called directly without Celery task overhead
  - Test that function signatures match expected inputs/outputs
  - Ensure no breaking changes to function interfaces

**Expected Outcome:**
- Only `generate_chunks` in `task.py` remains a Celery task
- All chunk generation functions (`generate_single_chunk_with_storyboard`, `generate_single_chunk_continuous`, etc.) are regular functions
- All callers use direct function calls (no `.apply()` or `.get()`)
- Ready for LangChain RunnableParallel integration (functions can be called directly in parallel)

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

### Task 9.2: Design LangChain RunnableParallel Pattern

**Files:** `backend/app/phases/phase4_chunks_storyboard/task.py`

**Terminology Cleanup Required:**
- [ ] Rename terms in code comments/docstrings for consistency:
  - "Reference chunk" → "Reference Image Chunk" (to avoid confusion with Phase 3 reference images)
  - "Follower" → "Continuous Chunk" (matches existing code terminology)
  - Clarify: Reference Image = storyboard from Phase 2 (`beat['image_url']`)
  - Clarify: Continuous = uses last frame from previous chunk in same beat

**Design Tasks:**
- [ ] Design two-phase parallel execution:
  - **Phase 1**: Separate reference image chunks from continuous chunks using `beat_to_chunk_map`
  - **Phase 2**: After Phase 1 completes, run continuous chunks in parallel (each uses its reference chunk's last_frame)
- [ ] Design chunk separation logic:
  - Iterate through chunks, check if chunk is in `beat_to_chunk_map` (starts beat)
  - Reference chunks: All chunks where `i in beat_to_chunk_map`
  - Continuous chunks: All chunks where `i not in beat_to_chunk_map` (find their reference chunk by looking backwards)
- [ ] Design RunnableParallel structure for Phase 1:
  ```python
  ref_parallel = RunnableParallel({
      f'chunk_{chunk_num}': lambda x: generate_chunk_reference_image(chunk_spec, beat_to_chunk_map)
      for chunk_spec, chunk_num in ref_chunks
  })
  ref_results = ref_parallel.invoke({})  # Blocks until all complete
  ```
- [ ] Design RunnableParallel structure for Phase 2:
  ```python
  cont_parallel = RunnableParallel({
      f'chunk_{chunk_num}': lambda x: generate_chunk_continuous(chunk_spec, ref_results_by_num[ref_chunk_num])
      for chunk_spec, ref_chunk_num in cont_chunks
  })
  cont_results = cont_parallel.invoke({})  # Blocks until all complete
  ```
- [ ] Plan data flow between phases:
  - Phase 1 returns: Dict of `{chunk_num: {'chunk_url': ..., 'last_frame_url': ..., 'cost': ...}}`
  - Phase 2 uses: `ref_results_by_num[ref_chunk_num]['last_frame_url']` for each continuous chunk
  - Phase 2 returns: Dict of `{chunk_num: {'chunk_url': ..., 'cost': ...}}`
- [ ] Plan result merging:
  - Merge `ref_results_by_num` and `cont_results_by_num` into single list
  - Sort by `chunk_num` to maintain order
  - Extract `chunk_urls` and calculate `total_cost`
- [ ] Plan error handling:
  - Wrap each phase in try/except
  - If Phase 1 fails, Phase 2 cannot proceed (raise PhaseException)
  - If Phase 2 fails partially, log errors but continue with successful chunks
  - Return error dicts for failed chunks: `{'error': 'message', 'chunk_num': ...}`
- [ ] Plan progress tracking:
  - Phase 1 start: 50% progress
  - Phase 1 complete: 60% progress
  - Phase 2 complete: 70% progress
  - After stitching: 90% progress (existing)

**Key Design Decisions (RESOLVED):**
- ✅ Two-phase execution: Reference chunks first (parallel), then continuous chunks (parallel)
- ✅ No Celery chains needed - LangChain handles parallelism within single Celery task
- ✅ Helper functions (not Celery tasks) - called synchronously but executed in parallel by RunnableParallel
- ✅ Closure capture: Use factory functions to properly capture variables in lambda closures
- ✅ Preserve ordering: Sort merged results by `chunk_num` before returning

### Task 9.3: Create Helper Functions for Chunk Generation

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

**Note:** These are helper functions (NOT Celery tasks) that will be called by LangChain RunnableParallel:
- `generate_single_chunk_with_storyboard()` - Existing Celery task in `chunk_generator.py`, call synchronously
- `generate_single_chunk_continuous()` - Existing helper function in `chunk_generator.py`, call directly

**Tasks:**

- [ ] Create `generate_chunk_reference_image` helper function (NEW in `task.py`)
  - **Purpose**: Generate chunk using storyboard image from Phase 2
  - **Signature**: `def generate_chunk_reference_image(chunk_spec: ChunkSpec, beat_to_chunk_map: dict) -> dict`
  - **Process**:
    - Call existing `generate_single_chunk_with_storyboard()` from `chunk_generator.py`
    - NOTE: This is a Celery task, but we'll call it synchronously (`.get()` result)
    - OR: Extract the core logic and call it directly (avoid Celery overhead)
    - Extract last frame from generated chunk (already done in `generate_single_chunk_with_storyboard`)
    - Return structured dict with chunk metadata
  - **Return**: `{'chunk_url': str, 'last_frame_url': str, 'chunk_num': int, 'cost': float}`
  - **Error Handling**: Wrap in try/except, raise PhaseException on failure (RunnableParallel will catch)

- [ ] Create `generate_chunk_continuous` helper function (NEW in `task.py`)
  - **Purpose**: Generate chunk using last frame from reference chunk
  - **Signature**: `def generate_chunk_continuous(chunk_spec: ChunkSpec, ref_result: dict) -> dict`
  - **Process**:
    - Extract `last_frame_url` from `ref_result` (passed from Phase 1 results)
    - Update `chunk_spec.previous_chunk_last_frame` with `last_frame_url`
    - Call existing `generate_single_chunk_continuous()` from `chunk_generator.py` directly
    - Return structured dict with chunk metadata
  - **Return**: `{'chunk_url': str, 'chunk_num': int, 'cost': float}` (no last_frame_url needed)
  - **Error Handling**: Wrap in try/except, raise PhaseException on failure

- [ ] Handle Celery task synchronization:
  - `generate_single_chunk_with_storyboard` is a Celery task
  - Options:
    1. Call `.apply()` and `.get()` result (synchronous, blocks)
    2. Extract core logic to separate function (better, avoids Celery overhead)
  - **Recommendation**: Option 2 - create wrapper that calls core logic directly
  - If keeping Celery: Use `.apply().get()` to get result synchronously

- [ ] Ensure both functions are thread-safe:
  - No shared mutable state between parallel calls
  - Each function operates on its own chunk_spec
  - S3 uploads are thread-safe (boto3 handles this)
  - Replicate API calls are stateless

- [ ] Add proper logging:
  - Log start of each chunk generation with chunk_num and type (reference/continuous)
  - Log completion with timing and cost
  - Log errors with full traceback
  - Use thread-safe logging (Python's logging module is thread-safe)

- [ ] Test function signatures:
  - Verify `generate_chunk_reference_image` takes ChunkSpec and beat_to_chunk_map
  - Verify `generate_chunk_continuous` takes ChunkSpec and ref_result dict
  - Verify return types match expected structure

### Task 9.4: Create Phase 4 Parallel Orchestrator with LangChain RunnableParallel

**File:** `backend/app/phases/phase4_chunks_storyboard/task.py`

**Goal:** Create new `generate_chunks_parallel()` function that builds and executes chunks in parallel using LangChain RunnableParallel (two-phase execution).

- [ ] Create `generate_chunks_parallel()` function (NEW - will replace sequential service call)
  - **Signature**: `def generate_chunks_parallel(video_id: str, spec: dict, reference_urls: dict, user_id: str) -> dict`
  - **Purpose**: Orchestrate two-phase parallel chunk generation using LangChain RunnableParallel
  - **Input**: video_id, spec, reference_urls, user_id (extracted from phase3_output in main task)
  - **Process**:
    1. Build chunk specs using `build_chunk_specs_with_storyboard()` (reuse existing)
    2. Get `beat_to_chunk_map` from build function
    3. Separate reference chunks from continuous chunks
    4. Phase 1: Build RunnableParallel for all reference chunks, execute in parallel
    5. Phase 2: Build RunnableParallel for all continuous chunks, execute in parallel
    6. Merge and sort results by chunk_num
    7. Return dict with chunk_urls and total_cost
  - **Return**: `{'chunk_urls': List[str], 'total_cost': float}`

- [ ] Implement chunk separation logic:
  ```python
  # Separate reference and continuous chunks
  ref_chunks = []  # List of (chunk_spec, chunk_num) tuples
  cont_chunks = []  # List of (chunk_spec, ref_chunk_num) tuples
  
  for i, chunk_spec in enumerate(chunk_specs):
      if i in beat_to_chunk_map:
          # Reference image chunk
          ref_chunks.append((chunk_spec, i))
      else:
          # Continuous chunk - find its reference chunk (look backwards)
          ref_chunk_num = None
          for j in range(i - 1, -1, -1):
              if j in beat_to_chunk_map:
                  ref_chunk_num = j
                  break
          
          if ref_chunk_num is None:
              raise PhaseException(f"Chunk {i} is orphaned (no reference chunk found)")
          
          cont_chunks.append((chunk_spec, ref_chunk_num))
  ```

- [ ] Build Phase 1 RunnableParallel (reference chunks):
  ```python
  from langchain_core.runnables import RunnableParallel
  
  # Build dict with proper closure capture
  ref_parallel_dict = {}
  for chunk_spec, chunk_num in ref_chunks:
      def make_ref_generator(cs, cn):
          return lambda x: generate_chunk_reference_image(cs, beat_to_chunk_map)
      ref_parallel_dict[f'chunk_{chunk_num}'] = make_ref_generator(chunk_spec, chunk_num)
  
  ref_parallel = RunnableParallel(ref_parallel_dict)
  ref_results = ref_parallel.invoke({})  # Blocks until all complete
  
  # Convert to dict keyed by chunk_num
  ref_results_by_num = {int(k.split('_')[1]): v for k, v in ref_results.items()}
  ```

- [ ] Build Phase 2 RunnableParallel (continuous chunks):
  ```python
  # Build dict with proper closure capture
  cont_parallel_dict = {}
  for chunk_spec, ref_chunk_num in cont_chunks:
      def make_cont_generator(cs, ref_num):
          return lambda x: generate_chunk_continuous(cs, ref_results_by_num[ref_num])
      cont_parallel_dict[f'chunk_{chunk_spec.chunk_num}'] = make_cont_generator(chunk_spec, ref_chunk_num)
  
  cont_parallel = RunnableParallel(cont_parallel_dict)
  cont_results = cont_parallel.invoke({})  # Blocks until all complete
  
  # Convert to dict keyed by chunk_num
  cont_results_by_num = {int(k.split('_')[1]): v for k, v in cont_results.items()}
  ```

- [ ] Merge and sort results:
  ```python
  all_chunks = []
  all_chunks.extend(ref_results_by_num.values())
  all_chunks.extend(cont_results_by_num.values())
  all_chunks.sort(key=lambda x: x['chunk_num'])
  
  chunk_urls = [chunk['chunk_url'] for chunk in all_chunks]
  total_cost = sum(chunk['cost'] for chunk in all_chunks)
  
  return {'chunk_urls': chunk_urls, 'total_cost': total_cost}
  ```

- [ ] Handle edge cases:
  - All chunks are reference (no continuous): Phase 1 only, Phase 2 skipped
  - Single chunk video: Phase 1 with 1 chunk, Phase 2 skipped
  - Mixed: Some reference chunks, some continuous chunks (both phases run)

- [ ] Test parallel execution:
  - 2 chunks (1 pair): Phase 1 (1 ref), Phase 2 (1 cont)
  - 3 chunks (pair + single): Phase 1 (2 refs), Phase 2 (1 cont)
  - 4 chunks (2 pairs): Phase 1 (2 refs), Phase 2 (2 conts)
  - 5 chunks (2 pairs + single): Phase 1 (3 refs), Phase 2 (2 conts)

**Note:** With LangChain RunnableParallel, we merge results directly in `generate_chunks_parallel()` - no separate callback task needed. Results are merged and sorted in the same function after both phases complete.

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
1. **Two-phase execution** - Phase 1: all reference chunks in parallel, Phase 2: all continuous chunks in parallel
2. **LangChain RunnableParallel** - Uses threads/async for I/O-bound Replicate API calls (thread-safe)
3. **Chunk ordering** - Sort by `chunk_num` after merging Phase 1 and Phase 2 results
4. **Last frame passing** - Phase 2 uses `ref_results_by_num[ref_chunk_num]['last_frame_url']` from Phase 1
5. **Error handling** - Wrap each phase in try/except, raise PhaseException on failure
6. **Dynamic structure** - `generate_chunks_parallel()` separates chunks at runtime based on `beat_to_chunk_map`
7. **No Celery chains** - All parallelism handled by LangChain within single Celery task
8. **Closure capture** - Use factory functions to properly capture variables in lambda closures

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
1. `generate_chunk_reference_image()` - Helper function, wraps existing storyboard generation
2. `generate_chunk_continuous()` - Helper function, wraps existing continuous generation
3. `generate_chunks_parallel()` - Main orchestrator using LangChain RunnableParallel (two-phase execution)

### New Dependency:
- `langchain-core` - For RunnableParallel (lightweight, no full LangChain needed)

### NO Changes To:
- `pipeline.py` (still calls `generate_chunks` Celery task)
- `chunk_generator.py` (existing functions reused)
- Database schema or models
- External API (Phase 4 inputs/outputs unchanged)
- Celery infrastructure (still used for pipeline orchestration)

### Key Design Decisions:
- ✅ Two-phase execution: Reference chunks first (parallel), then continuous chunks (parallel)
- ✅ LangChain RunnableParallel for I/O-bound operations (thread-safe, no Celery chains needed)
- ✅ Helper functions (not Celery tasks) - called synchronously but executed in parallel
- ✅ Iterate through chunks (not beats) using `beat_to_chunk_map` to separate reference/continuous
- ✅ Simplified progress: 50% start, 60% after Phase 1, 70% after Phase 2, 90% after stitch
- ✅ Closure capture: Use factory functions to properly capture variables in lambda closures

### Ready to Implement:
All terminology cleaned up, tasks updated, design documented. Ready to proceed with Task 9.3 (Create Individual Chunk Generation Tasks).