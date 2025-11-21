## PR #4: Auto-Matching Logic ✅

**Goal:** Automatically match reference assets to video beats based on semantic similarity and beat characteristics.

**Estimated Time:** 4-5 days  
**Dependencies:** PR #3  
**Status:** ✅ COMPLETE

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

### Task 4.1: Entity Extraction Service (Phase 0) ✅

**File:** `backend/app/services/entity_extraction.py`

- [x] Create `EntityExtractionService` class
- [x] Implement `extract_entities_from_prompt(user_id: str, prompt: str) -> dict`
- [x] Check if user has any assets first
  - [x] Query database for assets belonging to user
  - [x] If user has 0 assets, return empty result immediately (skip extraction)
  - [x] Only proceed with entity extraction if user has assets
- [x] Build GPT-4 prompt for entity extraction
  - [x] Request extraction of: product, brand, product_category, style_keywords
  - [x] Request JSON response
  - [x] Include examples
  - [x] Handle case where prompt is generic (no specific product mentioned)
- [x] Call OpenAI GPT-4 API
  - [x] Model: `gpt-4o-mini` (cheaper, fast enough for entity extraction)
  - [x] Temperature: 0.3 (more deterministic)
  - [x] Response format: JSON
- [x] Parse response
  - [x] Extract product name (may be null if not mentioned)
  - [x] Extract brand name (may be null if not mentioned)
  - [x] Extract product category (may be generic like "product")
  - [x] Extract style keywords (list)
- [x] Return dict with:
  - [x] `entities`: extracted entities dict (fields may be null/generic)
  - [x] `user_assets`: list of user's available assets (with metadata)
  - [x] `has_assets`: boolean flag
  - [x] `product_mentioned`: boolean (true if specific product named in prompt)

---

### Task 4.2: Create Phase 0 Task ✅

**File:** `backend/app/phases/phase0_reference_prep/task.py`

- [x] Create new phase directory: `backend/app/phases/phase0_reference_prep/`
- [x] Create `__init__.py`
- [x] Create `task.py` with `prepare_references()` Celery task
- [x] Implement `prepare_references(video_id: str, prompt: str, user_id: str) -> dict`
  - [x] Call `extract_entities_from_prompt(user_id, prompt)`
  - [x] If user has no assets, return minimal output (empty entities)
  - [x] If user has assets:
    - [x] Call `select_best_product(user_assets, entities, prompt)`
    - [x] Call `select_best_logo(user_assets, entities)`
    - [x] Return full output with entities, assets, and recommendations
- [x] Return PhaseOutput with:
  - [x] `phase`: "phase0_reference_prep"
  - [x] `output_data`:
    - [x] `entities`: extracted entities dict (or empty)
    - [x] `user_assets`: list of ALL available assets with metadata
    - [x] `recommended_product`: best matching product asset
    - [x] `recommended_logo`: best matching logo asset
    - [x] `selection_rationale`: why these were recommended
    - [x] `has_assets`: boolean
  - [x] `cost_usd`: API cost (if extraction ran)
  - [x] `duration_seconds`: execution time

---

### Task 4.3: Asset Metadata Retrieval ✅

**File:** `backend/app/services/asset_search.py` (extend existing)

- [x] Add function: `get_user_asset_library(user_id: str) -> list[dict]`
- [x] Query all assets for user with relevant metadata:
  - [x] asset_id, asset_type, primary_object, secondary_objects
  - [x] recommended_shot_types, style_tags, colors
  - [x] thumbnail_url (for frontend display)
  - [x] created_at (for recency sorting)
  - [x] usage_count (for popularity sorting)
- [x] Return list of asset dicts with ALL metadata needed for matching

---

### Task 4.3b: Product Selection & Ranking Logic ✅

**File:** `backend/app/services/product_selector.py` (NEW)

- [x] Create `ProductSelectorService` class
- [x] Implement `select_best_product(user_assets: list[dict], entities: dict, prompt: str) -> dict`
- [x] Selection priority logic:
  1. **Exact product match:** If entities['product'] matches asset's primary_object → return that asset
  2. **Brand match:** If entities['brand'] matches asset metadata → return that asset
  3. **Category match:** If entities['product_category'] matches asset type → rank by style similarity
  4. **Generic prompt:** Rank all products by:
     - Semantic similarity to prompt (CLIP score)
     - Recency (created_at, newer = higher score)
     - Popularity (usage_count, more used = higher score)
  5. **Fallback:** Return most recently uploaded product
- [x] Implement `rank_products_by_similarity(products: list[dict], prompt: str) -> list[dict]`
  - [x] Use CLIP to calculate text-to-image similarity for each product
  - [x] Combine similarity score with recency and popularity
  - [x] Weighted formula: `0.6 * similarity + 0.2 * recency_score + 0.2 * popularity_score`
  - [x] Return ranked list (highest score first)
- [x] Implement `select_best_logo(user_assets: list[dict], entities: dict) -> dict`
  - [x] If entities['brand'] specified → return logo matching brand
  - [x] If multiple logos → return most recent
  - [x] If no logos → return None
- [x] Return dict with:
  - [x] `selected_product`: asset dict or None
  - [x] `selected_logo`: asset dict or None
  - [x] `selection_rationale`: string explaining why this product was chosen
  - [x] `confidence`: float 0.0-1.0

---

### Task 4.4: Update Phase 1 to Receive Phase 0 Output ✅

**File:** `backend/app/phases/phase1_validate/task.py`

- [x] Update `plan_video_intelligent()` signature:
  - [x] Add parameter: `phase0_output: dict = None`
  - [x] Extract entities, user_assets, recommended_product, recommended_logo from phase0_output
- [x] Pass entities and recommendations to LLM in system prompt
  - [x] Include: "User has uploaded {N} assets: [asset list]"
  - [x] Include: "Extracted entities: product={X}, brand={Y}, category={Z}"
  - [x] Include: "**RECOMMENDED PRODUCT:** {recommended_product} - {selection_rationale}"
  - [x] Include: "**RECOMMENDED LOGO:** {recommended_logo}"
  - [x] Include: "**CRITICAL:** If recommended assets exist, USE THEM. This is an advertising app."
  - [x] Include: "Decide which beats should reference which assets based on guidelines"
- [x] After LLM generates spec, validate reference_mapping in output
  - [x] Check that referenced asset_ids exist in user's library
  - [x] Check that beat_ids exist in generated spec
  - [x] **VALIDATE:** If user has assets, verify at least one product and one logo is used
  - [x] If validation fails, log warning but don't fail (LLM may have good reason)
- [x] Return updated PhaseOutput with reference_mapping included

---

### Task 4.5: Update Phase 1 Schema for Reference Mapping ✅

**File:** `backend/app/phases/phase1_validate/schemas.py`

- [x] Extend `VideoPlanning` Pydantic schema
- [x] Add field: `reference_mapping: dict[str, dict]`
  - [x] Key: beat_id
  - [x] Value: dict with:
    - [x] `asset_ids`: list[str] - asset IDs to use for this beat
    - [x] `usage_type`: str - "product" | "logo" | "environment"
    - [x] `rationale`: str - why LLM chose these assets for this beat
- [x] Add validation:
  - [x] reference_mapping is optional (empty dict if no assets)
  - [x] asset_ids must be non-empty list if present
  - [x] usage_type must be valid enum value

---

### Task 4.6: Update Phase 1 System Prompt with Reference Guidelines ✅

**File:** `backend/app/phases/phase1_validate/task.py` (in `build_gpt4_system_prompt()`)

- [x] Add section: "REFERENCE ASSET USAGE GUIDELINES"
- [x] **CRITICAL INSTRUCTION:** "This is an ADVERTISING app - users upload products/logos to feature them. If user has assets, ALWAYS use at least one product and one logo (if both types exist)."
- [x] Document product selection priority:
  - [x] If prompt mentions specific product → use that product
  - [x] If prompt mentions category → use best matching product in that category
  - [x] If prompt is generic → use best style match OR most recent OR highest usage_count
  - [x] NEVER leave product beats empty if user has ANY product assets
- [x] Document WHEN to include product references:
  - [x] Hero shots: ALWAYS include product if available
  - [x] Product showcase beats: ALWAYS include product
  - [x] Detail shots: ALWAYS include product
  - [x] Lifestyle beats: ALWAYS include product (show in use)
  - [x] Environment/atmosphere beats: OPTIONAL - include if it enhances narrative
  - [x] Transition beats: NEVER include product (too brief)
- [x] Document WHEN to include logo references:
  - [x] Opening beats: SOMETIMES include logo (use if it fits narrative flow)
  - [x] Closing/CTA beats: ALWAYS include logo (brand reinforcement - critical)
  - [x] Hero shots: OPTIONAL - include if it enhances brand presence
  - [x] All other beats: NEVER include logo (clutters composition)
- [x] Document matching strategy:
  - [x] ≥ 0.7 similarity: Perfect match, use with confidence
  - [x] 0.5-0.7 similarity: Good match, use if no better option
  - [x] 0.3-0.5 similarity: Weak match, use if only product available
  - [x] < 0.3 similarity: Poor match, use most recent as fallback
  - [x] **Bias toward INCLUSION over exclusion for advertising**
- [x] Add examples:
  - [x] Example 1: Prompt "energetic sneaker ad" + 3 products (Nike, Adidas, Reebok) → pick Nike (best style match)
  - [x] Example 2: Prompt "luxury watch" + 1 product (Rolex) → use Rolex everywhere (hero/detail/lifestyle)
  - [x] Example 3: Prompt "tech ad" + iPhone + logo → iPhone in all product beats, logo in opening+closing

---

### Task 4.7: Update Phase 2 to Use Reference Mapping ✅

**File:** `backend/app/phases/phase2_storyboard/image_generation.py`

- [x] Update `generate_beat_image()` signature:
  - [x] Add parameter: `reference_mapping: dict = None`
  - [x] Add parameter: `user_assets: list[dict] = None`
- [x] Check if current beat has references in mapping:
  - [x] Look up `reference_mapping.get(beat['beat_id'])`
  - [x] If exists, extract asset_ids and usage_type
- [x] Fetch asset details from user_assets list
  - [x] Get primary_object, style_tags, colors for referenced assets
- [x] Enhance image generation prompt with reference info:
  - [x] If product reference: Add "featuring [product_name], [primary_object description]"
  - [x] If logo reference: Add "with [brand] logo visible, brand identity prominent"
  - [x] Include asset's dominant colors in color palette
  - [x] Include asset's style_tags in aesthetic description
- [x] Log reference usage:
  - [x] Log which assets were used for each beat
  - [x] Track for usage_count increment later

---

### Task 4.8: Update Pipeline to Include Phase 0 ✅

**File:** `backend/app/orchestrator/pipeline.py`

- [x] Import Phase 0 task: `from app.phases.phase0_reference_prep.task import prepare_references`
- [x] Update `run_pipeline()` chain:
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
- [x] Update progress tracking to include Phase 0
- [x] Update cost tracking to include Phase 0 entity extraction cost

---

### Task 4.9: Update Phase 2 Task to Accept Reference Mapping ✅

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [x] Update `generate_storyboard()` signature:
  - [x] Accept phase1_output (already does this)
  - [x] Extract reference_mapping from phase1_output['output_data']['reference_mapping']
  - [x] Extract user_assets from Phase 0 output (stored in phase1_output)
- [x] Pass reference_mapping + user_assets to `generate_beat_image()` for each beat
- [x] Track which assets were used:
  - [x] Build list of asset_ids that were actually used
  - [x] Return in Phase 2 output for usage_count increment

---

### Task 4.10: Track Asset Usage ✅

**File:** `backend/app/services/asset_usage_tracker.py` (NEW)

- [x] Create `AssetUsageTracker` class
- [x] Implement `increment_usage(asset_ids: list[str]) -> None`
  - [x] For each asset_id in list
  - [x] Increment `usage_count` in database
  - [x] Update `updated_at` timestamp
- [x] Implement `increment_usage_for_video(video_id: str) -> None`
  - [x] Fetch referenced_asset_ids from Phase 2 output
  - [x] Call increment_usage for all referenced assets
- [x] Call from Phase 4 (final phase) when video completes successfully

---

### Task 4.14: Testing & Validation

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

**Manual QA:**
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
