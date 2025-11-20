## PR #4: Auto-Matching Logic

**Goal:** Automatically match reference assets to video beats based on semantic similarity and beat characteristics.

**Estimated Time:** 3-4 days  
**Dependencies:** PR #3

---

### Task 4.1: Entity Extraction Service

**File:** `backend/app/services/entity_extraction.py`

- [ ] Create `EntityExtractionService` class
- [ ] Implement `extract_entities_from_prompt(prompt: str) -> dict`
- [ ] Build GPT-4 prompt for entity extraction
  - [ ] Request extraction of: product, brand, product_category, style_keywords
  - [ ] Request JSON response
  - [ ] Include examples
- [ ] Call OpenAI GPT-4 API
  - [ ] Model: `gpt-4-turbo-preview`
  - [ ] Temperature: 0.3 (more deterministic)
  - [ ] Response format: JSON
- [ ] Parse response
  - [ ] Extract product name
  - [ ] Extract brand name
  - [ ] Extract product category
  - [ ] Extract style keywords (list)
- [ ] Return dict with extracted entities
- [ ] Add caching (cache results per prompt for 1 hour)
- [ ] Write unit tests
  - [ ] Test: "15s Nike sneakers energetic urban" → extract "Nike", "sneakers", etc.
  - [ ] Test: "luxury watch elegant" → extract product category
  - [ ] Test: "minimalist iPhone ad" → extract brand and style

---

### Task 4.2: Auto-Matching Service

**File:** `backend/app/services/auto_matching.py`

- [ ] Create `AutoMatchingService` class
- [ ] Implement `auto_match_references(user_id: str, prompt: str, spec: dict) -> dict`
- [ ] Step 1: Extract entities from prompt
  - [ ] Call `extract_entities_from_prompt()`
  - [ ] Store entities for use in matching
- [ ] Step 2: Get all user's reference assets
  - [ ] Query database for assets belonging to user
  - [ ] If no assets, return empty mapping
- [ ] Step 3: Match assets to each beat
  - [ ] Loop through spec['beats']
  - [ ] For each beat, call `find_assets_for_beat()`
    - [ ] Pass user_id
    - [ ] Pass beat dict
    - [ ] Pass product_hint from extracted entities
    - [ ] Get back: product_refs, logo_refs, environment_refs
  - [ ] Calculate confidence score for this match
    - [ ] Call `calculate_match_confidence()`
  - [ ] Store in beat_reference_map
- [ ] Return dict mapping beat_id → matched references + confidence
- [ ] Write unit tests
  - [ ] Test with user having Nike product + logo
  - [ ] Test with user having no assets
  - [ ] Test with prompt mentioning specific product
  - [ ] Test with generic prompt (no product mentioned)

---

### Task 4.3: Confidence Scoring

**File:** `backend/app/services/auto_matching.py`

- [ ] Implement `calculate_match_confidence(beat: dict, matched_assets: dict, entities: dict) -> float`
- [ ] Scoring factors (total = 1.0):
  - [ ] Asset found: +0.3 if any product_refs exist
  - [ ] Shot type compatibility: +0.3 if beat shot_type in asset's recommended_shot_types
  - [ ] Semantic similarity: +0.2 based on CLIP similarity score
  - [ ] Product name match: +0.2 if entity product matches asset primary_object
- [ ] Calculate weighted sum
- [ ] Clamp result to [0.0, 1.0]
- [ ] Return confidence score
- [ ] Write unit tests
  - [ ] Perfect match → score ≈ 1.0
  - [ ] Partial match → score ≈ 0.5
  - [ ] Poor match → score ≈ 0.2

---

### Task 4.4: Integrate into Phase 1

**File:** `backend/app/phases/phase1_planning/task.py`

- [ ] Update `plan_video_intelligent()` function
- [ ] After building spec, add auto-matching step:
  ```python
  # Auto-match reference assets
  if reference_asset_ids:
      reference_mapping = auto_match_references(user_id, prompt, spec)
  else:
      reference_mapping = {}
  ```
- [ ] Store reference_mapping in Phase 1 output
- [ ] Update PhaseOutput schema to include reference_mapping
- [ ] Pass reference_mapping to Phase 2
- [ ] Write integration test
  - [ ] User with assets generates video
  - [ ] Verify reference_mapping is populated
  - [ ] Verify confidence scores are reasonable

---

### Task 4.5: Manual Override API

**File:** `backend/app/api/videos.py`

- [ ] Implement `POST /api/videos/{video_id}/reference-mapping` endpoint
- [ ] Accept request body:
  ```json
  {
    "beat_id": "hero_shot",
    "asset_ids": ["asset_id_1", "asset_id_2"]
  }
  ```
- [ ] Verify video ownership
- [ ] Verify assets belong to user
- [ ] Update video record:
  - [ ] Add/update `custom_reference_mapping` field
  - [ ] Store beat_id → asset_ids mapping
  - [ ] Mark as manually selected
- [ ] Return success response
- [ ] Implement `GET /api/videos/{video_id}/reference-mapping` endpoint
  - [ ] Return current reference mapping (auto + manual overrides)
  - [ ] Merge auto-matched and custom mappings
  - [ ] Indicate which are manual vs auto
- [ ] Write integration tests

---

### Task 4.6: Frontend: Reference Selection UI

**File:** `frontend/src/components/VideoGenerator.tsx`

- [ ] After entering prompt, show "Select References" step (optional)
- [ ] Display auto-matched references for each beat
  - [ ] Group by beat
  - [ ] Show thumbnails of matched assets
  - [ ] Show confidence score
  - [ ] Badge: "Auto-matched"
- [ ] Allow manual override
  - [ ] "Change" button next to each beat
  - [ ] Open asset picker modal
  - [ ] Allow selecting different assets
  - [ ] Update reference mapping
- [ ] Add "Skip" option
  - [ ] User can proceed without references
  - [ ] System uses auto-matched references automatically
- [ ] Show preview of selected references
  - [ ] Thumbnails with labels
  - [ ] Remove button for each
- [ ] Persist selection when user proceeds to generation
- [ ] Style with Tailwind CSS

**File:** `frontend/src/components/AssetPickerModal.tsx`

- [ ] Create modal for manually selecting assets
- [ ] Display user's asset library in grid
- [ ] Filter by asset type (product/logo/etc)
- [ ] Search assets (integrate with semantic search)
- [ ] Multi-select capability
  - [ ] Checkboxes on thumbnails
  - [ ] "Select" button to confirm
- [ ] Show selected count
- [ ] Close and return selected assets to parent component

---

### Task 4.7: Update Video Generation Flow

**File:** `backend/app/orchestrator/video_orchestrator.py`

- [ ] Update `orchestrate_video_generation()` task
- [ ] Pass reference_asset_ids to Phase 1
- [ ] Get reference_mapping from Phase 1 output
- [ ] Merge with custom_reference_mapping if exists
- [ ] Pass final reference_mapping to Phase 2
- [ ] Store reference usage in database
  - [ ] Track which assets were used in which videos
  - [ ] Increment usage_count for each asset
- [ ] Write integration test
  - [ ] Full video generation with references
  - [ ] Verify references used in storyboards
  - [ ] Verify usage_count incremented

---

### Task 4.8: Testing & Validation

**Unit Tests:**
- [ ] Test entity extraction with 20 diverse prompts
- [ ] Test auto-matching with various user asset libraries
- [ ] Test confidence scoring edge cases
- [ ] Test manual override logic

**Integration Tests:**
- [ ] User with 0 assets → auto-matching returns empty
- [ ] User with 1 Nike product → Nike prompt matches product
- [ ] User with 5 products → correct product matched based on prompt
- [ ] User with logo → logo matched to all beats
- [ ] Manual override → custom mapping used instead of auto

**Manual QA:**
- [ ] Generate video with auto-matched references
- [ ] Review matched assets for relevance
- [ ] Manually override one beat
- [ ] Verify override takes precedence
- [ ] Generate video without references (user has none)
- [ ] Verify pipeline doesn't break

---

### Acceptance Criteria

- [ ] System automatically matches user's assets to video beats
- [ ] Entity extraction identifies products/brands in prompts
- [ ] Confidence scores accurately reflect match quality
- [ ] Users can manually override auto-matched assets
- [ ] Reference mapping persists through video generation
- [ ] Asset usage_count is tracked
- [ ] Frontend shows auto-matched references clearly
- [ ] Manual selection UI is intuitive
- [ ] All tests pass
- [ ] Auto-matching accuracy >75% (manual review of 20 test cases)
