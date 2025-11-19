## PR #11: Phase Cleanup and Renaming

**Goal:** Remove unused phases and rename remaining phases to create a cleaner, sequential phase structure

**OVERVIEW:**

### Current Problem:
- **Unused Phases**: Multiple phases exist that are no longer used in the pipeline:
  - `phase6_export` - Not referenced in pipeline
  - `phase2_animatic` - Replaced by `phase2_storyboard`
  - `phase3_references` - No longer used in pipeline
  - `phase4_chunks` - Replaced by `phase4_chunks_storyboard`
- **Inconsistent Naming**: Phase numbering is non-sequential after removals
- **Code Clutter**: Unused code increases maintenance burden and confusion

### Solution:
1. **Remove Unused Phases**:
   - Delete `phase6_export` directory and all references
   - Delete `phase2_animatic` directory and all references
   - Delete `phase3_references` directory and all references
   - Delete `phase4_chunks` directory and all references (old phase 4)

2. **Rename Remaining Phases**:
   - Rename `phase4_chunks_storyboard` → `phase3`
   - Rename `phase5_refine` → `phase4`

3. **Update All References**:
   - Update imports in `pipeline.py`
   - Update imports in `celery_app.py`
   - Update phase names in progress tracking
   - Update phase names in status builder
   - Update phase names in all task files
   - Update phase output keys in database models
   - Update test files

**Benefits:**
- **Cleaner Codebase**: Remove ~50% of unused phase code
- **Sequential Naming**: Phases now numbered 1-4 sequentially
- **Easier Maintenance**: Less code to maintain and understand
- **Clearer Architecture**: Only active phases remain

**Scope:**
- ✅ Remove phase6_export directory and all references
- ✅ Remove phase2_animatic directory and all references
- ✅ Remove phase3_references directory and all references
- ✅ Remove phase4_chunks directory and all references
- ✅ Rename phase4_chunks_storyboard to phase3
- ✅ Rename phase5_refine to phase4
- ✅ Update all imports and references
- ✅ Update pipeline chain
- ✅ Update progress tracking phase names
- ✅ Update status builder phase output keys
- ✅ Update test files

**Files to Modify:**
- `backend/app/phases/` (delete 4 directories, rename 2 directories)
- `backend/app/orchestrator/pipeline.py` (update imports and chain)
- `backend/app/orchestrator/celery_app.py` (remove phase imports)
- `backend/app/orchestrator/progress.py` (update phase names)
- `backend/app/services/status_builder.py` (update phase output keys)
- `backend/app/api/video.py` (update phase output keys)
- `backend/app/tests/` (update test imports and references)

---

### Task 11.1: Remove phase6_export

**Goal:** Delete phase6_export directory and all references to it

- [ ] Search for all references to `phase6` or `phase6_export`:
  - Check `backend/app/orchestrator/pipeline.py`
  - Check `backend/app/orchestrator/celery_app.py`
  - Check `backend/app/orchestrator/progress.py`
  - Check `backend/app/services/status_builder.py`
  - Check `backend/app/api/` files
  - Check `backend/app/tests/` files
  - Check any other files that might reference it

- [ ] Remove all references:
  - Remove imports
  - Remove phase output key references
  - Remove any phase name strings
  - Remove from Celery task registration

- [ ] Delete directory:
  - Delete `backend/app/phases/phase6_export/` directory and all contents

- [ ] Verify removal:
  - Run `grep -r "phase6" backend/` to ensure no references remain
  - Verify pipeline still works without phase6

---

### Task 11.2: Remove phase2_animatic

**Goal:** Delete phase2_animatic directory and all references to it (replaced by phase2_storyboard)

- [ ] Search for all references to `phase2_animatic`:
  - Check `backend/app/orchestrator/pipeline.py`
  - Check `backend/app/orchestrator/celery_app.py`
  - Check `backend/app/orchestrator/progress.py`
  - Check `backend/app/services/status_builder.py` (has fallback: `phase_outputs.get('phase2_storyboard') or phase_outputs.get('phase2_animatic')`)
  - Check `backend/app/api/` files
  - Check `backend/app/tests/` files (test_phase2, test_integration)

- [ ] Remove all references:
  - Remove imports from `pipeline.py`
  - Remove imports from `celery_app.py`
  - Remove fallback logic in `status_builder.py` (only use `phase2_storyboard`)
  - Remove test imports and test cases
  - Remove from Celery task registration

- [ ] Delete directory:
  - Delete `backend/app/phases/phase2_animatic/` directory and all contents

- [ ] Verify removal:
  - Run `grep -r "phase2_animatic" backend/` to ensure no references remain
  - Verify pipeline still works (should only use phase2_storyboard)

---

### Task 11.3: Remove phase3_references

**Goal:** Delete phase3_references directory and all references to it (no longer used in pipeline)

- [ ] Search for all references to `phase3_references`:
  - Check `backend/app/orchestrator/pipeline.py` (imports and chain)
  - Check `backend/app/orchestrator/celery_app.py`
  - Check `backend/app/orchestrator/progress.py`
  - Check `backend/app/services/status_builder.py`
  - Check `backend/app/api/` files
  - Check `backend/app/tests/test_phase3/` directory

- [ ] Remove from pipeline:
  - Remove import: `from app.phases.phase3_references.task import generate_references`
  - Remove from chain: `generate_references.s(user_id),` (line 92)
  - Update chain to go directly from phase2_storyboard to phase4_chunks_storyboard

- [ ] Remove all other references:
  - Remove imports from `celery_app.py`
  - Remove phase output key references in `status_builder.py`
  - Remove test files in `backend/app/tests/test_phase3/`
  - Remove from Celery task registration

- [ ] Delete directory:
  - Delete `backend/app/phases/phase3_references/` directory and all contents

- [ ] Verify removal:
  - Run `grep -r "phase3_references" backend/` to ensure no references remain
  - Verify pipeline chain works (phase2 → phase4 directly)

---

### Task 11.4: Remove old phase4_chunks

**Goal:** Delete phase4_chunks directory and all references to it (replaced by phase4_chunks_storyboard)

- [ ] Search for all references to `phase4_chunks` (but NOT `phase4_chunks_storyboard`):
  - Check `backend/app/orchestrator/pipeline.py`
  - Check `backend/app/orchestrator/celery_app.py` (has import and registration)
  - Check `backend/app/orchestrator/progress.py` (has phase4_chunks progress tracking)
  - Check `backend/app/services/status_builder.py` (has phase4_output references)
  - Check `backend/app/api/video.py` (has phase4_output reference)
  - Check `backend/app/tests/` files

- [ ] Remove all references:
  - Remove imports from `celery_app.py`
  - Remove from Celery task registration
  - Note: Keep progress tracking for `phase4_chunks` key (will be updated in rename task)
  - Note: Keep status builder references (will be updated in rename task)

- [ ] Delete directory:
  - Delete `backend/app/phases/phase4_chunks/` directory and all contents

- [ ] Verify removal:
  - Run `grep -r "from app.phases.phase4_chunks" backend/` to ensure no imports remain
  - Run `grep -r "app.phases.phase4_chunks.task" backend/` to ensure no task references remain
  - Verify pipeline still works (should only use phase4_chunks_storyboard)

---

### Task 11.5: Rename phase4_chunks_storyboard to phase3

**Goal:** Rename directory and update all references from `phase4_chunks_storyboard` to `phase3`

- [ ] Rename directory:
  - Rename `backend/app/phases/phase4_chunks_storyboard/` → `backend/app/phases/phase3/`

- [ ] Update all imports:
  - `backend/app/orchestrator/pipeline.py`: 
    - Change: `from app.phases.phase4_chunks_storyboard.task import generate_chunks as generate_chunks_storyboard`
    - To: `from app.phases.phase3.task import generate_chunks`
    - Update chain call: `generate_chunks_storyboard.s(user_id, model)` → `generate_chunks.s(user_id, model)`

- [ ] Update internal imports in phase3 files:
  - Update all `from app.phases.phase4_chunks_storyboard.*` imports to `from app.phases.phase3.*`
  - Files to check:
    - `phase3/task.py`
    - `phase3/service.py`
    - `phase3/chunk_generator.py`
    - `phase3/model_config.py`
    - `phase3/schemas.py`
    - `phase3/stitcher.py`

- [ ] Update Celery task names:
  - In `phase3/task.py`: Update `@celery_app.task(bind=True, name="app.phases.phase4_chunks_storyboard.task.generate_chunks")`
  - To: `@celery_app.task(bind=True, name="app.phases.phase3.task.generate_chunks")`
  - Update any other Celery task decorators in phase3 files

- [ ] Update phase names in progress tracking:
  - In `phase3/task.py`: Update all `current_phase="phase4_chunks"` → `current_phase="phase3"`
  - In `phase3/task.py`: Update all `phase="phase4_chunks_storyboard"` → `phase="phase3"`
  - In `phase3/service.py`: Update all `current_phase="phase4_chunks"` → `current_phase="phase3"`

- [ ] Update phase output keys:
  - In `phase3/task.py`: Update `video.phase_outputs['phase4_chunks']` → `video.phase_outputs['phase3']`
  - In `backend/app/orchestrator/progress.py`: Update `phase_outputs["phase4_chunks"]` → `phase_outputs["phase3"]`
  - In `backend/app/services/status_builder.py`: Update `phase_outputs.get('phase4_chunks')` → `phase_outputs.get('phase3')`
  - In `backend/app/api/video.py`: Update `video.phase_outputs.get('phase4_chunks')` → `video.phase_outputs.get('phase3')`

- [ ] Update celery_app.py:
  - Remove old import/registration for phase4_chunks_storyboard
  - Add new import/registration for phase3:
    ```python
    from app.phases.phase3 import task as phase3_task  # noqa: F401
    logger.info("✓ Imported app.phases.phase3.task")
    ```

- [ ] Verify rename:
  - Run `grep -r "phase4_chunks_storyboard" backend/` to ensure no references remain
  - Run `grep -r "phase4_chunks" backend/` to ensure only old references are gone (new phase3 should use "phase3")
  - Verify pipeline chain works with new phase3

---

### Task 11.6: Rename phase5_refine to phase4

**Goal:** Rename directory and update all references from `phase5_refine` to `phase4`

- [ ] Rename directory:
  - Rename `backend/app/phases/phase5_refine/` → `backend/app/phases/phase4/`

- [ ] Update all imports:
  - `backend/app/orchestrator/pipeline.py`: 
    - Change: `from app.phases.phase5_refine.task import refine_video`
    - To: `from app.phases.phase4.task import refine_video`
    - Chain call stays the same: `refine_video.s(user_id)`

- [ ] Update internal imports in phase4 files:
  - Update all `from app.phases.phase5_refine.*` imports to `from app.phases.phase4.*`
  - Files to check:
    - `phase4/task.py`
    - `phase4/service.py`
    - `phase4/model_config.py`
    - `phase4/music_generator.py`
    - `phase4/schemas.py`

- [ ] Update Celery task names:
  - In `phase4/task.py`: Update `@celery_app.task(bind=True, name="app.phases.phase5_refine.task.refine_video")`
  - To: `@celery_app.task(bind=True, name="app.phases.phase4.task.refine_video")`

- [ ] Update phase names in progress tracking:
  - In `phase4/task.py`: Update all `current_phase="phase5_refine"` → `current_phase="phase4"`
  - In `phase4/task.py`: Update all `phase="phase5_refine"` → `phase="phase4"`
  - In `phase4/task.py`: Update reference to previous phase: `video.current_phase = "phase4_chunks"` → `video.current_phase = "phase3"`

- [ ] Update phase output keys:
  - In `phase4/task.py`: Update `video.phase_outputs['phase5_refine']` → `video.phase_outputs['phase4']`
  - In `backend/app/services/status_builder.py`: Update `phase_outputs.get('phase5_refine')` → `phase_outputs.get('phase4')`

- [ ] Update celery_app.py:
  - Remove old import/registration for phase5_refine
  - Add new import/registration for phase4:
    ```python
    from app.phases.phase4 import task as phase4_task  # noqa: F401
    logger.info("✓ Imported app.phases.phase4.task")
    ```

- [ ] Verify rename:
  - Run `grep -r "phase5_refine" backend/` to ensure no references remain
  - Verify pipeline chain works with new phase4

---

### Task 11.7: Update Pipeline Chain

**Goal:** Update pipeline.py to reflect new phase structure (1 → 2 → 3 → 4)

- [ ] Review current chain in `backend/app/orchestrator/pipeline.py`:
  - Current: phase1 → phase2_storyboard → phase3_references → phase4_chunks_storyboard → phase5_refine
  - New: phase1 → phase2_storyboard → phase3 → phase4

- [ ] Update chain:
  ```python
  workflow = chain(
      # Phase 1: Validate prompt and extract spec
      validate_prompt.s(video_id, prompt, assets),
      
      # Phase 2: Generate storyboard images (receives Phase 1 output)
      generate_storyboard.s(user_id),
      
      # Phase 3: Generate chunks and stitch (receives Phase 2 output)
      generate_chunks.s(user_id, model),
      
      # Phase 4: Refine video with music (receives Phase 3 output)
      refine_video.s(user_id)
  )
  ```

- [ ] Update comments:
  - Update phase comments to reflect new numbering
  - Remove comment about phase3_references skipping

- [ ] Verify chain:
  - Test pipeline execution with new chain
  - Verify each phase receives correct input from previous phase

---

### Task 11.8: Update Progress Tracking

**Goal:** Update progress.py to use new phase names

- [ ] Review `backend/app/orchestrator/progress.py`:
  - Check for any hardcoded phase names
  - Check for phase output key references

- [ ] Update phase output keys:
  - Update `phase_outputs["phase4_chunks"]` → `phase_outputs["phase3"]` (if still exists after rename)
  - Ensure all phase names match new structure

- [ ] Update phase name strings:
  - Update any hardcoded phase name strings to match new structure

- [ ] Verify:
  - Run `grep -r "phase[456]" backend/app/orchestrator/progress.py` to check for old references
  - Test progress tracking with new phase names

---

### Task 11.9: Update Status Builder

**Goal:** Update status_builder.py to use new phase output keys

- [ ] Review `backend/app/services/status_builder.py`:
  - Check all `phase_outputs.get()` calls
  - Check all `video.phase_outputs.get()` calls

- [ ] Update phase output keys:
  - Update `phase_outputs.get('phase3_references')` → Remove (no longer exists)
  - Update `phase_outputs.get('phase4_chunks')` → `phase_outputs.get('phase3')`
  - Update `phase_outputs.get('phase5_refine')` → `phase_outputs.get('phase4')`
  - Update `phase_outputs.get('phase2_animatic')` → Remove fallback (only use phase2_storyboard)

- [ ] Update video.phase_outputs references:
  - Same updates as above for `video.phase_outputs.get()` calls

- [ ] Verify:
  - Run `grep -r "phase[3456]" backend/app/services/status_builder.py` to check for old references
  - Test status endpoint with new phase structure

---

### Task 11.10: Update API Endpoints

**Goal:** Update API endpoints to use new phase output keys

- [ ] Review `backend/app/api/video.py`:
  - Check for phase output key references

- [ ] Update phase output keys:
  - Update `video.phase_outputs.get('phase4_chunks')` → `video.phase_outputs.get('phase3')`

- [ ] Verify:
  - Run `grep -r "phase[456]" backend/app/api/` to check for old references
  - Test API endpoints with new phase structure

---

### Task 11.11: Update Test Files

**Goal:** Update or remove test files for deleted/renamed phases

- [ ] Remove test files for deleted phases:
  - Delete `backend/app/tests/test_phase2/test_prompts.py` (if it tests phase2_animatic)
  - Delete `backend/app/tests/test_phase3/` directory (phase3_references tests)
  - Check `backend/app/tests/test_integration/test_phase1_and_2.py` for phase2_animatic references

- [ ] Update test imports:
  - Update any imports from deleted phases
  - Update imports from renamed phases:
    - `from app.phases.phase4_chunks_storyboard.*` → `from app.phases.phase3.*`
    - `from app.phases.phase5_refine.*` → `from app.phases.phase4.*`

- [ ] Update test phase names:
  - Update any hardcoded phase names in tests
  - Update phase output key assertions

- [ ] Verify:
  - Run tests to ensure they pass with new structure
  - Remove any broken tests for deleted phases

---

### Task 11.12: Final Verification and Testing

**Goal:** Comprehensive testing of the cleaned-up phase structure

- [ ] Verify directory structure:
  - Check `backend/app/phases/` contains only:
    - `phase1_validate/`
    - `phase2_storyboard/`
    - `phase3/` (renamed from phase4_chunks_storyboard)
    - `phase4/` (renamed from phase5_refine)

- [ ] Verify no old references:
  - Run `grep -r "phase2_animatic" backend/` → Should return nothing
  - Run `grep -r "phase3_references" backend/` → Should return nothing
  - Run `grep -r "phase4_chunks[^_]" backend/` → Should return nothing (only phase4_chunks_storyboard if rename failed)
  - Run `grep -r "phase5_refine" backend/` → Should return nothing
  - Run `grep -r "phase6" backend/` → Should return nothing

- [ ] Verify new phase structure:
  - Run `grep -r "from app.phases.phase3" backend/` → Should show imports
  - Run `grep -r "from app.phases.phase4" backend/` → Should show imports
  - Verify phase3 is phase4_chunks_storyboard renamed
  - Verify phase4 is phase5_refine renamed

- [ ] Test pipeline execution:
  - Create a test video generation
  - Verify pipeline chain: phase1 → phase2 → phase3 → phase4
  - Verify each phase completes successfully
  - Verify phase outputs are stored with correct keys

- [ ] Test status endpoint:
  - Check status endpoint returns correct phase information
  - Verify phase output keys match new structure

- [ ] Test progress tracking:
  - Verify progress updates use correct phase names
  - Verify phase transitions work correctly

- [ ] Run all tests:
  - Run test suite to ensure nothing is broken
  - Fix any failing tests related to phase changes

---

**Key Implementation Notes:**
1. **Phase Structure**: Final structure is phase1 → phase2 → phase3 → phase4 (sequential, clean)
2. **Phase Names**: Use consistent naming: `phase1_validate`, `phase2_storyboard`, `phase3`, `phase4`
3. **Phase Output Keys**: Use `phase1_validate`, `phase2_storyboard`, `phase3`, `phase4` in phase_outputs dict
4. **Current Phase**: Use `phase1_validate`, `phase2_storyboard`, `phase3`, `phase4` for current_phase field
5. **Backward Compatibility**: Old videos in DB may have old phase output keys - status builder should handle gracefully
6. **Testing**: Comprehensive testing required to ensure pipeline works end-to-end after cleanup

