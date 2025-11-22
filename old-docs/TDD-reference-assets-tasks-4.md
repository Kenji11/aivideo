# TDD-reference-assets-tasks-5.md

## PR #5: ControlNet Image Generation

**Goal:** Enhance Phase 2 storyboard generation to use reference assets with ControlNet for product consistency using flux-dev-controlnet.

**Estimated Time:** 4-5 days  
**Dependencies:** PR #4 ✅

---

### Task 5.1: ControlNet Preprocessing Service ✅

**File:** `backend/app/services/controlnet.py`

- [x] Install dependencies: `pip install opencv-python` (already in requirements.txt)
- [x] Create `ControlNetService` class
- [x] Implement `preprocess_for_controlnet(image_path: str, method: str = "canny") -> str`
- [x] Support Canny edge detection (default)
  - [x] Load image with OpenCV
  - [x] Convert to grayscale
  - [x] Apply Canny edge detection (thresholds: 100, 200)
  - [x] Convert edges to 3-channel image (ControlNet requirement)
  - [x] Save preprocessed image
  - [x] Return path to preprocessed image
- [x] Add error handling
  - [x] Handle corrupted images
  - [x] Handle unexpected image formats
- [ ] Cache preprocessed images (deferred - not critical for MVP)
  - [ ] Save to S3: `{asset_id}/preprocessed/edges.png`
  - [ ] Check cache before reprocessing
- [ ] Write unit tests (deferred)
  - [ ] Test with product image → verify edges extracted
  - [ ] Test cache hit (second call should use cached)
  - [ ] Test error handling

---

### Task 5.2: ControlNet Generation Service ✅

**File:** `backend/app/services/controlnet.py`

**Note:** Added cost constant to `backend/app/common/constants.py`:
```python
COST_FLUX_DEV_CONTROLNET_IMAGE = 0.058  # flux-dev with ControlNet support
```

- [x] Implement `generate_with_controlnet(prompt: str, control_image_path: str, conditioning_scale: float, aspect_ratio: str) -> str`
- [x] Call Replicate flux-dev-controlnet model
  - [x] Model: `xlabs-ai/flux-dev-controlnet`
  - [x] Parameters:
    - [x] prompt (text prompt)
    - [x] image (control image file)
    - [x] conditioning_scale (0.5-1.0, default 0.75)
    - [x] aspect_ratio ("16:9" for 1280x720)
    - [x] output_format ("png")
    - [x] output_quality (90)
    - [x] num_inference_steps (30)
    - [x] controlnet_type ("canny")
- [x] Download result from Replicate URL
- [x] Return image URL
- [x] Add timeout (2 minutes)
- [x] Track generation time and cost
- [ ] Write unit tests (deferred)
  - [ ] Test with sample control image
  - [ ] Verify image dimensions
  - [ ] Test error handling

---

### Task 5.3: Update Phase 2 for ControlNet ✅

**File:** `backend/app/phases/phase2_storyboard/task.py` and `image_generation.py`

- [x] Update `generate_storyboard()` task
- [x] Accept new parameter: `reference_mapping` (from Phase 1)
- [x] For each beat:
  - [x] Check if references exist in mapping
  - [x] If yes: use ControlNet generation
  - [x] If no: fallback to regular flux-dev
- [x] Implement ControlNet path:
  - [x] Get product_ref from reference_mapping[beat_id]
  - [x] Download product reference image from S3
  - [x] Preprocess for ControlNet (extract edges)
  - [x] Generate with flux-dev-controlnet
  - [x] Upload to S3
- [x] Implement fallback path (no references):
  - [x] Use existing flux-dev generation (current implementation)
  - [x] Graceful fallback if download/preprocessing fails
- [x] Track which path was used (for debugging) - `used_controlnet` flag
- [x] Update cost tracking
  - [x] flux-dev: $0.025 (COST_FLUX_DEV_IMAGE - already exists)
  - [x] flux-dev-controlnet: $0.058 (COST_FLUX_DEV_CONTROLNET_IMAGE - added to constants.py)
- [x] Fixed Phase 1 prompt to ensure reference_mapping uses beat_ids as keys (not asset IDs)
- [ ] Write integration test (deferred)

---

### Acceptance Criteria (Completed)

- [x] Phase 2 supports reference assets via flux-dev-controlnet
- [x] ControlNet preprocessing service implemented (Canny edge detection)
- [x] ControlNet generation service implemented (flux-dev-controlnet model)
- [x] Phase 2 integration complete with reference mapping support
- [x] Fallback to regular flux-dev works when no references
- [x] Cost tracking accurate for both paths ($0.058 ControlNet, $0.025 regular)
- [x] Reference mapping structure fixed (beat_ids as keys)

---

**Note:** Remaining features (logo overlay, quality tiers, API updates, frontend) will be handled in future iterations.