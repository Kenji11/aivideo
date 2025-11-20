# TDD-reference-assets-tasks-3.md

## PR #3: Semantic Search System

**Goal:** Implement vector similarity search for finding relevant assets by text query or visual similarity.

**Estimated Time:** 2-3 days  
**Dependencies:** PR #2

---

### Task 3.1: Semantic Search Service

**File:** `backend/app/services/asset_search.py`

- [ ] Create `AssetSearchService` class
- [ ] Implement `search_assets_by_text(user_id: str, query: str, asset_type: AssetType = None, limit: int = 10) -> list[ReferenceAsset]`
  - [ ] Generate query embedding using CLIP text encoder
  - [ ] Build SQLAlchemy query filtering by user_id
  - [ ] If asset_type provided, add filter
  - [ ] Order by cosine distance to query embedding
  - [ ] Limit results
  - [ ] Calculate similarity score for each result
  - [ ] Attach similarity_score as attribute to each asset
  - [ ] Return list of assets
- [ ] Implement `find_similar_assets(reference_asset_id: str, limit: int = 10, exclude_self: bool = True) -> list[ReferenceAsset]`
  - [ ] Fetch reference asset from database
  - [ ] Get its embedding
  - [ ] Query for similar embeddings
  - [ ] Optionally exclude the reference asset itself
  - [ ] Order by cosine distance
  - [ ] Return list of similar assets
- [ ] Implement `find_assets_for_beat(user_id: str, beat: dict, product_hint: str = None, limit: int = 3) -> dict`
  - [ ] Compose search query from beat characteristics
    - [ ] Include product_hint if provided
    - [ ] Include beat['shot_type']
    - [ ] Include beat['action']
    - [ ] Include beat.get('mood', '')
  - [ ] Call search_assets_by_text() with composed query
  - [ ] Filter results by recommended_shot_types
    - [ ] Keep only assets where beat['shot_type'] in asset.recommended_shot_types
  - [ ] Separate results by asset type
  - [ ] Return dict with keys: 'product_refs', 'logo_refs', 'environment_refs'
- [ ] Add helper: `cosine_distance(vec1: list[float], vec2: list[float]) -> float`
  - [ ] Calculate cosine distance = 1 - cosine_similarity
  - [ ] Use numpy for efficiency
- [ ] Write unit tests
  - [ ] Test text search with various queries
  - [ ] Test visual similarity search
  - [ ] Test filtering by asset_type
  - [ ] Test beat-specific search

---

### Task 3.2: De-duplication Service

**File:** `backend/app/services/asset_search.py`

- [ ] Implement `check_duplicate_asset(user_id: str, new_image_embedding: list[float], similarity_threshold: float = 0.95) -> list[ReferenceAsset]`
- [ ] Query for assets with similar embeddings
  - [ ] Filter by user_id
  - [ ] Order by cosine distance to new embedding
  - [ ] Limit to top 5 matches
- [ ] Calculate similarity scores (1 - cosine_distance)
- [ ] Filter by threshold (default 0.95 = very similar)
- [ ] Return potential duplicates with similarity scores
- [ ] Write unit tests
  - [ ] Upload same image twice → should detect duplicate
  - [ ] Upload similar but different images → should not flag
  - [ ] Test threshold sensitivity

---

### Task 3.3: Style Recommendation Service

**File:** `backend/app/services/asset_search.py`

- [ ] Implement `recommend_style_consistent_assets(user_id: str, selected_asset_ids: list[str], limit: int = 10) -> list[ReferenceAsset]`
- [ ] Fetch selected assets from database
- [ ] Extract embeddings from selected assets
- [ ] Calculate centroid (average embedding)
  - [ ] Use numpy.mean() across embeddings
- [ ] Query for assets near centroid
  - [ ] Filter by user_id
  - [ ] Exclude selected assets
  - [ ] Order by cosine distance to centroid
  - [ ] Limit results
- [ ] Return recommended assets
- [ ] Write unit tests
  - [ ] Select 2 Nike products → should recommend other Nike products
  - [ ] Select luxury items → should recommend other luxury items

---

### Task 3.4: Search API Endpoints

**File:** `backend/app/api/reference_assets.py`

- [ ] Implement `GET /api/reference-assets/search` endpoint
  - [ ] Accept query parameters:
    - [ ] `q` (query string, required)
    - [ ] `asset_type` (optional filter)
    - [ ] `limit` (default 10, max 50)
  - [ ] Call `search_assets_by_text()`
  - [ ] Return list of assets with similarity scores
  - [ ] Include thumbnails in response
- [ ] Implement `GET /api/reference-assets/{asset_id}/similar` endpoint
  - [ ] Accept query parameters:
    - [ ] `limit` (default 10, max 50)
    - [ ] `exclude_self` (default true)
  - [ ] Verify asset ownership
  - [ ] Call `find_similar_assets()`
  - [ ] Return list of similar assets
- [ ] Implement `POST /api/reference-assets/check-duplicate` endpoint
  - [ ] Accept request body with image file (multipart)
  - [ ] Generate embedding for uploaded image
  - [ ] Call `check_duplicate_asset()`
  - [ ] Return potential duplicates with similarity scores
  - [ ] If duplicates found, suggest using existing asset
- [ ] Implement `POST /api/reference-assets/recommend` endpoint
  - [ ] Accept request body: `{"selected_asset_ids": ["id1", "id2"]}`
  - [ ] Call `recommend_style_consistent_assets()`
  - [ ] Return recommended assets
- [ ] Write integration tests for all endpoints

---

### Task 3.5: Frontend Search Bar

**File:** `frontend/src/components/AssetSearchBar.tsx`

- [ ] Create search bar component
- [ ] Implement text input with search icon
- [ ] Add debounced search (wait 300ms after typing stops)
- [ ] Call `/api/reference-assets/search` on input change
- [ ] Display results in dropdown
  - [ ] Show thumbnail + name
  - [ ] Show asset type badge
  - [ ] Show similarity score (if relevant)
- [ ] Click result → show detail modal
- [ ] Add "Clear" button to reset search
- [ ] Show loading indicator while searching
- [ ] Handle empty results gracefully
- [ ] Style with Tailwind CSS

**File:** `frontend/src/pages/ReferenceAssets.tsx`

- [ ] Add search bar to top of page
- [ ] When search active, show search results instead of full grid
- [ ] Add "Clear search" to return to full grid
- [ ] Highlight matching text in results (optional)

---

### Task 3.6: Duplicate Detection on Upload

**File:** `frontend/src/components/UploadAssetModal.tsx`

- [ ] After file selected, before upload:
  - [ ] Generate preview
  - [ ] Call `/api/reference-assets/check-duplicate` endpoint
  - [ ] If duplicates found (similarity > 0.95):
    - [ ] Show warning message
    - [ ] Display potential duplicate thumbnails
    - [ ] Offer options:
      - [ ] "Use existing asset" (cancel upload, select duplicate)
      - [ ] "Upload anyway" (proceed with upload)
  - [ ] If no duplicates, proceed normally
- [ ] Add loading state during duplicate check
- [ ] Style warning message prominently

---

### Task 3.7: "Find Similar" Feature

**File:** `frontend/src/components/AssetDetailModal.tsx`

- [ ] Add "Find Similar" button to asset detail modal
- [ ] On click:
  - [ ] Call `/api/reference-assets/{asset_id}/similar`
  - [ ] Show results in modal or new view
  - [ ] Display thumbnails of similar assets
  - [ ] Show similarity scores
  - [ ] Allow clicking to view those assets
- [ ] Add loading state
- [ ] Style with Tailwind CSS

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

- [ ] Users can search assets by text query
- [ ] Search results are semantically relevant (not just keyword matching)
- [ ] Users can find visually similar assets
- [ ] Duplicate detection warns before uploading duplicates
- [ ] Search latency is <500ms
- [ ] "Find Similar" feature works in detail modal
- [ ] Search results show similarity scores
- [ ] All tests pass
- [ ] Search works with 1000+ assets efficiently

---

# TDD-reference-assets-tasks-4.md