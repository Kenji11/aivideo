# TDD Implementation Tasks - Part 1: Foundation & Beat Library

**Goal:** Set up project foundation, beat library, and template archetypes

---

## PR #1: Project Structure & Constants

### Task 1.1: Create Beat Library Module

**File:** `backend/app/common/beat_library.py`

- [x] Create `beat_library.py` file
- [x] Define `OPENING_BEATS` dictionary with 5 beats:
  - [x] `hero_shot` (5s, close_up, product_reveal)
  - [x] `ambient_lifestyle` (5s, wide, establish_environment)
  - [x] `teaser_reveal` (5s, extreme_close_up, mysterious_preview)
  - [x] `dynamic_intro` (5s, dynamic, energetic_opening)
  - [x] `atmospheric_setup` (5s, wide, mood_establishment)
- [x] Define `MIDDLE_PRODUCT_BEATS` dictionary with 5 beats:
  - [x] `detail_showcase` (5s, macro, feature_highlight)
  - [x] `product_in_motion` (5s, tracking, dynamic_product)
  - [x] `usage_scenario` (10s, medium, person_using_product)
  - [x] `lifestyle_context` (10s, medium, aspirational_lifestyle)
  - [x] `feature_highlight_sequence` (10s, medium_close_up, multiple_features)
- [x] Define `MIDDLE_DYNAMIC_BEATS` dictionary with 3 beats:
  - [x] `action_montage` (5s, dynamic_multi, fast_energy)
  - [x] `benefit_showcase` (5s, medium, demonstrate_benefit)
  - [x] `transformation_moment` (10s, medium_wide, before_after)
- [x] Define `CLOSING_BEATS` dictionary with 2 beats:
  - [x] `call_to_action` (5s, close_up, final_impression)
  - [x] `brand_moment` (10s, wide_cinematic, brand_story)
- [x] Create `BEAT_LIBRARY` by merging all beat dictionaries
- [x] Verify total of 15 beats in library

### Task 1.2: Create Template Archetypes Module

**File:** `backend/app/common/template_archetypes.py`

- [x] Create `template_archetypes.py` file
- [x] Define `luxury_showcase` archetype:
  - [x] Set typical_duration_range: (15, 30)
  - [x] Set suggested_beat_sequence: hero_shot, detail_showcase, lifestyle_context, call_to_action
  - [x] Set typical_products: watches, jewelry, luxury_cars, high_end_fashion, premium_tech
  - [x] Set style_hints: elegant, sophisticated, premium, minimalist, cinematic
  - [x] Set energy_curve: "steady"
  - [x] Set narrative_structure: "reveal → appreciate → aspire → desire"
- [x] Define `energetic_lifestyle` archetype:
  - [x] Set typical_duration_range: (10, 20)
  - [x] Set suggested_beat_sequence: dynamic_intro, action_montage, product_in_motion, call_to_action
  - [x] Set typical_products: sportswear, sneakers, fitness_equipment, energy_drinks, outdoor_gear
  - [x] Set style_hints: energetic, vibrant, dynamic, authentic, motivational
  - [x] Set energy_curve: "building"
  - [x] Set narrative_structure: "excite → engage → empower → inspire"
- [x] Define `minimalist_reveal` archetype:
  - [x] Set typical_duration_range: (10, 20)
  - [x] Set suggested_beat_sequence: hero_shot, detail_showcase, call_to_action
  - [x] Set typical_products: tech_gadgets, design_objects, skincare, minimal_fashion, smart_devices
  - [x] Set style_hints: minimalist, clean, modern, simple, focused
  - [x] Set energy_curve: "steady"
  - [x] Set narrative_structure: "reveal → appreciate → conclude"
- [x] Define `emotional_storytelling` archetype:
  - [x] Set typical_duration_range: (20, 30)
  - [x] Set suggested_beat_sequence: atmospheric_setup, usage_scenario, transformation_moment, call_to_action
  - [x] Set typical_products: family_products, healthcare, home_goods, insurance, nonprofits
  - [x] Set style_hints: emotional, authentic, warm, human, heartfelt
  - [x] Set energy_curve: "building"
  - [x] Set narrative_structure: "relate → connect → transform → remember"
- [x] Define `feature_demo` archetype:
  - [x] Set typical_duration_range: (15, 30)
  - [x] Set suggested_beat_sequence: hero_shot, feature_highlight_sequence, benefit_showcase, call_to_action
  - [x] Set typical_products: tech_products, appliances, software, tools, automotive
  - [x] Set style_hints: informative, clear, professional, modern, benefit-driven
  - [x] Set energy_curve: "steady"
  - [x] Set narrative_structure: "introduce → demonstrate → explain → convince"
- [x] Create `TEMPLATE_ARCHETYPES` dictionary with all 5 archetypes

### Task 1.3: Update Constants

**File:** `backend/app/common/constants.py`

- [x] Add `BEAT_COMPOSITION_CREATIVITY` constant (default 0.5, from env var)
- [x] Add `get_planning_temperature(creativity: float) -> float` function
- [x] Implement temperature mapping: 0.2 + (creativity * 0.6)
- [x] Add comment explaining temperature ranges:
  - [x] 0.0 → 0.2 (strict template adherence)
  - [x] 0.5 → 0.5 (balanced adaptation)
  - [x] 1.0 → 0.8 (creative reinterpretation)

### Task 1.4: Update Database Models

**File:** `backend/app/common/models.py`

- [x] Add `storyboard_images` column (JSON, default list)
- [x] Note: `creativity_level`, `selected_archetype`, `num_beats`, `num_chunks` stored in `spec` JSON
- [x] Note: Keep existing `VideoStatus` enum unchanged (out of scope)

### Task 1.5: Create Database Migration

**File:** `backend/alembic/versions/003_add_storyboard_images.py`

- [x] Create new migration file `003_add_storyboard_images.py`
- [x] Set revision ID: `003_add_storyboard_images`
- [x] Set down_revision: `002_add_final_music_url`
- [x] In `upgrade()`: Add `storyboard_images` column (JSON, nullable=True, default=list)
- [x] In `downgrade()`: Remove `storyboard_images` column
- [x] Test migration: `alembic upgrade head`
- [x] Verify column exists in database

---

## PR #2: Phase 1 Structure & Validation

### Task 2.1: Create Phase 1 Directory Structure

- [x] Use existing directory `backend/app/phases/phase1_validate/`
- [x] Keep existing `__init__.py`, `task.py`, `service.py`, `schemas.py`
- [x] Create `prompts.py` in phase1_validate (for system prompt)
- [x] Create `validation.py` in phase1_validate

### Task 2.2: Implement System Prompt Builder

**File:** `backend/app/phases/phase1_validate/prompts.py`

- [x] Import `BEAT_LIBRARY` from common
- [x] Import `TEMPLATE_ARCHETYPES` from common
- [x] Import `json` module
- [x] Create `build_planning_system_prompt() -> str` function
- [x] Add archetype description section in prompt
- [x] Add beat library description section in prompt
- [x] Add task instructions (4 steps: understand, select, compose, style)
- [x] Add critical constraints section:
  - [x] Total duration must equal user's request
  - [x] Each beat must be 5s, 10s, or 15s
  - [x] First beat from opening beats
  - [x] Last beat from closing beats
  - [x] Sum of durations must equal total
- [x] Add JSON output format specification
- [x] Add validation checklist section
- [x] Return complete system prompt string

### Task 2.3: Implement Spec Validation

**File:** `backend/app/phases/phase1_validate/validation.py`

- [x] Import `BEAT_LIBRARY` from common
- [x] Import `logging`
- [x] Create logger instance
- [x] Create `validate_spec(spec: dict) -> None` function
- [x] Check beat durations sum to total duration
- [x] Raise ValueError if sum doesn't match
- [x] Check all beat durations are 5, 10, or 15 seconds
- [x] Raise ValueError if invalid duration found
- [x] Check all beat_ids exist in BEAT_LIBRARY
- [x] Raise ValueError if unknown beat_id found
- [x] Check at least one beat exists
- [x] Raise ValueError if no beats
- [x] Add warnings (not errors) for:
  - [x] First beat not from opening beats
  - [x] Last beat not from closing beats
- [x] Log success message when validation passes

### Task 2.4: Implement Spec Builder

**File:** `backend/app/phases/phase1_validate/validation.py` (continued)

- [x] Create `build_full_spec(llm_output: dict, video_id: str) -> dict` function
- [x] Extract `intent_analysis` from LLM output
- [x] Extract `beat_sequence` from LLM output
- [x] Extract `style` from LLM output
- [x] Initialize `current_time = 0`
- [x] Initialize empty `full_beats` list
- [x] Loop through beat_sequence:
  - [x] Get beat_id and duration
  - [x] Validate beat_id exists in BEAT_LIBRARY
  - [x] Get beat_template from library
  - [x] Copy all fields from template
  - [x] Set `start` to current_time
  - [x] Set `duration` from beat_sequence
  - [x] Fill in prompt_template with product name and style
  - [x] Append to full_beats
  - [x] Increment current_time
- [x] Build final spec dictionary with:
  - [x] template, duration, fps, resolution
  - [x] product, style, beats
  - [x] llm_reasoning section
- [x] Return spec

---

## PR #3: Phase 1 LLM Agent Implementation

### Task 3.1: Implement Main Phase 1 Task

**File:** `backend/app/phases/phase1_validate/task_intelligent.py`

- [x] Import celery_app
- [x] Import PhaseOutput from common.schemas
- [x] Import openai_client from services
- [x] Import build_planning_system_prompt from .prompts
- [x] Import validate_spec, build_full_spec from .validation
- [x] Import BEAT_COMPOSITION_CREATIVITY, get_planning_temperature from constants
- [x] Import json, time, logging
- [x] Create logger instance
- [x] Create `@celery_app.task(bind=True)` decorator
- [x] Define `plan_video_intelligent(self, video_id, prompt, creativity_level=None)` function
- [x] Add docstring with Args and Returns
- [x] Record start_time
- [x] Set creativity_level to config default if None
- [x] Log start message with video_id, prompt, creativity_level

### Task 3.2: Implement LLM Call Logic

**File:** `backend/app/phases/phase1_validate/task_intelligent.py` (continued)

- [x] Wrap main logic in try/except block
- [x] Call `build_planning_system_prompt()` to get system prompt
- [x] Build user_message: "Create a video advertisement: {prompt}"
- [x] Calculate temperature using `get_planning_temperature(creativity_level)`
- [x] Log temperature being used
- [x] Call `openai_client.chat.completions.create` with:
  - [x] model="gpt-4-turbo-preview"
  - [x] messages=[system, user]
  - [x] response_format={"type": "json_object"}
  - [x] temperature=calculated_temperature
- [x] Parse response as JSON
- [x] Log selected archetype
- [x] Log number of beats composed

### Task 3.3: Implement Success/Failure Paths

**File:** `backend/app/phases/phase1_validate/task_intelligent.py` (continued)

- [x] Call `build_full_spec(llm_output, video_id)`
- [x] Call `validate_spec(spec)`
- [x] Log completion message
- [x] Create PhaseOutput with:
  - [x] video_id
  - [x] phase="phase1_planning"
  - [x] status="success"
  - [x] output_data={"spec": spec}
  - [x] cost_usd=0.02
  - [x] duration_seconds
  - [x] error_message=None
- [x] Return output.dict()
- [x] In except block:
  - [x] Log error with video_id
  - [x] Create PhaseOutput with status="failed"
  - [x] Set error_message=str(e)
  - [x] cost_usd=0.0
  - [x] Return output.dict()

---

## ✅ PR #1, #2, #3 Complete Checklist

All tasks completed:
- [x] Beat library has exactly 15 beats
- [x] All beat durations are 5, 10, or 15 seconds
- [x] Template archetypes has exactly 5 archetypes
- [x] Creativity constants added to constants.py
- [x] Database model updated with storyboard_images
- [x] Migration created and executed successfully
- [x] Phase 1 task imports without errors
- [x] System prompt generates without errors (13,831 characters)
- [x] Spec validation catches invalid durations
- [x] Spec validation catches unknown beat_ids
- [x] Test script created and working (scripts/test_phase1_intelligent.py)

---

## 📋 Database Migration Plan (Execute LAST)

**Migration File:** `backend/alembic/versions/003_tdd_beat_based_architecture.py`

### Fields to ADD:
```python
# Add to VideoGeneration model
storyboard_images = Column(JSON, default=list, nullable=True)
```

### Fields Stored in `spec` JSON (No DB columns needed):
- `creativity_level` - User creativity setting (0.0-1.0)
- `selected_archetype` - Which template archetype was chosen
- `num_beats` - Number of beats in composition
- `num_chunks` - Number of video chunks
- All beat-specific data (beat_id, duration, prompt, etc.)

### Fields to KEEP (Do NOT Remove):
- `animatic_urls` - Keep for backward compat with existing videos
- `chunk_urls` - Still used
- `stitched_url` - Still used
- `refined_url` - Still used
- `final_video_url` - Still used
- `final_music_url` - Still used
- `spec` - JSON column, handles format changes automatically
- `template` - Keep, now stores archetype_id
- All other existing fields

### Migration Tasks:
- [ ] Create migration file after all TDD PRs complete
- [ ] Add `storyboard_images` column with nullable=True (backward compat)
- [ ] Test migration on development database
- [ ] Verify existing videos still accessible
- [ ] Run migration on production
- [ ] Update model file (`common/models.py`)
- [ ] Update schemas if needed

### Backward Compatibility Strategy:
- **Old videos**: Keep spec JSON as-is, don't migrate data
- **New videos**: Use new spec format with beats from library
- **Database**: Both formats coexist via JSON column flexibility
- **Code**: Only generate new format, don't support generating old format

### Status Enum:
- **No changes to VideoStatus enum** (out of scope)
- Use existing statuses for TDD implementation
- `VALIDATING` → Phase 1 (Planning)
- `GENERATING_ANIMATIC` → Phase 2 (Storyboard)
- `GENERATING_REFERENCES` → Phase 3 (References)
- `GENERATING_CHUNKS` → Phase 4 (Chunks)
- `REFINING` → Phase 4 (Refinement)
- `EXPORTING` → Phase 6 (Export)

**Note:** Migration executed LAST after full TDD implementation and testing.

---

**Next:** Move to `TDD-tasks-2.md` for Phase 1 testing and Phase 2 implementation