# TDD-reference-assets-tasks-5.md

## PR #5: ControlNet Image Generation

**Goal:** Enhance Phase 2 storyboard generation to use reference assets with ControlNet for product consistency using flux-dev-controlnet.

**Estimated Time:** 4-5 days  
**Dependencies:** PR #4 ✅

---

### Task 5.1: ControlNet Preprocessing Service

**File:** `backend/app/services/controlnet.py`

- [ ] Install dependencies: `pip install opencv-python`
- [ ] Create `ControlNetService` class
- [ ] Implement `preprocess_for_controlnet(image_path: str, method: str = "canny") -> str`
- [ ] Support Canny edge detection (default)
  - [ ] Load image with OpenCV
  - [ ] Convert to grayscale
  - [ ] Apply Canny edge detection (thresholds: 100, 200)
  - [ ] Convert edges to 3-channel image (ControlNet requirement)
  - [ ] Save preprocessed image
  - [ ] Return path to preprocessed image
- [ ] Add error handling
  - [ ] Handle corrupted images
  - [ ] Handle unexpected image formats
- [ ] Cache preprocessed images
  - [ ] Save to S3: `{asset_id}/preprocessed/edges.png`
  - [ ] Check cache before reprocessing
- [ ] Write unit tests
  - [ ] Test with product image → verify edges extracted
  - [ ] Test cache hit (second call should use cached)
  - [ ] Test error handling

---

### Task 5.2: ControlNet Generation Service

**File:** `backend/app/services/controlnet.py`

**Note:** Add cost constant to `backend/app/common/constants.py`:
```python
COST_FLUX_DEV_CONTROLNET_IMAGE = 0.058  # flux-dev with ControlNet support
```

- [ ] Implement `generate_with_controlnet(prompt: str, control_image_path: str, conditioning_scale: float, width: int, height: int) -> Image`
- [ ] Call Replicate flux-dev-controlnet model
  - [ ] Model: `black-forest-labs/flux-dev-controlnet` (or equivalent flux-dev with ControlNet support)
  - [ ] Parameters:
    - [ ] prompt (text prompt)
    - [ ] image (control image file)
    - [ ] conditioning_scale (0.5-1.0, default 0.75)
    - [ ] aspect_ratio ("16:9" for 1280x720)
    - [ ] output_format ("png")
    - [ ] output_quality (90)
    - [ ] num_inference_steps (30)
    - [ ] controlnet_type ("canny")
- [ ] Download result from Replicate URL
- [ ] Convert to PIL Image
- [ ] Return Image object
- [ ] Add retry logic (3 attempts)
- [ ] Add timeout (2 minutes)
- [ ] Track generation time and cost
- [ ] Write unit tests
  - [ ] Test with sample control image
  - [ ] Verify image dimensions
  - [ ] Test error handling

---

### Task 5.3: Update Phase 2 for ControlNet

**File:** `backend/app/phases/phase2_storyboard/task.py`

- [ ] Update `generate_storyboard()` task
- [ ] Accept new parameter: `reference_mapping` (from Phase 1)
- [ ] For each beat:
  - [ ] Check if references exist in mapping
  - [ ] If yes: use ControlNet generation
  - [ ] If no: fallback to regular flux-dev
- [ ] Implement ControlNet path:
  - [ ] Get product_ref from reference_mapping[beat_id]
  - [ ] Download product reference image from S3
  - [ ] Preprocess for ControlNet (extract edges)
  - [ ] Generate with flux-dev-controlnet
  - [ ] Apply logo overlay (if logo_ref exists)
  - [ ] Upload to S3
- [ ] Implement fallback path (no references):
  - [ ] Use existing flux-dev generation (current implementation)
  - [ ] No changes to current logic
- [ ] Track which path was used (for debugging)
- [ ] Update cost tracking
  - [ ] flux-dev: $0.025 (COST_FLUX_DEV_IMAGE - already exists)
  - [ ] flux-dev-controlnet: $0.058 (COST_FLUX_DEV_CONTROLNET_IMAGE - **NEW constant to add to constants.py**)
- [ ] Write integration test

---

### Task 5.4: Logo Overlay Service

**File:** `backend/app/services/logo_overlay.py`

- [ ] Create `LogoOverlayService` class
- [ ] Implement `apply_logo_overlay(image: Image, logo_asset: ReferenceAsset, beat_composition: str, opacity: float = 0.95) -> Image`
- [ ] Download logo from S3
- [ ] Ensure logo has alpha channel (RGBA)
- [ ] Determine optimal position
  - [ ] Call `find_optimal_logo_position()`
- [ ] Scale logo if needed
  - [ ] Max width: 15% of image width
  - [ ] Maintain aspect ratio
  - [ ] Use high-quality resize (LANCZOS)
- [ ] Apply opacity
  - [ ] Modify alpha channel
- [ ] Composite logo onto image
  - [ ] Use PIL Image.paste() with alpha mask
- [ ] Convert back to RGB (remove alpha)
- [ ] Return final image
- [ ] Write unit tests
  - [ ] Test with transparent PNG logo
  - [ ] Test with different image sizes
  - [ ] Verify logo not cropped
  - [ ] Verify opacity applied correctly

---

### Task 5.5: Smart Logo Positioning

**File:** `backend/app/services/logo_overlay.py`

- [ ] Implement `find_optimal_logo_position(base_image: Image, logo: Image, composition: str, user_preference: str = None) -> tuple[int, int]`
- [ ] If user preference exists, use it
  - [ ] Call `get_position_from_preference()`
  - [ ] Return coordinates
- [ ] Otherwise, find best position automatically
  - [ ] Define candidate positions (4 corners)
  - [ ] For each position:
    - [ ] Extract region where logo would be placed
    - [ ] Calculate simplicity score (lower variance = simpler = better)
    - [ ] Use variance of grayscale values as metric
  - [ ] Select position with highest score
- [ ] Return (x, y) coordinates
- [ ] Implement `get_position_from_preference(image_size, logo_size, preference) -> tuple[int, int]`
  - [ ] Support preferences: bottom-right, bottom-left, top-right, top-left, center
  - [ ] Calculate coordinates with padding (30px)
  - [ ] Return (x, y)
- [ ] Write unit tests
  - [ ] Test with simple background → logo should be placed there
  - [ ] Test with busy background → logo should avoid it
  - [ ] Test user preference → should use exact position

---

### Task 5.6: Quality Tier Configuration

**File:** `backend/app/common/quality_tiers.py`

- [ ] Define IMAGE_QUALITY_TIERS dict
  ```python
  IMAGE_QUALITY_TIERS = {
      "draft": {
          "model": "flux-dev",
          "use_references": False,
          "cost_per_image": 0.025
      },
      "standard": {
          "model": "flux-dev-controlnet",
          "use_references": True,
          "cost_per_image": 0.058
      },
      "final": {
          "model": "flux-pro",
          "use_references": True,
          "cost_per_image": 0.040
      }
  }
  ```
- [ ] Update Phase 2 to accept quality_tier parameter
- [ ] Select model based on tier
- [ ] Track tier in video generation record
- [ ] Write unit tests

---

### Task 5.7: Update Video Generation API

**File:** `backend/app/api/videos.py`

- [ ] Update `POST /api/videos/generate` endpoint
- [ ] Add new parameters:
  - [ ] `reference_asset_ids` (list of asset IDs, optional)
  - [ ] `quality_tier` (draft/standard/final, default: standard)
- [ ] Validate reference_asset_ids
  - [ ] Verify assets belong to user
  - [ ] Verify assets exist
- [ ] Pass reference_asset_ids to orchestrator
- [ ] Pass quality_tier to orchestrator
- [ ] Estimate cost based on quality tier
- [ ] Update response to include:
  - [ ] Estimated cost
  - [ ] Quality tier
  - [ ] Reference assets used
- [ ] Write integration test

---

### Task 5.8: Frontend Quality Selector

**File:** `frontend/src/components/VideoGenerator.tsx`

- [ ] Add quality tier selector
  - [ ] Radio buttons: Draft / Standard / Final
  - [ ] Show cost estimate for each tier
  - [ ] Default: Standard
- [ ] Display quality tier descriptions
  - [ ] Draft: "Fast, no references"
  - [ ] Standard: "Good quality, references supported"
  - [ ] Final: "Best quality, premium cost"
- [ ] Update cost estimate when tier changes
- [ ] Show selected tier in video generation summary
- [ ] Style with Tailwind CSS

---

### Task 5.9: Testing & Validation

**Unit Tests:**
- [ ] Test ControlNet preprocessing
- [ ] Test ControlNet generation
- [ ] Test logo overlay with various positions
- [ ] Test quality tier selection

**Integration Tests:**
- [ ] Generate storyboard with references (standard tier)
  - [ ] Verify flux-dev-controlnet used
  - [ ] Verify product consistency across beats
  - [ ] Verify logo overlaid
- [ ] Generate storyboard without references (draft tier)
  - [ ] Verify regular flux-dev used
  - [ ] Verify no ControlNet processing
- [ ] Generate storyboard with references (final tier)
  - [ ] Verify Flux Pro used (if implemented)

**Manual QA:**
- [ ] Generate 5 videos with same product reference
- [ ] Visual inspection: Is product consistent across storyboards?
- [ ] Expected: 85% consistency (product recognizable)
- [ ] Compare to baseline (without flux-dev-controlnet)
- [ ] Verify logo placement looks good
- [ ] Test with different logo sizes
- [ ] Test with different image compositions

**Performance:**
- [ ] Measure storyboard generation time with ControlNet
  - [ ] Target: <10s per image
  - [ ] Compare to baseline (regular flux-dev ~8s)
- [ ] Test with large reference images (10MB)
- [ ] Test concurrent storyboard generation

---

### Acceptance Criteria

- [ ] Phase 2 supports reference assets via flux-dev-controlnet
- [ ] Product consistency in storyboards: >85% (visual QA)
- [ ] Logo overlay works with 100% accuracy
- [ ] Logo positioning avoids busy areas
- [ ] Quality tiers work (draft/standard/final)
- [ ] Cost tracking accurate for different tiers
- [ ] Frontend shows quality selector
- [ ] Reference assets visibly used in storyboards
- [ ] Fallback to regular flux-dev works when no references
- [ ] All tests pass
- [ ] Performance acceptable (<10s per storyboard image)

---

This completes all 5 task files! Each PR is scoped to 3-5 days of work and builds progressively on the previous one. Total estimated timeline: **15-20 days** for complete implementation of the reference asset library with AI analysis and ControlNet integration.