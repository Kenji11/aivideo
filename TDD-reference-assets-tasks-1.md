# TDD-reference-assets-tasks-1.md

## PR #1: Reference Asset Library Foundation & Database

**Goal:** Set up the core infrastructure for storing and managing reference assets with AI analysis.

**Estimated Time:** 3-4 days  
**Dependencies:** None

---

### Task 1.1: Database Schema & Models

**File:** `backend/app/common/models.py`

- [x] Install `pgvector` extension in PostgreSQL (if not already installed)
- [x] **Update existing `AssetType` enum** to reference asset content types:
  - [x] Change from: `IMAGE`, `VIDEO`, `AUDIO`
  - [x] Change to: `product`, `logo`, `person`, `environment`, `texture`, `prop`
  - [x] Note: The `assets` table was always meant for reference assets, consolidating now
- [x] Extend existing `Asset` model with reference asset fields:
  - [x] Add `name` column (String, nullable=True) - User-defined name (editable, defaults to filename)
  - [x] Add `description` column (String, nullable=True) - Optional user description
  - [x] Add `thumbnail_url` column (String, nullable=True) - Optimized thumbnail S3 URL
  - [x] Add `width` column (Integer, nullable=True) - Image width in pixels
  - [x] Add `height` column (Integer, nullable=True) - Image height in pixels
  - [x] Add `has_transparency` column (Boolean, default=False) - Whether image has alpha channel
  - [x] Add `analysis` column (JSON, nullable=True) - Full GPT-4V analysis response
  - [x] Add `primary_object` column (String, nullable=True, index=True) - "Nike Air Max sneaker"
  - [x] Add `colors` column (ARRAY(String), nullable=True) - ["white", "red", "black"]
  - [x] Add `dominant_colors_rgb` column (JSON, nullable=True) - [[255,255,255], [220,20,60]]
  - [x] Add `style_tags` column (ARRAY(String), nullable=True, index=True) - ["athletic", "modern", "clean"]
  - [x] Add `recommended_shot_types` column (ARRAY(String), nullable=True) - ["close_up", "hero_shot"]
  - [x] Add `usage_contexts` column (ARRAY(String), nullable=True) - ["product shots", "action scenes"]
  - [x] Add `is_logo` column (Boolean, default=False, index=True) - Logo detection flag
  - [x] Add `logo_position_preference` column (String, nullable=True) - "bottom-right", "top-left", etc.
  - [x] Add `embedding` column (Vector(512), nullable=True) - CLIP embedding for semantic search (ViT-B/32 produces 512-dim vectors)
  - [x] Add `updated_at` column (DateTime(timezone=True), nullable=True, onupdate=func.now())
  - [x] Add `usage_count` column (Integer, default=0) - Track how often used in videos
- [x] Add database indexes:
  - [x] Index on `asset_type` (already exists, but verify it works with new enum values)
  - [x] Index on `is_logo`
  - [x] IVFFlat index on `embedding` for vector search (using pgvector)
- [x] Create SQL migration script: `backend/migrations/004_add_reference_asset_fields.sql`
  - [x] Install pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
  - [x] **Alter existing `assettype` enum** to add new values (PostgreSQL doesn't support removing enum values easily, so we'll add new ones)
  - [x] **OR**: Create new enum and migrate (safer approach):
    - [x] Create new enum `reference_asset_type` with values: `product`, `logo`, `person`, `environment`, `texture`, `prop`
    - [x] Add column `reference_asset_type` (nullable, for new assets)
    - [x] Keep old `asset_type` column for backward compatibility during migration
    - [x] **Decision needed**: Full migration or gradual? For now, add new column and migrate enum later
  - [x] Add all new columns to `assets` table
  - [x] Create indexes
  - [x] Use `DO $$ BEGIN ... END $$;` blocks for idempotency
- [x] Test migration on dev database using `python migrate.py up`

---

### Task 1.2: S3 Storage Structure

**File:** `backend/app/common/constants.py` and `backend/app/services/s3.py`

- [x] Define S3 bucket structure (flat structure, preserve original filename):
  ```
  {user_id}/assets/
    nike_sneaker.png              # Original image (user's filename preserved)
    nike_sneaker_thumbnail.jpg    # Thumbnail (400x400, auto-generated)
    nike_sneaker_edges.png        # Preprocessed edges for ControlNet (optional, generated later)
  ```
  - [x] Note: S3 key uses original filename from user upload
  - [x] Thumbnails and preprocessed files use `{original_filename}_thumbnail.jpg` pattern
  - [x] S3 key should remain unchanged when user edits asset name in DB (name is separate from S3 key)
- [x] Add helper function in `constants.py`: `get_asset_s3_key(user_id: str, filename: str) -> str`
  - [x] Returns: `f"{user_id}/assets/{filename}"`
  - [x] Example: `get_asset_s3_key("user123", "nike_sneaker.png")` → `"user123/assets/nike_sneaker.png"`
- [x] Add helper function in `constants.py`: `get_asset_thumbnail_s3_key(user_id: str, filename: str) -> str`
  - [x] Returns: `f"{user_id}/assets/{base_name}_thumbnail.jpg"` (replaces extension with `_thumbnail.jpg`)
  - [x] Example: `get_asset_thumbnail_s3_key("user123", "nike_sneaker.png")` → `"user123/assets/nike_sneaker_thumbnail.jpg"`
- [x] **Update existing upload endpoint** (`backend/app/api/upload.py`):
  - [x] Change S3 key structure from `assets/{user_id}/{asset_id}/{filename}` to `{user_id}/assets/{filename}`
  - [x] Keep original filename as-is (sanitize for safety but preserve user's naming)
  - [x] Store original filename in `file_name` column (already done)
  - [x] Set `name` column to filename by default (user can edit later)
- [x] Add `upload_thumbnail()` method to `S3Client` class
  - [x] Accept PIL Image or file path, `user_id`, and `original_filename`
  - [x] Resize image to 400x400 (maintain aspect ratio, pad if needed)
  - [x] Optimize quality (JPEG 85% if JPEG, PNG if PNG)
  - [x] Generate S3 key using `get_asset_thumbnail_s3_key(user_id, original_filename)`
  - [x] Upload to S3
  - [x] Return S3 URL
- [x] Add `delete_asset_files()` method to `S3Client` class
  - [x] Accept `user_id` and `filename` (original filename)
  - [x] Delete all files for asset: `{filename}`, `{filename}_thumbnail.jpg`, `{filename}_edges.png`
  - [x] Use `list_files()` with prefix `{user_id}/assets/{base_name}` to find all related files
  - [x] Delete all matching files
- [x] Note: `generate_presigned_url()` already exists in S3Client, can be reused
- [x] Write unit tests for S3 operations

---

### Task 1.3: Base API Endpoints

**File:** `backend/app/api/upload.py` (extend existing)

- [x] **Update existing `POST /api/upload` endpoint**:
  - [x] Change S3 key structure from `assets/{user_id}/{asset_id}/{filename}` to `{user_id}/assets/{filename}`
  - [x] Accept optional fields in form data: `name`, `description`, `asset_type` (product/logo/person/etc)
  - [x] Validate file type (PNG, JPG, WEBP only for reference assets - keep existing validation for now)
  - [x] Validate file size (max 10MB for images - keep existing 100MB limit for other types)
  - [x] Extract image dimensions and file size using PIL (for images only)
  - [x] Check for transparency (alpha channel) using PIL (for images only)
  - [x] Upload original to S3 using new S3 key structure: `{user_id}/assets/{filename}`
  - [x] Generate and upload thumbnail using `upload_thumbnail()` → `{user_id}/assets/{filename}_thumbnail.jpg`
  - [x] Create/update database record in `assets` table:
    - [x] Set `asset_type` to provided value or default (product/logo/etc)
    - [x] Set `source = AssetSource.USER_UPLOAD`
    - [x] Set `s3_key` and `s3_url` for original image
    - [x] Set `thumbnail_url` for thumbnail
    - [x] Set `name` to provided value or default to `file_name` (user can edit later)
    - [x] Set `description`, `width`, `height`, `has_transparency`, `file_size_bytes`, `mime_type`
    - [x] Leave AI analysis fields null for now (will add in Task 2.5)
  - [x] Return asset metadata including new fields
- [x] **Update existing `GET /api/assets` endpoint**:
  - [x] Add query parameters:
    - [x] `asset_type` (optional): Filter by asset_type (product/logo/person/etc)
    - [x] `is_logo` (optional): Filter by is_logo (true/false)
    - [x] `limit` and `offset` for pagination
  - [x] Query user's assets from `assets` table where `source = USER_UPLOAD`
  - [x] Apply filters if provided
  - [x] Sort by `created_at` DESC (newest first)
  - [x] Return list of assets with thumbnails and all reference asset fields
- [x] **Add new `GET /api/assets/{asset_id}` endpoint**:
  - [x] Fetch single asset by ID from `assets` table
  - [x] Verify ownership (user_id matches current user)
  - [x] Return full asset details including all reference asset fields
- [x] **Add new `PATCH /api/assets/{asset_id}` endpoint**:
  - [x] Accept partial updates: `name`, `description`, `asset_type`, `logo_position_preference`
  - [x] Verify ownership
  - [x] Update database record (S3 key remains unchanged - only DB fields update)
  - [x] Return updated asset
- [x] **Add new `DELETE /api/assets/{asset_id}` endpoint**:
  - [x] Verify ownership
  - [x] Get asset record to find `file_name` (original filename)
  - [x] Delete from S3 using `delete_asset_files(user_id, file_name)`
  - [x] Delete from database (`assets` table)
  - [x] Return success response
- [x] Note: Authentication already handled by `get_current_user` dependency
- [x] Write API integration tests

---

### Task 1.4: Frontend Asset Library Page (Basic)

**File:** `frontend/src/pages/Assets.tsx` (or extend existing if it exists)

- [x] Create new page component `Assets` (or update existing)
- [x] Add route to React Router: `/assets`
- [x] Implement asset grid layout
  - [x] Display thumbnails in responsive grid (3-4 columns)
  - [x] Show asset name below thumbnail
  - [x] Show asset type badge (product/logo/etc)
- [x] Implement upload button
  - [x] Open file picker on click
  - [x] Show upload progress indicator
  - [x] Display success/error toast
  - [x] Refresh grid after successful upload
- [x] Implement delete functionality
  - [x] Add delete icon on thumbnail hover
  - [x] Show confirmation modal
  - [x] Delete asset and refresh grid
- [x] Add empty state
  - [x] Show friendly message when no assets
  - [x] Large "Upload First Asset" button
- [x] Add loading states (skeleton loaders)
- [x] Add error handling (display error messages)
- [x] Add pagination controls (if >20 assets)
- [x] Style with Tailwind CSS

---

### Task 1.5: Upload Modal Component

**File:** `frontend/src/components/UploadAssetModal.tsx`

- [x] Create modal component with drag-and-drop zone
- [x] Implement drag-and-drop functionality
  - [x] Highlight drop zone on drag over
  - [x] Accept PNG, JPG, WEBP files
  - [x] Show file preview after drop
- [x] Add manual file selection fallback
  - [x] Click drop zone to open file picker
- [x] Add optional metadata fields
  - [x] Asset name (text input)
  - [x] Asset type (dropdown: product/logo/person/environment/texture/prop)
  - [x] Description (textarea, optional)
- [x] Show file preview before upload
  - [x] Display thumbnail
  - [x] Show file name and size
- [x] Implement upload with progress
  - [x] Upload to API endpoint
  - [x] Show progress bar (0-100%)
  - [x] Handle upload errors
- [x] Add validation
  - [x] File size limit (10MB)
  - [x] File type validation
  - [x] Asset name required (unless auto-generated)
- [x] Close modal on success
- [x] Call parent callback to refresh asset list
- [x] Style with Tailwind CSS

---

### Task 1.6: Testing & Documentation

**Tests:**
- [x] Write unit tests for extended `Asset` model (reference asset fields)
- [x] Write unit tests for S3 upload/delete operations
- [x] Write API integration tests for all endpoints
- [x] Write frontend component tests (upload modal, asset grid)
- [x] Test with various image formats (PNG with/without alpha, JPG, WEBP)
- [x] Test file size limits
- [x] Test concurrent uploads
- [x] Test pagination with 100+ assets

**Documentation:**
- [x] Add API documentation (OpenAPI/Swagger)
- [x] Document S3 bucket structure: `{user_id}/assets/` for reference assets
- [x] Document database schema changes (new columns on `assets` table)
- [x] Add developer guide for reference assets
- [x] Update main README with new feature

**Deployment:**
- [x] Run database migration on staging: `python migrate.py up`
- [x] Test on staging environment
- [x] Verify S3 bucket exists and has appropriate policies
- [x] Deploy to production
- [x] Run migration on production: `python migrate.py up`
- [x] Verify production works

---

### Acceptance Criteria

- [x] Users can upload images to reference asset library
- [x] Uploaded images are stored in S3 with proper structure
- [x] Thumbnails are automatically generated
- [x] Assets are saved to database with metadata
- [x] Users can view all their assets in a grid
- [x] Users can delete assets (removes from S3 and DB)
- [x] Upload progress is shown during upload
- [x] File type and size validation works
- [x] Pagination works for users with many assets
- [x] All tests pass
- [x] Documentation is complete

---

# TDD-reference-assets-tasks-2.md

## PR #2: AI Analysis & Categorization

**Goal:** Integrate GPT-4o Vision and embedding service for automatic asset analysis and embedding generation.

**Estimated Time:** 3-4 days  
**Dependencies:** PR #1

**Decisions Made:**
- Use `gpt-4o` model (not `gpt-4-vision-preview`) for consistency with codebase
- Use existing `backend/app/api/upload.py` file (not create new `reference_assets.py`)
- Keep image in memory during upload (for CLIP embedding generation)
- Upload endpoint returns success immediately after S3/DB save; analysis runs in background
- **Single GPT-4o Call:** One comprehensive API call returns all analysis fields in JSON (simpler, faster, cheaper than multiple calls)
  - GPT-4o handles: asset_type, colors, dominant_colors_rgb, style_tags, shot_types, usage_contexts, logo detection
  - No separate CV2 color extraction or heuristic logo detection needed (GPT-4o does it all)
- If GPT-4o analysis fails, skip CLIP embedding generation (don't generate embeddings)
- **CLIP Implementation:** Use self-hosted CLIP with ViT-B/32 (512 dimensions, 350MB model)
- **Model Caching:** Docker volume caching (`/mnt/models`) - downloads once, cached forever
- **Embedding Dimensions:** 512 (not 768) - matches ViT-B/32 output

---

### Task 2.0: Install Dependencies & Docker Configuration

**File:** `backend/requirements.txt`

- [x] Add CLIP dependencies:
  - [x] `torch>=2.0.0` (CPU version recommended for smaller image)
  - [x] `torchvision>=0.15.0`
  - [x] `clip-by-openai>=1.0`
  - [x] `pillow>=9.0.0` (already installed, verify version)
- [x] Add other required packages:
  - [x] `opencv-python` (for logo detection and color extraction)
  - [x] `scikit-learn` (for K-means clustering in color extraction)

**File:** `backend/Dockerfile`

- [x] Install system dependencies for OpenCV:
  - [x] `libglib2.0-0`, `libsm6`, `libxext6`, `libxrender-dev`
- [x] Install PyTorch CPU version (smaller than GPU version):
  - [x] Use `--index-url https://download.pytorch.org/whl/cpu`
- [x] Set environment variables:
  - [x] `ENV CLIP_MODEL=ViT-B/32`
  - [x] `ENV CLIP_MODEL_CACHE=/mnt/models`

**File:** `backend/docker-compose.yml`

- [x] Add Docker volume for CLIP model cache:
  - [x] Create volume: `clip-models:/mnt/models`
  - [x] Mount volume to backend service
- [x] Add environment variables to backend service:
  - [x] `CLIP_MODEL=ViT-B/32`
  - [x] `CLIP_MODEL_CACHE=/mnt/models`

### Task 2.1: CLIP Embedding Service

**File:** `backend/app/services/clip_embeddings.py`

- [x] Create `CLIPEmbeddingService` class
- [x] Implement model loading with volume caching:
  - [x] Load CLIP model: `ViT-B/32` (512 dimensions, 350MB model)
  - [x] Use `@lru_cache(maxsize=1)` decorator for singleton pattern
  - [x] Configure model cache directory: `/mnt/models` (from `CLIP_MODEL_CACHE` env var)
  - [x] Use `clip.load()` with `download_root=MODEL_CACHE_DIR` parameter
  - [x] Model downloads to volume on first run (~15-20s), loads from cache on subsequent runs (~3-5s)
  - [x] Detect GPU availability, fallback to CPU
- [x] Implement `generate_image_embedding(image: PIL.Image) -> list[float]`
  - [x] Accept PIL Image (from memory, not file path)
  - [x] Preprocess image for CLIP using loaded preprocess function
  - [x] Encode image to embedding
  - [x] Normalize embedding (L2 norm)
  - [x] Return as list of 512 floats (ViT-B/32 produces 512-dim embeddings)
- [x] Implement `generate_text_embedding(text: str) -> list[float]`
  - [x] Tokenize text using `clip.tokenize()`
  - [x] Encode text to embedding
  - [x] Normalize embedding (L2 norm)
  - [x] Return as list of 512 floats
- [x] Add error handling:
  - [x] Handle corrupted images
  - [x] Handle CUDA out of memory (fallback to CPU)
  - [x] Handle model download failures
  - [x] Log model loading time (cold start vs warm start)
- [x] Add optional caching (cache embeddings in Redis for frequently accessed assets)
- [x] Write unit tests:
  - [x] Test with sample images
  - [x] Test with various text queries
  - [x] Verify embedding dimensions (512)
  - [x] Verify normalization (magnitude ≈ 1.0)
  - [x] Test cold start (first load with download)
  - [x] Test warm start (load from cache)
  - [x] Verify volume persistence (restart container, no re-download)

---

### Task 2.2: GPT-4o Vision Analysis Service (Single Comprehensive Call)

**File:** `backend/app/services/asset_analysis.py`

**Approach:** Single GPT-4o API call returns all analysis fields in JSON format. Simpler, faster, cheaper than multiple calls.

- [ ] Create `AssetAnalysisService` class
- [ ] Implement `analyze_reference_asset(image_url: str, user_provided_name: str, user_provided_description: str) -> dict`
  - [ ] Accept S3 URL (presigned URL for GPT-4o API) and user context
  - [ ] Note: PIL Image not needed here (GPT-4o uses URL)
- [ ] Build comprehensive GPT-4o prompt requesting ALL fields in one JSON response:
  - [ ] `asset_type`: product/logo/person/environment/texture/prop
  - [ ] `primary_object`: detailed description of main subject
  - [ ] `colors`: array of color names (e.g., ["white", "red", "black"])
  - [ ] `dominant_colors_rgb`: array of RGB arrays (e.g., [[255,255,255], [220,20,60]])
  - [ ] `style_tags`: array of style descriptors (e.g., ["athletic", "modern", "clean"])
  - [ ] `recommended_shot_types`: array of shot types (e.g., ["close_up", "hero_shot"])
  - [ ] `usage_contexts`: array of usage contexts (e.g., ["product shots", "action scenes"])
  - [ ] `is_logo`: boolean (logo detection)
  - [ ] `logo_position_preference`: string if logo detected (e.g., "bottom-right")
  - [ ] `confidence`: float 0.0-1.0
- [ ] Call OpenAI GPT-4o API with structured JSON response:
  - [ ] Model: `gpt-4o` (consistent with codebase)
  - [ ] Pass image URL (presigned S3 URL) in `image_url` format
  - [ ] Use `response_format={"type": "json_object"}` for guaranteed JSON
  - [ ] Pass user-provided context (name, description) in prompt
  - [ ] Set max_tokens to 1000
- [ ] Parse and validate response:
  - [ ] Extract JSON from response (should be clean JSON due to response_format)
  - [ ] Validate all required fields present
  - [ ] Validate data types (arrays are arrays, booleans are booleans, etc.)
  - [ ] Handle malformed JSON gracefully (fallback to empty analysis)
- [ ] Add retry logic:
  - [ ] Retry up to 3 times on API errors (rate limits, network errors)
  - [ ] Exponential backoff between retries
  - [ ] Log retry attempts
- [ ] Add cost tracking:
  - [ ] Log tokens used (input + output)
  - [ ] Calculate cost (~$0.01-0.03 per image for GPT-4o vision)
  - [ ] Log cost per analysis
- [ ] Write unit tests:
  - [ ] Test with sample product image → verify product type, colors, style tags
  - [ ] Test with logo image → verify is_logo=true, logo_position_preference
  - [ ] Test with person image → verify person type
  - [ ] Test with environment image → verify environment type
  - [ ] Verify JSON structure matches expected schema
  - [ ] Test error handling (API failures, malformed JSON, network errors)
  - [ ] Test retry logic

---

### Task 2.3: (SKIPPED - Handled by GPT-4o)

**Note:** Dominant color extraction and logo detection are now handled by GPT-4o in Task 2.2. No separate services needed.

**Optional Fallback (Future Enhancement):**
- If GPT-4o color extraction is inaccurate, we can add CV2-based color extraction as fallback
- If GPT-4o logo detection is unreliable, we can add heuristic-based logo detection as fallback
- For MVP, GPT-4o analysis is sufficient

---

### Task 2.5: Integrate Analysis into Upload Flow

**File:** `backend/app/api/upload.py` (existing file)

- [ ] Update existing `POST /api/upload` endpoint
- [ ] **Upload flow:**
  1. [ ] Save file to S3 (keep image in memory for CLIP embedding)
  2. [ ] Save asset record to database (basic metadata only)
  3. [ ] **Return success immediately** (don't wait for analysis)
  4. [ ] Trigger background analysis task (see below)
- [ ] **Background analysis:** Evaluate options for async processing
  - [ ] Option A: Celery task (consistent with existing architecture)
  - [ ] Option B: FastAPI BackgroundTasks (simpler, no infrastructure)
  - [ ] **Decision needed:** Which approach to use?
- [ ] Create background analysis function/task:
  - [ ] Accept: `asset_id`, `s3_url`, `image` (PIL Image from memory), `user_provided_name`, `user_provided_description`
  - [ ] **Step 1: GPT-4o Analysis** (single comprehensive call)
    - [ ] Call `analyze_reference_asset(s3_url, user_provided_name, user_provided_description)`
    - [ ] Returns JSON with all fields: asset_type, primary_object, colors, dominant_colors_rgb, style_tags, recommended_shot_types, usage_contexts, is_logo, logo_position_preference, confidence
    - [ ] Store full analysis JSON in `analysis` field
    - [ ] Extract and store individual fields in database columns
  - [ ] **Step 2: CLIP Embedding** (only if GPT-4o succeeded)
    - [ ] Call `generate_image_embedding(image)` with PIL Image from memory
    - [ ] Store embedding in `embedding` field (pgvector, 512 dimensions)
  - [ ] Update database record with all analysis results
- [ ] **Error handling:**
  - [ ] If GPT-4o analysis fails, **skip CLIP embedding** (don't generate embeddings)
  - [ ] Log error for debugging
  - [ ] Asset remains in database with basic metadata (no analysis)
  - [ ] Retry logic handled in AssetAnalysisService
- [ ] **Frontend:** Update to handle async analysis
  - [ ] Show "Upload successful" immediately
  - [ ] Show "Analysis in progress..." indicator
  - [ ] Poll or use WebSocket to update when analysis completes
  - [ ] Display analysis results when available

---

### Task 2.6: Display Analysis Results in Frontend

**File:** `frontend/src/components/AssetDetailModal.tsx`

- [ ] Create new modal component for viewing asset details
- [ ] Display full-size image preview
- [ ] Display AI analysis results
  - [ ] Primary object description
  - [ ] Detected colors (color swatches)
  - [ ] Style tags (badges)
  - [ ] Recommended shot types (chips)
  - [ ] Usage contexts (list)
- [ ] Display logo detection result
  - [ ] Show "Logo Detected" badge if `is_logo = true`
  - [ ] Show confidence score
- [ ] Display metadata
  - [ ] File size, dimensions
  - [ ] Upload date
  - [ ] Usage count (how many times used in videos)
- [ ] Add edit functionality
  - [ ] Allow editing name
  - [ ] Allow editing description
  - [ ] Allow editing asset type
  - [ ] Allow setting logo position preference (if logo)
  - [ ] Save button → PATCH endpoint
- [ ] Add delete button
  - [ ] Confirmation modal
  - [ ] Delete and close modal
- [ ] Style with Tailwind CSS
- [ ] Open modal when clicking asset in grid

**File:** `frontend/src/pages/Assets.tsx`

- [ ] Update grid to show AI-detected asset type badge
- [ ] Add filter by asset type (dropdown)
- [ ] Add filter by logo (checkbox: "Show logos only")
- [ ] Show primary object description on hover
- [ ] Add "AI Analyzed" indicator icon

---

### Task 2.7: Backend PATCH Endpoint

**File:** `backend/app/api/upload.py` (existing file)

- [ ] Update existing `PATCH /api/assets/{asset_id}` endpoint (if exists) OR create new one
- [ ] Accept partial updates:
  - [ ] `name` (optional)
  - [ ] `description` (optional)
  - [ ] `asset_type` (optional)
  - [ ] `logo_position_preference` (optional, only if is_logo=true)
- [ ] Verify ownership
- [ ] Update database record
- [ ] Return updated asset
- [ ] Write integration test

---

### Task 2.8: Testing & Validation

**Integration Tests:**
- [ ] Upload product image → verify analysis returns product type
- [ ] Upload logo image → verify `is_logo = true`
- [ ] Upload person photo → verify analysis returns person type
- [ ] Verify embeddings are 512 dimensions (ViT-B/32 output)
- [ ] Verify dominant colors are valid RGB values
- [ ] Test with various image formats (PNG, JPG, WEBP)

**Manual QA:**
- [ ] Upload 10 diverse images
- [ ] Review AI analysis results for accuracy
- [ ] Verify logo detection accuracy (test with 5 logos, 5 non-logos)
- [ ] Check that embeddings are stored correctly
- [ ] Verify frontend displays analysis results nicely

**Performance:**
- [ ] Measure upload + analysis latency (target: <5s for upload, analysis runs in background)
- [ ] Test with large images (5MB+)
- [ ] Test concurrent uploads (10 simultaneous)
- [ ] **CLIP Model Performance:**
  - [ ] Measure cold start time (first run with model download): ~15-20s expected
  - [ ] Measure warm start time (cached model load): ~3-5s expected
  - [ ] Verify embedding generation latency: <2s per image (CPU)
  - [ ] Test volume persistence: restart container, verify no re-download
  - [ ] Verify Docker volume created: `docker volume ls | grep clip-models`
  - [ ] Verify model cached: `docker exec backend ls -lh /mnt/models/`
  - [ ] Verify model size: ~350MB for ViT-B/32.pt

---

### Acceptance Criteria

- [ ] All uploaded images are automatically analyzed with GPT-4o (in background)
- [ ] Single GPT-4o call returns comprehensive JSON with all fields:
  - [ ] asset_type, primary_object, colors, dominant_colors_rgb
  - [ ] style_tags, recommended_shot_types, usage_contexts
  - [ ] is_logo, logo_position_preference (if logo detected)
  - [ ] confidence score
- [ ] CLIP embeddings (512-dim, ViT-B/32) are generated and stored in pgvector (only if GPT-4o succeeds)
- [ ] Logo detection works with reasonable accuracy (via GPT-4o)
- [ ] Dominant colors are extracted accurately (via GPT-4o, RGB arrays)
- [ ] Frontend displays analysis results in detail modal
- [ ] Users can edit asset metadata
- [ ] Upload returns success immediately (<2s), analysis runs in background
- [ ] CLIP model loads from Docker volume cache (warm start ~3-5s)
- [ ] All tests pass