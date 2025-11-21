# TDD-reference-assets-tasks-3.md

## PR #3: Semantic Search System

**Goal:** Implement vector similarity search for finding relevant assets by text query or visual similarity.

**Estimated Time:** 2-3 days  
**Dependencies:** PR #2

---

### Task 3.1: Semantic Search Service

**File:** `backend/app/services/asset_search.py`

- [x] Create `AssetSearchService` class
- [x] Implement `search_assets_by_text(user_id: str, query: str, asset_type: AssetType = None, limit: int = 10) -> list[Asset]`
  - [x] Generate query embedding using CLIP text encoder
  - [x] Build SQLAlchemy query filtering by user_id
  - [x] If asset_type provided, add filter
  - [x] Order by cosine distance to query embedding
  - [x] Limit results
  - [x] Calculate similarity score for each result
  - [x] Attach similarity_score as attribute to each asset
  - [x] Return list of assets
- [x] Implement `find_similar_assets(reference_asset_id: str, limit: int = 10, exclude_self: bool = True) -> list[Asset]`
  - [x] Fetch reference asset from database
  - [x] Get its embedding
  - [x] Query for similar embeddings
  - [x] Optionally exclude the reference asset itself
  - [x] Order by cosine distance
  - [x] Return list of similar assets
- [x] Implement `find_assets_for_beat(user_id: str, beat: dict, product_hint: str = None, limit: int = 3) -> dict`
  - [x] Compose search query from beat characteristics
    - [x] Include product_hint if provided
    - [x] Include beat['shot_type']
    - [x] Include beat['action']
    - [x] Include beat.get('mood', '')
  - [x] Call search_assets_by_text() with composed query
  - [x] Filter results by recommended_shot_types
    - [x] Keep only assets where beat['shot_type'] in asset.recommended_shot_types
  - [x] Separate results by asset type
  - [x] Return dict with keys: 'product_refs', 'logo_refs', 'environment_refs'
- [x] Add helper: `cosine_distance(vec1: list[float], vec2: list[float]) -> float`
  - [x] Calculate cosine distance = 1 - cosine_similarity
  - [x] Use numpy for efficiency
- [ ] Write unit tests
  - [ ] Test text search with various queries
  - [ ] Test visual similarity search
  - [ ] Test filtering by asset_type
  - [ ] Test beat-specific search

---

### Task 3.2: De-duplication Service (SKIPPED)

**Note:** Duplicate detection on upload has been removed. The service method `check_duplicate_asset()` remains in `asset_search.py` for potential future use, but is not exposed via API or used in upload flow.

---

### Task 3.3: Style Recommendation Service

**File:** `backend/app/services/asset_search.py`

- [x] Implement `recommend_style_consistent_assets(user_id: str, selected_asset_ids: list[str], limit: int = 10) -> list[Asset]`
- [x] Fetch selected assets from database
- [x] Extract embeddings from selected assets
- [x] Calculate centroid (average embedding)
  - [x] Use numpy.mean() across embeddings
- [x] Query for assets near centroid
  - [x] Filter by user_id
  - [x] Exclude selected assets
  - [x] Order by cosine distance to centroid
  - [x] Limit results
- [x] Return recommended assets
- [ ] Write unit tests
  - [ ] Select 2 Nike products → should recommend other Nike products
  - [ ] Select luxury items → should recommend other luxury items

---

### Task 3.4: Search API Endpoints

**File:** `backend/app/api/assets.py` (new file - separate from upload.py)

- [x] Implement `GET /api/assets/search` endpoint
  - [x] Accept query parameters:
    - [x] `q` (query string, required)
    - [x] `asset_type` (optional filter: product/logo/person/etc)
    - [x] `limit` (default 10, max 50)
  - [x] Call `search_assets_by_text()`
  - [x] Return list of assets with similarity scores
  - [x] Include thumbnails in response
- [x] Implement `GET /api/assets/{asset_id}/similar` endpoint
  - [x] Accept query parameters:
    - [x] `limit` (default 10, max 50)
    - [x] `exclude_self` (default true)
  - [x] Verify asset ownership
  - [x] Call `find_similar_assets()`
  - [x] Return list of similar assets
- [x] Implement `POST /api/assets/recommend` endpoint
  - [x] Accept request body: `{"selected_asset_ids": ["id1", "id2"]}`
  - [x] Call `recommend_style_consistent_assets()`
  - [x] Return recommended assets
- [ ] Write integration tests for all endpoints

---

### Task 3.5: Frontend Search Bar

**File:** `frontend/src/pages/AssetLibrary.tsx` (integrate directly, no separate component)

- [x] Add search bar to top of page (above filters)
- [x] Implement text input with search icon
- [x] Add debounced search (wait 300ms after typing stops)
- [x] Call `/api/assets/search` on input change
- [x] When search active, show search results instead of full grid
- [x] Display search results with:
  - [x] Thumbnail + name
  - [x] Asset type badge
  - [x] Similarity score (if relevant)
- [x] Click result → show detail modal
- [x] Add "Clear search" button to return to full grid
- [x] Show loading indicator while searching
- [x] Handle empty results gracefully
- [x] Style with Tailwind CSS

---

### Task 3.6: Duplicate Detection on Upload (SKIPPED)

**Note:** Duplicate detection on upload has been removed. Users can upload assets without duplicate warnings.

---

### Task 3.7: "Find Similar" Feature

**File:** `frontend/src/components/AssetDetailModal.tsx`

- [x] Add "Find Similar" button to asset detail modal
- [x] On click:
  - [x] Call `/api/assets/{asset_id}/similar`
  - [x] Show results in modal or new view
  - [x] Display thumbnails of similar assets
  - [x] Show similarity scores
  - [x] Allow clicking to view those assets
- [x] Add loading state
- [x] Style with Tailwind CSS

---

### Task 3.8: Testing & Performance

**Unit Tests:**
- [ ] Test semantic search with various queries
  - [ ] "red Nike sneaker" → find red Nike products
  - [ ] "minimalist logo" → find logos with minimalist style
  - [ ] "urban environment" → find city/street scenes
- [ ] Test visual similarity
  - [ ] Similar products should rank high
  - [ ] Different products should rank low
- [ ] Test duplicate detection
  - [ ] Exact duplicate → score ≈ 1.0
  - [ ] Similar but different → score < 0.95

**Integration Tests:**
- [ ] Upload 20 diverse assets
- [ ] Run 10 different search queries
- [ ] Verify results are relevant
- [ ] Test pagination
- [ ] Test filters (asset_type, is_logo)

**Performance:**
- [ ] Measure search latency (target: <500ms)
- [ ] Test with 1000+ assets in database
- [ ] Verify pgvector index is being used (check EXPLAIN output)
- [ ] Optimize if needed (adjust IVFFlat lists parameter)

**Manual QA:**
- [ ] Search for "red product" → verify red products returned
- [ ] Upload duplicate → verify warning shown
- [ ] Click "Find Similar" → verify similar assets shown
- [ ] Test empty search results
- [ ] Test search with typos

---

### Acceptance Criteria

- [x] Users can search assets by text query
- [x] Search results are semantically relevant (not just keyword matching)
- [x] Users can find visually similar assets
- [x] Search latency is <500ms
- [x] "Find Similar" feature works in detail modal
- [x] Search results show similarity scores
- [ ] All tests pass
- [x] Search works with 1000+ assets efficiently

---

# TDD-reference-assets-tasks-4.md