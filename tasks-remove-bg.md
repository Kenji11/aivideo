# Background Removal for Product Images

**Goal**: Automatically remove backgrounds from product images during asset upload using Replicate's recraft-remove-background model.

**Scope**: Single PR implementing background removal in the asset upload pipeline.

---

## Tasks

### 1. Configuration & Constants
- [ ] 1.1. Add `RECRAFT_REMOVE_BG` model configuration to `backend/app/common/constants.py`
  - Model identifier: `ai/recraft-remove-background`
  - Add to REPLICATE_MODELS dict with appropriate version
- [ ] 1.2. Add any necessary environment variables or configuration settings

### 2. Background Removal Service
- [ ] 2.1. Create background removal function in `backend/app/services/` (or extend existing service)
  - Function to call recraft-remove-background model via Replicate API
  - Handle input/output image formats
  - Include error handling and retry logic
- [ ] 2.2. Add logging for background removal operations
  - Log when background removal starts
  - Log success/failure with asset details

### 3. Asset Upload Integration
- [ ] 3.1. Identify where asset type determination happens in upload flow
  - Review `backend/app/api/upload.py` or relevant upload handler
- [ ] 3.2. Add background removal step after "product image" type is identified
  - Check if asset_type == "product_image"
  - Call background removal service
  - Handle the returned image
- [ ] 3.3. Overwrite original image with background-removed version
  - Update S3/storage with new image
  - Maintain same filename/path for seamless replacement
  - Update any database records if necessary

### 4. Error Handling & Fallback
- [ ] 4.1. Implement graceful degradation if background removal fails
  - Keep original image if API call fails
  - Log error but don't block upload process
- [ ] 4.2. Add timeout handling for Replicate API calls
- [ ] 4.3. Handle edge cases (unsupported formats, corrupted images, etc.)

### 5. Testing
- [ ] 5.1. Test with sample product images
  - Upload various product images and verify background removal
  - Confirm original image is overwritten correctly
- [ ] 5.2. Test error scenarios
  - API failures
  - Invalid image formats
  - Network timeouts
- [ ] 5.3. Verify non-product images are unaffected
  - Upload other asset types (background, overlay, etc.)
  - Confirm background removal is NOT applied

### 6. Documentation
- [ ] 6.1. Update relevant documentation with background removal feature
- [ ] 6.2. Add comments in code explaining the background removal logic
- [ ] 6.3. Document the model choice and any limitations

---

## Technical Notes

**Model**: `ai/recraft-remove-background` (Replicate)
- High-quality background removal
- Optimized for product images
- Returns PNG with transparency

**Integration Point**: Asset upload pipeline after type classification
- Only applies to `asset_type == "product_image"`
- Overwrites original image storage location
- Maintains same asset URL/reference

**Storage Strategy**: In-place replacement
- Download original from S3
- Process through background removal
- Upload result to same S3 path (overwrite)
- Ensures all references remain valid

---

## Success Criteria
- ✅ Product images uploaded have backgrounds automatically removed
- ✅ Background-removed image replaces original at same location
- ✅ Other asset types are not affected
- ✅ Graceful error handling if background removal fails
- ✅ All operations logged appropriately

