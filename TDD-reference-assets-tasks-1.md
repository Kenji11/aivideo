# TDD-reference-assets-tasks-1.md

## PR #1: Reference Asset Library Foundation & Database

**Goal:** Set up the core infrastructure for storing and managing reference assets with AI analysis.

**Estimated Time:** 3-4 days  
**Dependencies:** None

---

### Task 1.1: Database Schema & Models

**File:** `backend/app/common/models.py`

- [ ] Install `pgvector` extension in PostgreSQL (if not already installed)
- [ ] **Update existing `AssetType` enum** to reference asset content types:
  - [ ] Change from: `IMAGE`, `VIDEO`, `AUDIO`
  - [ ] Change to: `product`, `logo`, `person`, `environment`, `texture`, `prop`
  - [ ] Note: The `assets` table was always meant for reference assets, consolidating now
- [ ] Extend existing `Asset` model with reference asset fields:
  - [ ] Add `name` column (String, nullable=True) - User-defined name (editable, defaults to filename)
  - [ ] Add `description` column (String, nullable=True) - Optional user description
  - [ ] Add `thumbnail_url` column (String, nullable=True) - Optimized thumbnail S3 URL
  - [ ] Add `width` column (Integer, nullable=True) - Image width in pixels
  - [ ] Add `height` column (Integer, nullable=True) - Image height in pixels
  - [ ] Add `has_transparency` column (Boolean, default=False) - Whether image has alpha channel
  - [ ] Add `analysis` column (JSON, nullable=True) - Full GPT-4V analysis response
  - [ ] Add `primary_object` column (String, nullable=True, index=True) - "Nike Air Max sneaker"
  - [ ] Add `colors` column (ARRAY(String), nullable=True) - ["white", "red", "black"]
  - [ ] Add `dominant_colors_rgb` column (JSON, nullable=True) - [[255,255,255], [220,20,60]]
  - [ ] Add `style_tags` column (ARRAY(String), nullable=True, index=True) - ["athletic", "modern", "clean"]
  - [ ] Add `recommended_shot_types` column (ARRAY(String), nullable=True) - ["close_up", "hero_shot"]
  - [ ] Add `usage_contexts` column (ARRAY(String), nullable=True) - ["product shots", "action scenes"]
  - [ ] Add `is_logo` column (Boolean, default=False, index=True) - Logo detection flag
  - [ ] Add `logo_position_preference` column (String, nullable=True) - "bottom-right", "top-left", etc.
  - [ ] Add `embedding` column (Vector(768), nullable=True) - CLIP embedding for semantic search
  - [ ] Add `updated_at` column (DateTime(timezone=True), nullable=True, onupdate=func.now())
  - [ ] Add `usage_count` column (Integer, default=0) - Track how often used in videos
- [ ] Add database indexes:
  - [ ] Index on `asset_type` (already exists, but verify it works with new enum values)
  - [ ] Index on `is_logo`
  - [ ] IVFFlat index on `embedding` for vector search (using pgvector)
- [ ] Create SQL migration script: `backend/migrations/004_add_reference_asset_fields.sql`
  - [ ] Install pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector;`
  - [ ] **Alter existing `assettype` enum** to add new values (PostgreSQL doesn't support removing enum values easily, so we'll add new ones)
  - [ ] **OR**: Create new enum and migrate (safer approach):
    - [ ] Create new enum `reference_asset_type` with values: `product`, `logo`, `person`, `environment`, `texture`, `prop`
    - [ ] Add column `reference_asset_type` (nullable, for new assets)
    - [ ] Keep old `asset_type` column for backward compatibility during migration
    - [ ] **Decision needed**: Full migration or gradual? For now, add new column and migrate enum later
  - [ ] Add all new columns to `assets` table
  - [ ] Create indexes
  - [ ] Use `DO $$ BEGIN ... END $$;` blocks for idempotency
- [ ] Test migration on dev database using `python migrate.py up`

---

### Task 1.2: S3 Storage Structure

**File:** `backend/app/common/constants.py` and `backend/app/services/s3.py`

- [ ] Define S3 bucket structure (flat structure, preserve original filename):
  ```
  {user_id}/assets/
    nike_sneaker.png              # Original image (user's filename preserved)
    nike_sneaker_thumbnail.jpg    # Thumbnail (400x400, auto-generated)
    nike_sneaker_edges.png        # Preprocessed edges for ControlNet (optional, generated later)
  ```
  - [ ] Note: S3 key uses original filename from user upload
  - [ ] Thumbnails and preprocessed files use `{original_filename}_thumbnail.jpg` pattern
  - [ ] S3 key should remain unchanged when user edits asset name in DB (name is separate from S3 key)
- [ ] Add helper function in `constants.py`: `get_asset_s3_key(user_id: str, filename: str) -> str`
  - [ ] Returns: `f"{user_id}/assets/{filename}"`
  - [ ] Example: `get_asset_s3_key("user123", "nike_sneaker.png")` → `"user123/assets/nike_sneaker.png"`
- [ ] Add helper function in `constants.py`: `get_asset_thumbnail_s3_key(user_id: str, filename: str) -> str`
  - [ ] Returns: `f"{user_id}/assets/{base_name}_thumbnail.jpg"` (replaces extension with `_thumbnail.jpg`)
  - [ ] Example: `get_asset_thumbnail_s3_key("user123", "nike_sneaker.png")` → `"user123/assets/nike_sneaker_thumbnail.jpg"`
- [ ] **Update existing upload endpoint** (`backend/app/api/upload.py`):
  - [ ] Change S3 key structure from `assets/{user_id}/{asset_id}/{filename}` to `{user_id}/assets/{filename}`
  - [ ] Keep original filename as-is (sanitize for safety but preserve user's naming)
  - [ ] Store original filename in `file_name` column (already done)
  - [ ] Set `name` column to filename by default (user can edit later)
- [ ] Add `upload_thumbnail()` method to `S3Client` class
  - [ ] Accept PIL Image or file path, `user_id`, and `original_filename`
  - [ ] Resize image to 400x400 (maintain aspect ratio, pad if needed)
  - [ ] Optimize quality (JPEG 85% if JPEG, PNG if PNG)
  - [ ] Generate S3 key using `get_asset_thumbnail_s3_key(user_id, original_filename)`
  - [ ] Upload to S3
  - [ ] Return S3 URL
- [ ] Add `delete_asset_files()` method to `S3Client` class
  - [ ] Accept `user_id` and `filename` (original filename)
  - [ ] Delete all files for asset: `{filename}`, `{filename}_thumbnail.jpg`, `{filename}_edges.png`
  - [ ] Use `list_files()` with prefix `{user_id}/assets/{base_name}` to find all related files
  - [ ] Delete all matching files
- [ ] Note: `generate_presigned_url()` already exists in S3Client, can be reused
- [ ] Write unit tests for S3 operations

---

### Task 1.3: Base API Endpoints

**File:** `backend/app/api/upload.py` (extend existing)

- [ ] **Update existing `POST /api/upload` endpoint**:
  - [ ] Change S3 key structure from `assets/{user_id}/{asset_id}/{filename}` to `{user_id}/assets/{filename}`
  - [ ] Accept optional fields in form data: `name`, `description`, `asset_type` (product/logo/person/etc)
  - [ ] Validate file type (PNG, JPG, WEBP only for reference assets - keep existing validation for now)
  - [ ] Validate file size (max 10MB for images - keep existing 100MB limit for other types)
  - [ ] Extract image dimensions and file size using PIL (for images only)
  - [ ] Check for transparency (alpha channel) using PIL (for images only)
  - [ ] Upload original to S3 using new S3 key structure: `{user_id}/assets/{filename}`
  - [ ] Generate and upload thumbnail using `upload_thumbnail()` → `{user_id}/assets/{filename}_thumbnail.jpg`
  - [ ] Create/update database record in `assets` table:
    - [ ] Set `asset_type` to provided value or default (product/logo/etc)
    - [ ] Set `source = AssetSource.USER_UPLOAD`
    - [ ] Set `s3_key` and `s3_url` for original image
    - [ ] Set `thumbnail_url` for thumbnail
    - [ ] Set `name` to provided value or default to `file_name` (user can edit later)
    - [ ] Set `description`, `width`, `height`, `has_transparency`, `file_size_bytes`, `mime_type`
    - [ ] Leave AI analysis fields null for now (will add in Task 2.5)
  - [ ] Return asset metadata including new fields
- [ ] **Update existing `GET /api/assets` endpoint**:
  - [ ] Add query parameters:
    - [ ] `asset_type` (optional): Filter by asset_type (product/logo/person/etc)
    - [ ] `is_logo` (optional): Filter by is_logo (true/false)
    - [ ] `limit` and `offset` for pagination
  - [ ] Query user's assets from `assets` table where `source = USER_UPLOAD`
  - [ ] Apply filters if provided
  - [ ] Sort by `created_at` DESC (newest first)
  - [ ] Return list of assets with thumbnails and all reference asset fields
- [ ] **Add new `GET /api/assets/{asset_id}` endpoint**:
  - [ ] Fetch single asset by ID from `assets` table
  - [ ] Verify ownership (user_id matches current user)
  - [ ] Return full asset details including all reference asset fields
- [ ] **Add new `PATCH /api/assets/{asset_id}` endpoint**:
  - [ ] Accept partial updates: `name`, `description`, `asset_type`, `logo_position_preference`
  - [ ] Verify ownership
  - [ ] Update database record (S3 key remains unchanged - only DB fields update)
  - [ ] Return updated asset
- [ ] **Add new `DELETE /api/assets/{asset_id}` endpoint**:
  - [ ] Verify ownership
  - [ ] Get asset record to find `file_name` (original filename)
  - [ ] Delete from S3 using `delete_asset_files(user_id, file_name)`
  - [ ] Delete from database (`assets` table)
  - [ ] Return success response
- [ ] Note: Authentication already handled by `get_current_user` dependency
- [ ] Write API integration tests

---

### Task 1.4: Frontend Asset Library Page (Basic)

**File:** `frontend/src/pages/Assets.tsx` (or extend existing if it exists)

- [ ] Create new page component `Assets` (or update existing)
- [ ] Add route to React Router: `/assets`
- [ ] Implement asset grid layout
  - [ ] Display thumbnails in responsive grid (3-4 columns)
  - [ ] Show asset name below thumbnail
  - [ ] Show asset type badge (product/logo/etc)
- [ ] Implement upload button
  - [ ] Open file picker on click
  - [ ] Show upload progress indicator
  - [ ] Display success/error toast
  - [ ] Refresh grid after successful upload
- [ ] Implement delete functionality
  - [ ] Add delete icon on thumbnail hover
  - [ ] Show confirmation modal
  - [ ] Delete asset and refresh grid
- [ ] Add empty state
  - [ ] Show friendly message when no assets
  - [ ] Large "Upload First Asset" button
- [ ] Add loading states (skeleton loaders)
- [ ] Add error handling (display error messages)
- [ ] Add pagination controls (if >20 assets)
- [ ] Style with Tailwind CSS

---

### Task 1.5: Upload Modal Component

**File:** `frontend/src/components/UploadAssetModal.tsx`

- [ ] Create modal component with drag-and-drop zone
- [ ] Implement drag-and-drop functionality
  - [ ] Highlight drop zone on drag over
  - [ ] Accept PNG, JPG, WEBP files
  - [ ] Show file preview after drop
- [ ] Add manual file selection fallback
  - [ ] Click drop zone to open file picker
- [ ] Add optional metadata fields
  - [ ] Asset name (text input)
  - [ ] Asset type (dropdown: product/logo/person/environment/texture/prop)
  - [ ] Description (textarea, optional)
- [ ] Show file preview before upload
  - [ ] Display thumbnail
  - [ ] Show file name and size
- [ ] Implement upload with progress
  - [ ] Upload to API endpoint
  - [ ] Show progress bar (0-100%)
  - [ ] Handle upload errors
- [ ] Add validation
  - [ ] File size limit (10MB)
  - [ ] File type validation
  - [ ] Asset name required (unless auto-generated)
- [ ] Close modal on success
- [ ] Call parent callback to refresh asset list
- [ ] Style with Tailwind CSS

---

### Task 1.6: Testing & Documentation

**Tests:**
- [ ] Write unit tests for extended `Asset` model (reference asset fields)
- [ ] Write unit tests for S3 upload/delete operations
- [ ] Write API integration tests for all endpoints
- [ ] Write frontend component tests (upload modal, asset grid)
- [ ] Test with various image formats (PNG with/without alpha, JPG, WEBP)
- [ ] Test file size limits
- [ ] Test concurrent uploads
- [ ] Test pagination with 100+ assets

**Documentation:**
- [ ] Add API documentation (OpenAPI/Swagger)
- [ ] Document S3 bucket structure: `{user_id}/assets/` for reference assets
- [ ] Document database schema changes (new columns on `assets` table)
- [ ] Add developer guide for reference assets
- [ ] Update main README with new feature

**Deployment:**
- [ ] Run database migration on staging: `python migrate.py up`
- [ ] Test on staging environment
- [ ] Verify S3 bucket exists and has appropriate policies
- [ ] Deploy to production
- [ ] Run migration on production: `python migrate.py up`
- [ ] Verify production works

---

### Acceptance Criteria

- [ ] Users can upload images to reference asset library
- [ ] Uploaded images are stored in S3 with proper structure
- [ ] Thumbnails are automatically generated
- [ ] Assets are saved to database with metadata
- [ ] Users can view all their assets in a grid
- [ ] Users can delete assets (removes from S3 and DB)
- [ ] Upload progress is shown during upload
- [ ] File type and size validation works
- [ ] Pagination works for users with many assets
- [ ] All tests pass
- [ ] Documentation is complete

---

# TDD-reference-assets-tasks-2.md

## PR #2: AI Analysis & Categorization

**Goal:** Integrate GPT-4 Vision and CLIP for automatic asset analysis and embedding generation.

**Estimated Time:** 3-4 days  
**Dependencies:** PR #1

---

### Task 2.1: CLIP Embedding Service

**File:** `backend/app/services/clip_embeddings.py`

- [ ] Install dependencies: `pip install torch clip-by-openai pillow`
- [ ] Create `CLIPEmbeddingService` class
- [ ] Implement model loading
  - [ ] Load CLIP model: `ViT-L/14` (768 dimensions)
  - [ ] Cache model in memory (singleton pattern)
  - [ ] Detect GPU availability, fallback to CPU
- [ ] Implement `generate_image_embedding(image_path: str) -> list[float]`
  - [ ] Load image with PIL
  - [ ] Preprocess image for CLIP
  - [ ] Encode image to embedding
  - [ ] Normalize embedding (L2 norm)
  - [ ] Return as list of 768 floats
- [ ] Implement `generate_text_embedding(text: str) -> list[float]`
  - [ ] Tokenize text
  - [ ] Encode text to embedding
  - [ ] Normalize embedding
  - [ ] Return as list of 768 floats
- [ ] Add error handling
  - [ ] Handle corrupted images
  - [ ] Handle CUDA out of memory
  - [ ] Fallback to CPU if needed
- [ ] Add caching (optional: cache embeddings in Redis)
- [ ] Write unit tests
  - [ ] Test with sample images
  - [ ] Test with various text queries
  - [ ] Verify embedding dimensions (768)
  - [ ] Verify normalization (magnitude ≈ 1.0)

---

### Task 2.2: GPT-4 Vision Analysis Service

**File:** `backend/app/services/asset_analysis.py`

- [ ] Create `AssetAnalysisService` class
- [ ] Implement `analyze_reference_asset(image_url: str, user_provided_name: str, user_provided_description: str) -> dict`
- [ ] Build comprehensive GPT-4V prompt
  - [ ] Include instructions for extracting: asset_type, primary_object, colors, style_tags, recommended_shot_types, usage_contexts
  - [ ] Request JSON response format
  - [ ] Include examples for clarity
- [ ] Call OpenAI GPT-4 Vision API
  - [ ] Model: `gpt-4-vision-preview`
  - [ ] Pass image URL
  - [ ] Pass user-provided context (name, description)
  - [ ] Request JSON response
  - [ ] Set max_tokens to 1000
- [ ] Parse response
  - [ ] Extract JSON from response
  - [ ] Validate required fields present
  - [ ] Handle malformed JSON gracefully
- [ ] Add retry logic
  - [ ] Retry up to 3 times on API errors
  - [ ] Exponential backoff
- [ ] Add cost tracking
  - [ ] Log tokens used
  - [ ] Calculate cost ($0.01-0.03 per image)
- [ ] Write unit tests
  - [ ] Test with sample product image
  - [ ] Test with logo image
  - [ ] Test with person image
  - [ ] Verify JSON structure
  - [ ] Test error handling

---

### Task 2.3: Dominant Color Extraction

**File:** `backend/app/services/asset_analysis.py`

- [ ] Install dependencies: `pip install opencv-python scikit-learn`
- [ ] Implement `extract_dominant_colors(image_url: str, n_colors: int = 5) -> list[list[int]]`
- [ ] Download image from URL
- [ ] Convert to RGB color space
- [ ] Reshape image to list of pixels
- [ ] Apply K-means clustering
  - [ ] n_clusters = n_colors (default 5)
  - [ ] Use sklearn.cluster.KMeans
  - [ ] Random state for reproducibility
- [ ] Extract cluster centers (dominant colors)
- [ ] Convert to integer RGB values
- [ ] Return as list of [R, G, B] arrays
- [ ] Add error handling
  - [ ] Handle grayscale images
  - [ ] Handle images with few unique colors
- [ ] Write unit tests
  - [ ] Test with colorful product image
  - [ ] Test with mostly black/white image
  - [ ] Verify output format: [[R,G,B], [R,G,B], ...]

---

### Task 2.4: Logo Detection Service

**File:** `backend/app/services/logo_detection.py`

- [ ] Create `LogoDetectionService` class
- [ ] Implement `detect_logo(image_path: str) -> dict`
- [ ] Check for transparency (alpha channel)
  - [ ] Open image with PIL
  - [ ] Check if mode == 'RGBA'
  - [ ] Check if any alpha < 255
  - [ ] Score: +0.3 if transparent
- [ ] Check file size vs dimensions
  - [ ] Calculate bytes per pixel
  - [ ] If < 0.5 bytes/pixel → simple graphics
  - [ ] Score: +0.2 if simple
- [ ] Check color palette size
  - [ ] Convert to grayscale
  - [ ] Count unique values
  - [ ] If < 50 unique colors → limited palette
  - [ ] Score: +0.25 if limited
- [ ] Check edge density (Canny edges)
  - [ ] Apply Canny edge detection
  - [ ] Calculate edge pixel ratio
  - [ ] If > 0.1 → crisp edges
  - [ ] Score: +0.15 if crisp
- [ ] Check aspect ratio
  - [ ] Calculate width/height
  - [ ] If 0.5 < ratio < 2.0 → squarish
  - [ ] Score: +0.1 if squarish
- [ ] Return result
  - [ ] `is_logo`: true if score > 0.5
  - [ ] `confidence`: min(score, 1.0)
  - [ ] `reasons`: list of contributing factors
- [ ] Write unit tests
  - [ ] Test with Nike logo (transparent PNG) → should detect
  - [ ] Test with product photo → should not detect
  - [ ] Test with simple icon → should detect

---

### Task 2.5: Integrate Analysis into Upload Flow

**File:** `backend/app/api/reference_assets.py`

- [ ] Update `POST /api/reference-assets/upload` endpoint
- [ ] After S3 upload, trigger async analysis
  - [ ] Option A: Call analysis synchronously (user waits ~3-5s)
  - [ ] Option B: Queue analysis as background task (Celery)
  - [ ] Decision: Use Option A for now (simpler, acceptable latency)
- [ ] Call `analyze_reference_asset()` with S3 URL
  - [ ] Pass user-provided name and description
  - [ ] Store full analysis JSON in `analysis` field
  - [ ] Extract and store individual fields: `primary_object`, `colors`, `style_tags`, etc.
- [ ] Call `extract_dominant_colors()` with S3 URL
  - [ ] Store result in `dominant_colors_rgb` field
- [ ] Call `generate_image_embedding()` with downloaded image
  - [ ] Store embedding in `embedding` field (pgvector)
- [ ] Call `detect_logo()` with downloaded image
  - [ ] Store `is_logo` field
  - [ ] If detected as logo, set default `logo_position_preference` = "bottom-right"
- [ ] Update database record with all analysis results
- [ ] Return enriched asset metadata to client
- [ ] Add error handling
  - [ ] If analysis fails, still save asset (with empty analysis)
  - [ ] Log error for debugging
  - [ ] Return warning to user
- [ ] Add loading indicator on frontend
  - [ ] Show "Analyzing..." message during upload
  - [ ] Display analysis results after completion

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

**File:** `backend/app/api/reference_assets.py`

- [ ] Implement `PATCH /api/reference-assets/{asset_id}` endpoint
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
- [ ] Verify embeddings are 768 dimensions
- [ ] Verify dominant colors are valid RGB values
- [ ] Test with various image formats (PNG, JPG, WEBP)

**Manual QA:**
- [ ] Upload 10 diverse images
- [ ] Review AI analysis results for accuracy
- [ ] Verify logo detection accuracy (test with 5 logos, 5 non-logos)
- [ ] Check that embeddings are stored correctly
- [ ] Verify frontend displays analysis results nicely

**Performance:**
- [ ] Measure upload + analysis latency (target: <5s)
- [ ] Test with large images (5MB+)
- [ ] Test concurrent uploads (10 simultaneous)

---

### Acceptance Criteria

- [ ] All uploaded images are automatically analyzed with GPT-4V
- [ ] Analysis includes: asset type, colors, style tags, shot types, usage contexts
- [ ] CLIP embeddings are generated and stored
- [ ] Logo detection works with >85% accuracy
- [ ] Dominant colors are extracted accurately
- [ ] Frontend displays analysis results in detail modal
- [ ] Users can edit asset metadata
- [ ] Upload latency is <5 seconds
- [ ] All tests pass