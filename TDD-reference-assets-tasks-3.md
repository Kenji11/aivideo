## PR #4: Auto-Matching Logic

**Goal:** Automatically match reference assets to video beats based on semantic similarity and beat characteristics.

**Estimated Time:** 4-5 days  
**Dependencies:** PR #3

---

## Architecture Decision

**Phase Flow:**
- **Phase 0 (NEW):** Entity extraction & reference preparation
  - Runs BEFORE planning
  - Skips if user has 0 assets (performance optimization)
  - Outputs: extracted entities + user's available asset library
- **Phase 1 (Planning):** Receives Phase 0 output
  - LLM decides WHEN/WHERE to use reference assets
  - Generates reference_mapping based on beat requirements and guidelines
  - Outputs: spec + reference_mapping
- **Phase 2 (Storyboard):** Uses reference_mapping
  - Enhances image generation prompts with reference asset details
  - Generates storyboards informed by user's actual products/logos

---

## Reference Asset Usage Guidelines

**These guidelines will be provided to the LLM in Phase 1 system prompt.**

### Core Principle: ALWAYS USE ASSETS IF AVAILABLE

**This is an ADVERTISING app - users upload products/logos to feature them in videos.**

- If user has assets, **ALWAYS use at least one product and one logo** (if both types exist)
- If user has 0 assets, proceed with generic video generation
- Asset usage is the PRIMARY PURPOSE of this feature

### Product Selection Priority

**If user has multiple products:**

1. **Prompt mentions specific product** → Use that product (highest priority)
2. **Prompt mentions product category** → Use best matching product in that category
3. **Prompt is generic** → Use the product with:
   - Best style match (semantic similarity to prompt style_keywords)
   - OR most recently uploaded
   - OR highest usage_count (most popular)

**Never leave product beats empty if user has ANY product assets.**

### Product References - WHEN to Include

| Beat Type | Usage | Rationale |
|-----------|-------|-----------|
| Hero shots | **ALWAYS** | Product is the star, must be prominently featured |
| Product showcase | **ALWAYS** | Core purpose is to display the product |
| Detail shots | **ALWAYS** | Highlighting specific product features |
| Lifestyle beats | **ALWAYS** | Show product in use/context |
| Environment/atmosphere | **OPTIONAL** | Include if it enhances the narrative |
| Transition beats | **NEVER** | Too brief, focus is on motion/flow |

### Logo References - WHEN to Include

| Beat Type | Usage | Rationale |
|-----------|-------|-----------|
| Closing/CTA beats | **ALWAYS** | Brand reinforcement at video end - critical for recall |
| Opening beats | **SOMETIMES** | Brand recognition upfront - use if it fits the narrative flow |
| Hero shots | **OPTIONAL** | Enhances brand presence if composition allows |
| All other beats | **NEVER** | Clutters composition, distracts from narrative |

### Matching Strategy

**Semantic Similarity Thresholds:**
- **≥ 0.7:** Perfect match - use with confidence
- **0.5 - 0.7:** Good match - use if no better option
- **0.3 - 0.5:** Weak match - use if it's the only product available
- **< 0.3:** Poor match - skip only if this would break narrative coherence

**For advertising, bias toward INCLUSION over exclusion.**

**Fallback Logic:**
- If no products match above 0.3 → Use most recently uploaded product
- If user has logo → ALWAYS use in closing
- If user has multiple logos → Use the one matching brand name in prompt (if any)

### Examples

**Example 1: Nike Sneaker Ad**
- Opening: Skip logo (let product take focus)
- Hero shot: Product + Logo (both prominent)
- Detail shot: Product only (focus on texture/features)
- Lifestyle (running): Product only (in-use context)
- Closing: Logo (ALWAYS - brand reinforcement)

**Example 2: iPhone Ad**
- Opening: Apple logo (premium brand, fits narrative)
- Hero shots: Product (phone as star)
- Detail shots: Product (close-ups of features)
- Lifestyle beats: Product (in-hand usage)
- Closing: Logo (ALWAYS - Apple logo for brand recall)

**Example 3: Energy Drink Ad**
- Opening: Skip logo (dynamic opening needs energy, not branding)
- Hero: Product + Logo (can + branding)
- Lifestyle: Product (being consumed)
- Environment: Skip (mood/atmosphere focus)
- Closing: Logo (ALWAYS - brand reinforcement)

---

### Task 4.1: Entity Extraction Service (Phase 0)

**File:** `backend/app/services/entity_extraction.py`

- [ ] Create `EntityExtractionService` class
- [ ] Implement `extract_entities_from_prompt(user_id: str, prompt: str) -> dict`
- [ ] Check if user has any assets first
  - [ ] Query database for assets belonging to user
  - [ ] If user has 0 assets, return empty result immediately (skip extraction)
  - [ ] Only proceed with entity extraction if user has assets
- [ ] Build GPT-4 prompt for entity extraction
  - [ ] Request extraction of: product, brand, product_category, style_keywords
  - [ ] Request JSON response
  - [ ] Include examples
  - [ ] Handle case where prompt is generic (no specific product mentioned)
- [ ] Call OpenAI GPT-4 API
  - [ ] Model: `gpt-4o-mini` (cheaper, fast enough for entity extraction)
  - [ ] Temperature: 0.3 (more deterministic)
  - [ ] Response format: JSON
- [ ] Parse response
  - [ ] Extract product name (may be null if not mentioned)
  - [ ] Extract brand name (may be null if not mentioned)
  - [ ] Extract product category (may be generic like "product")
  - [ ] Extract style keywords (list)
- [ ] Return dict with:
  - [ ] `entities`: extracted entities dict (fields may be null/generic)
  - [ ] `user_assets`: list of user's available assets (with metadata)
  - [ ] `has_assets`: boolean flag
  - [ ] `product_mentioned`: boolean (true if specific product named in prompt)
- [ ] Add caching (cache results per prompt + user_id for 1 hour)
- [ ] Write unit tests
  - [ ] Test: User with 0 assets → skip extraction, return empty
  - [ ] Test: "15s Nike sneakers energetic urban" → extract "Nike", "sneakers", product_mentioned=true
  - [ ] Test: "luxury watch elegant" → extract category, product_mentioned=false
  - [ ] Test: "energetic ad" + user has 3 products → product_mentioned=false, return all assets
  - [ ] Test: "minimalist iPhone ad" → extract brand and style, product_mentioned=true

---

### Task 4.2: Create Phase 0 Task

**File:** `backend/app/phases/phase0_reference_prep/task.py`

- [ ] Create new phase directory: `backend/app/phases/phase0_reference_prep/`
- [ ] Create `__init__.py`
- [ ] Create `task.py` with `prepare_references()` Celery task
- [ ] Implement `prepare_references(video_id: str, prompt: str, user_id: str) -> dict`
  - [ ] Call `extract_entities_from_prompt(user_id, prompt)`
  - [ ] If user has no assets, return minimal output (empty entities)
  - [ ] If user has assets:
    - [ ] Call `select_best_product(user_assets, entities, prompt)`
    - [ ] Call `select_best_logo(user_assets, entities)`
    - [ ] Return full output with entities, assets, and recommendations
- [ ] Return PhaseOutput with:
  - [ ] `phase`: "phase0_reference_prep"
  - [ ] `output_data`:
    - [ ] `entities`: extracted entities dict (or empty)
    - [ ] `user_assets`: list of ALL available assets with metadata
    - [ ] `recommended_product`: best matching product asset
    - [ ] `recommended_logo`: best matching logo asset
    - [ ] `selection_rationale`: why these were recommended
    - [ ] `has_assets`: boolean
  - [ ] `cost_usd`: API cost (if extraction ran)
  - [ ] `duration_seconds`: execution time
- [ ] Write unit tests
  - [ ] Test with user who has no assets
  - [ ] Test with user who has 1 product → recommended
  - [ ] Test with user who has 3 products + Nike in prompt → Nike recommended
  - [ ] Test with user who has 3 products + generic prompt → best match recommended

---

### Task 4.3: Asset Metadata Retrieval

**File:** `backend/app/services/asset_search.py` (extend existing)

- [ ] Add function: `get_user_asset_library(user_id: str) -> list[dict]`
- [ ] Query all assets for user with relevant metadata:
  - [ ] asset_id, asset_type, primary_object, secondary_objects
  - [ ] recommended_shot_types, style_tags, colors
  - [ ] thumbnail_url (for frontend display)
  - [ ] created_at (for recency sorting)
  - [ ] usage_count (for popularity sorting)
- [ ] Return list of asset dicts with ALL metadata needed for matching
- [ ] Cache results (5 minutes TTL - user's asset library doesn't change often)
- [ ] Write unit tests
  - [ ] User with 0 assets → empty list
  - [ ] User with 5 assets → all metadata included

---

### Task 4.3b: Product Selection & Ranking Logic

**File:** `backend/app/services/product_selector.py` (NEW)

- [ ] Create `ProductSelectorService` class
- [ ] Implement `select_best_product(user_assets: list[dict], entities: dict, prompt: str) -> dict`
- [ ] Selection priority logic:
  1. **Exact product match:** If entities['product'] matches asset's primary_object → return that asset
  2. **Brand match:** If entities['brand'] matches asset metadata → return that asset
  3. **Category match:** If entities['product_category'] matches asset type → rank by style similarity
  4. **Generic prompt:** Rank all products by:
     - Semantic similarity to prompt (CLIP score)
     - Recency (created_at, newer = higher score)
     - Popularity (usage_count, more used = higher score)
  5. **Fallback:** Return most recently uploaded product
- [ ] Implement `rank_products_by_similarity(products: list[dict], prompt: str) -> list[dict]`
  - [ ] Use CLIP to calculate text-to-image similarity for each product
  - [ ] Combine similarity score with recency and popularity
  - [ ] Weighted formula: `0.6 * similarity + 0.2 * recency_score + 0.2 * popularity_score`
  - [ ] Return ranked list (highest score first)
- [ ] Implement `select_best_logo(user_assets: list[dict], entities: dict) -> dict`
  - [ ] If entities['brand'] specified → return logo matching brand
  - [ ] If multiple logos → return most recent
  - [ ] If no logos → return None
- [ ] Return dict with:
  - [ ] `selected_product`: asset dict or None
  - [ ] `selected_logo`: asset dict or None
  - [ ] `selection_rationale`: string explaining why this product was chosen
  - [ ] `confidence`: float 0.0-1.0
- [ ] Write unit tests
  - [ ] Test: Prompt "Nike sneakers" + 3 products → Nike selected
  - [ ] Test: Prompt "energetic ad" + 3 products → best style match selected
  - [ ] Test: Generic prompt + 3 products → most recent selected
  - [ ] Test: Multiple logos + brand in prompt → matching logo selected

---

### Task 4.4: Update Phase 1 to Receive Phase 0 Output

**File:** `backend/app/phases/phase1_validate/task.py`

- [ ] Update `plan_video_intelligent()` signature:
  - [ ] Add parameter: `phase0_output: dict = None`
  - [ ] Extract entities, user_assets, recommended_product, recommended_logo from phase0_output
- [ ] Pass entities and recommendations to LLM in system prompt
  - [ ] Include: "User has uploaded {N} assets: [asset list]"
  - [ ] Include: "Extracted entities: product={X}, brand={Y}, category={Z}"
  - [ ] Include: "**RECOMMENDED PRODUCT:** {recommended_product} - {selection_rationale}"
  - [ ] Include: "**RECOMMENDED LOGO:** {recommended_logo}"
  - [ ] Include: "**CRITICAL:** If recommended assets exist, USE THEM. This is an advertising app."
  - [ ] Include: "Decide which beats should reference which assets based on guidelines"
- [ ] After LLM generates spec, validate reference_mapping in output
  - [ ] Check that referenced asset_ids exist in user's library
  - [ ] Check that beat_ids exist in generated spec
  - [ ] **VALIDATE:** If user has assets, verify at least one product and one logo is used
  - [ ] If validation fails, log warning but don't fail (LLM may have good reason)
- [ ] Return updated PhaseOutput with reference_mapping included
- [ ] Write integration test
  - [ ] Phase 0 → Phase 1 with assets → verify reference_mapping generated
  - [ ] Phase 0 → Phase 1 without assets → verify empty reference_mapping
  - [ ] Phase 0 recommends Nike → Phase 1 uses Nike in reference_mapping
  - [ ] User has 3 products + generic prompt → Phase 1 uses recommended product

---

### Task 4.5: Update Phase 1 Schema for Reference Mapping

**File:** `backend/app/phases/phase1_validate/schemas.py`

- [ ] Extend `VideoPlanning` Pydantic schema
- [ ] Add field: `reference_mapping: dict[str, dict]`
  - [ ] Key: beat_id
  - [ ] Value: dict with:
    - [ ] `asset_ids`: list[str] - asset IDs to use for this beat
    - [ ] `usage_type`: str - "product" | "logo" | "environment"
    - [ ] `rationale`: str - why LLM chose these assets for this beat
- [ ] Add validation:
  - [ ] reference_mapping is optional (empty dict if no assets)
  - [ ] asset_ids must be non-empty list if present
  - [ ] usage_type must be valid enum value

---

### Task 4.6: Update Phase 1 System Prompt with Reference Guidelines

**File:** `backend/app/phases/phase1_validate/task.py` (in `build_gpt4_system_prompt()`)

- [ ] Add section: "REFERENCE ASSET USAGE GUIDELINES"
- [ ] **CRITICAL INSTRUCTION:** "This is an ADVERTISING app - users upload products/logos to feature them. If user has assets, ALWAYS use at least one product and one logo (if both types exist)."
- [ ] Document product selection priority:
  - [ ] If prompt mentions specific product → use that product
  - [ ] If prompt mentions category → use best matching product in that category
  - [ ] If prompt is generic → use best style match OR most recent OR highest usage_count
  - [ ] NEVER leave product beats empty if user has ANY product assets
- [ ] Document WHEN to include product references:
  - [ ] Hero shots: ALWAYS include product if available
  - [ ] Product showcase beats: ALWAYS include product
  - [ ] Detail shots: ALWAYS include product
  - [ ] Lifestyle beats: ALWAYS include product (show in use)
  - [ ] Environment/atmosphere beats: OPTIONAL - include if it enhances narrative
  - [ ] Transition beats: NEVER include product (too brief)
- [ ] Document WHEN to include logo references:
  - [ ] Opening beats: SOMETIMES include logo (use if it fits narrative flow)
  - [ ] Closing/CTA beats: ALWAYS include logo (brand reinforcement - critical)
  - [ ] Hero shots: OPTIONAL - include if it enhances brand presence
  - [ ] All other beats: NEVER include logo (clutters composition)
- [ ] Document matching strategy:
  - [ ] ≥ 0.7 similarity: Perfect match, use with confidence
  - [ ] 0.5-0.7 similarity: Good match, use if no better option
  - [ ] 0.3-0.5 similarity: Weak match, use if only product available
  - [ ] < 0.3 similarity: Poor match, use most recent as fallback
  - [ ] **Bias toward INCLUSION over exclusion for advertising**
- [ ] Add examples:
  - [ ] Example 1: Prompt "energetic sneaker ad" + 3 products (Nike, Adidas, Reebok) → pick Nike (best style match)
  - [ ] Example 2: Prompt "luxury watch" + 1 product (Rolex) → use Rolex everywhere (hero/detail/lifestyle)
  - [ ] Example 3: Prompt "tech ad" + iPhone + logo → iPhone in all product beats, logo in opening+closing

---

### Task 4.7: Update Phase 2 to Use Reference Mapping

**File:** `backend/app/phases/phase2_storyboard/image_generation.py`

- [ ] Update `generate_beat_image()` signature:
  - [ ] Add parameter: `reference_mapping: dict = None`
  - [ ] Add parameter: `user_assets: list[dict] = None`
- [ ] Check if current beat has references in mapping:
  - [ ] Look up `reference_mapping.get(beat['beat_id'])`
  - [ ] If exists, extract asset_ids and usage_type
- [ ] Fetch asset details from user_assets list
  - [ ] Get primary_object, style_tags, colors for referenced assets
- [ ] Enhance image generation prompt with reference info:
  - [ ] If product reference: Add "featuring [product_name], [primary_object description]"
  - [ ] If logo reference: Add "with [brand] logo visible, brand identity prominent"
  - [ ] Include asset's dominant colors in color palette
  - [ ] Include asset's style_tags in aesthetic description
- [ ] Log reference usage:
  - [ ] Log which assets were used for each beat
  - [ ] Track for usage_count increment later
- [ ] Write unit tests
  - [ ] Beat with product reference → prompt includes product details
  - [ ] Beat with logo reference → prompt includes logo mention
  - [ ] Beat with no references → prompt unchanged

---

### Task 4.8: Update Pipeline to Include Phase 0

**File:** `backend/app/orchestrator/pipeline.py`

- [ ] Import Phase 0 task: `from app.phases.phase0_reference_prep.task import prepare_references`
- [ ] Update `run_pipeline()` chain:
  ```python
  workflow = chain(
      # NEW: Phase 0 - Reference preparation
      prepare_references.s(video_id, prompt, user_id),
      
      # Phase 1 - Planning (receives Phase 0 output)
      plan_video_intelligent.s(video_id, prompt),
      
      # Phase 2 - Storyboard (receives Phase 1 output with reference_mapping)
      generate_storyboard.s(user_id),
      
      # Phase 3 - Chunks
      generate_chunks.s(user_id, model),
      
      # Phase 4 - Refine
      refine_video.s(user_id)
  )
  ```
- [ ] Update progress tracking to include Phase 0
- [ ] Update cost tracking to include Phase 0 entity extraction cost
- [ ] Write integration test
  - [ ] Full pipeline with Phase 0 → Phase 4
  - [ ] Verify Phase 0 output flows to Phase 1
  - [ ] Verify reference_mapping flows to Phase 2

---

### Task 4.9: Update Phase 2 Task to Accept Reference Mapping

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Update `generate_storyboard()` signature:
  - [ ] Accept phase1_output (already does this)
  - [ ] Extract reference_mapping from phase1_output['output_data']['reference_mapping']
  - [ ] Extract user_assets from Phase 0 output (stored in phase1_output or fetch from Redis)
- [ ] Pass reference_mapping + user_assets to `generate_beat_image()` for each beat
- [ ] Track which assets were used:
  - [ ] Build list of asset_ids that were actually used
  - [ ] Return in Phase 2 output for usage_count increment
- [ ] Write unit tests

---

### Task 4.10: Track Asset Usage

**File:** `backend/app/services/asset_usage_tracker.py` (NEW)

- [ ] Create `AssetUsageTracker` class
- [ ] Implement `increment_usage(asset_ids: list[str]) -> None`
  - [ ] For each asset_id in list
  - [ ] Increment `usage_count` in database
  - [ ] Update `last_used_at` timestamp
- [ ] Call from Phase 4 (final phase) when video completes successfully
- [ ] Write unit tests

---

### Task 4.11: Manual Override API

---

### Task 4.12: Manual Override API

**File:** `backend/app/api/videos.py`

- [ ] Implement `POST /api/videos/{video_id}/reference-mapping` endpoint
- [ ] Accept request body:
  ```json
  {
    "beat_id": "hero_shot",
    "asset_ids": ["asset_id_1", "asset_id_2"],
    "usage_type": "product"
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

### Task 4.13: Frontend: Reference Selection UI

**File:** `frontend/src/components/VideoGenerator.tsx`

- [ ] After entering prompt, show "Select References" step (optional)
- [ ] Display auto-matched references for each beat
  - [ ] Group by beat
  - [ ] Show thumbnails of matched assets
  - [ ] Show usage_type badge ("Product", "Logo", etc.)
  - [ ] Badge: "Auto-selected by AI"
- [ ] Allow manual override
  - [ ] "Change" button next to each beat
  - [ ] Open asset picker modal
  - [ ] Allow selecting different assets
  - [ ] Update reference mapping
- [ ] Add "Skip" option
  - [ ] User can proceed without references
  - [ ] System uses auto-selected references automatically
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

### Task 4.14: Testing & Validation

**Unit Tests:**
- [ ] Test entity extraction with 20 diverse prompts
- [ ] Test Phase 0 with user who has 0 assets (skip extraction)
- [ ] Test Phase 0 with user who has assets (run extraction)
- [ ] Test Phase 1 receives and uses Phase 0 output correctly
- [ ] Test Phase 2 uses reference_mapping in prompts
- [ ] Test asset usage tracking increments correctly
- [ ] Test manual override logic

**Integration Tests:**
- [ ] User with 0 assets → Phase 0 skips extraction, Phase 1 proceeds without references
- [ ] User with 1 Nike product + prompt "Nike sneakers" → Nike recommended and used in all product beats
- [ ] User with 3 products + prompt mentions Nike → Nike selected over other products
- [ ] User with 3 products + generic prompt "energetic ad" → best style match selected and used
- [ ] User with 1 product + 1 logo → BOTH used (product in hero/detail/lifestyle, logo in closing + optionally opening)
- [ ] User with logo only → logo used in closing beat (always), optionally in opening
- [ ] User with product only → product used in hero/detail/lifestyle beats
- [ ] Manual override → custom mapping used instead of AI-selected
- [ ] Full pipeline Phase 0 → Phase 4 with references

**Manual QA:**
- [ ] Generate video with 3 products, no specific mention → verify best match is selected
- [ ] Review beat-to-asset assignments for appropriateness
- [ ] Verify products appear in hero/detail/lifestyle shots (ALWAYS if available)
- [ ] Verify logos appear in closing (ALWAYS), sometimes in opening
- [ ] Manually override one beat
- [ ] Verify override takes precedence
- [ ] Generate video without references (user has none) → verify pipeline doesn't break
- [ ] Test with weak similarity match (< 0.3) → verify most recent product is used as fallback

---

### Task 4.15: Rename Phases Across Codebase

**Goal:** Rename all phases to reflect new Phase 0 insertion. This is cleanup work done during debugging/final implementation.

**Phase Renaming:**
- Phase 0 (NEW): `phase0_reference_prep` - Entity extraction & reference preparation
- Phase 1 (CURRENT): `phase1_validate` → Keep as `phase1_validate` (planning with references)
- Phase 2 (CURRENT): `phase2_storyboard` → Keep as `phase2_storyboard` 
- Phase 3 (CURRENT): `phase3_chunks` → Keep as `phase3_chunks`
- Phase 4 (CURRENT): `phase4_refine` → Keep as `phase4_refine`

**Note:** Since we're INSERTING Phase 0 before Phase 1, existing phase numbers don't need to change. Phase 0 is truly "pre-planning" preparation.

**Files to Update:**
- [ ] `backend/app/orchestrator/pipeline.py` - Add Phase 0 to chain
- [ ] `backend/app/orchestrator/progress.py` - Update progress tracking
- [ ] `backend/app/common/schemas.py` - Add Phase 0 to PhaseOutput enum (if exists)
- [ ] `backend/app/database.py` - Update phase_outputs JSONB field documentation
- [ ] All log messages referencing phase numbers
- [ ] Frontend phase display components
- [ ] API documentation
- [ ] Architecture diagrams in `/architecture` directory
- [ ] Update `README.md` to reflect Phase 0

**Testing:**
- [ ] Verify all phase transitions work correctly
- [ ] Verify progress tracking shows Phase 0
- [ ] Verify cost tracking includes Phase 0
- [ ] Verify logs correctly identify phases
- [ ] Verify frontend displays Phase 0 status

---

### Acceptance Criteria

- [ ] Phase 0 runs before Phase 1 for all video generations
- [ ] Phase 0 skips entity extraction if user has 0 assets (performance optimization)
- [ ] Phase 0 recommends best product and logo based on prompt analysis
- [ ] **CRITICAL:** If user has assets, at least one product and one logo are ALWAYS used (if both types exist)
- [ ] Product selection priority works correctly:
  - [ ] Specific product mentioned in prompt → that product is used
  - [ ] No product mentioned → best style match is selected
  - [ ] Multiple products → ranking algorithm selects best fit
- [ ] Phase 1 receives recommendations and uses them in reference_mapping
- [ ] Phase 1 LLM follows guidelines and uses recommended assets
- [ ] Reference asset usage follows documented guidelines:
  - [ ] Products: ALWAYS in hero/showcase/detail/lifestyle beats if available
  - [ ] Logos: ALWAYS in closing beats, SOMETIMES in opening beats
- [ ] Phase 2 generates storyboard images with reference asset information in prompts
- [ ] Asset usage_count is tracked correctly
- [ ] Frontend shows AI-selected references clearly
- [ ] Manual selection UI allows overrides
- [ ] All tests pass
- [ ] Product selection accuracy >85% (manual review of 20 test cases with multiple products)
- [ ] Asset inclusion rate: >95% (if user has assets, they MUST appear in video)
- [ ] Pipeline works correctly for users with and without assets
- [ ] All phases correctly named and documented
