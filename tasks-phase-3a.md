# Phase 3 Tasks - Part A: Reference Asset System

**Owner:** Person handling Phase 3  
**Goal:** Create reference asset generation system and schemas

---

## PR #10: Phase 3 Schemas

### Task 10.1: Create Phase 3 Schemas

**File:** `backend/app/phases/phase3_references/schemas.py`

```python
from pydantic import BaseModel
from typing import Dict, List, Optional

class StyleGuideSpec(BaseModel):
    """Style guide image specification"""
    prompt: str
    aesthetic: str
    color_palette: List[str]
    mood: str
    lighting: str

class ProductReferenceSpec(BaseModel):
    """Product reference image specification"""
    product_name: str
    product_category: str
    prompt: str

class ReferenceAssetsOutput(BaseModel):
    """Output from Phase 3"""
    style_guide_url: str
    product_reference_url: Optional[str] = None
    uploaded_assets: List[Dict] = []
    total_cost: float
```

- [ ] Import BaseModel from pydantic
- [ ] Create StyleGuideSpec model (prompt, aesthetic, color_palette, mood, lighting)
- [ ] Create ProductReferenceSpec model (product_name, product_category, prompt)
- [ ] Create ReferenceAssetsOutput model with all URLs and cost

---

## PR #11: Asset Handler

### Task 11.1: Create Asset Handler Utility

**File:** `backend/app/phases/phase3_references/asset_handler.py`

```python
from typing import List, Dict
from app.services.s3 import s3_client

class AssetHandler:
    """Handle uploaded assets and reference images"""
    
    def __init__(self):
        self.s3 = s3_client
    
    def process_uploaded_assets(self, assets: List[Dict], video_id: str) -> List[Dict]:
        """Process and validate uploaded assets"""
        # Download, validate, resize if needed
        # Return processed asset metadata
    
    def download_asset(self, asset_url: str) -> str:
        """Download asset to temp file for processing"""
    
    def validate_image(self, image_path: str) -> bool:
        """Validate image format and dimensions"""
```

- [ ] Import s3_client
- [ ] Create AssetHandler class
- [ ] Implement `process_uploaded_assets()` method
- [ ] Add validation for image formats (JPEG, PNG)
- [ ] Add validation for image dimensions (max 2048x2048)
- [ ] Implement `download_asset()` method
- [ ] Implement `validate_image()` method
- [ ] Add error handling for invalid assets

---

## PR #12: Reference Generation Service

### Task 12.1: Create ReferenceAssetService Class

**File:** `backend/app/phases/phase3_references/service.py`

- [ ] Import necessary dependencies (replicate_client, s3_client, schemas, asset_handler)
- [ ] Create ReferenceAssetService class
- [ ] Add `__init__` method to initialize services
- [ ] Add `total_cost` attribute for cost tracking

### Task 12.2: Implement generate_all_references Method

- [ ] Create `generate_all_references(video_id, spec)` method signature
- [ ] Add docstring explaining method purpose
- [ ] Extract style information from spec
- [ ] Call `_generate_style_guide(video_id, spec)`
- [ ] Call `_generate_product_reference(video_id, spec)` if product exists
- [ ] Process uploaded assets using AssetHandler
- [ ] Upload all references to S3
- [ ] Calculate total cost
- [ ] Return reference URLs dictionary

### Task 12.3: Implement _generate_style_guide Method

- [ ] Create `_generate_style_guide(video_id, spec)` private method
- [ ] Build prompt from spec style information
- [ ] Format prompt: "{aesthetic} style, {color_palette} colors, {mood} mood, {lighting} lighting"
- [ ] Call Replicate SDXL model
- [ ] Use model: "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
- [ ] Set width=1024, height=1024
- [ ] Set num_outputs=1
- [ ] Download generated image
- [ ] Upload to S3 at `references/{video_id}/style_guide.png`
- [ ] Track cost (COST_SDXL_IMAGE)
- [ ] Return S3 URL

### Task 12.4: Implement _generate_product_reference Method

- [ ] Create `_generate_product_reference(video_id, spec)` private method
- [ ] Extract product information from spec
- [ ] Build prompt: "Professional product photography of {product_name}, {category}, studio lighting, high quality"
- [ ] Call Replicate SDXL model
- [ ] Set width=1024, height=1024
- [ ] Download generated image
- [ ] Upload to S3 at `references/{video_id}/product_reference.png`
- [ ] Track cost (COST_SDXL_IMAGE)
- [ ] Return S3 URL (or None if no product)

### Task 12.5: Implement Uploaded Asset Processing

- [ ] Check if spec has uploaded_assets
- [ ] Use AssetHandler to process each asset
- [ ] Validate image format and dimensions
- [ ] Resize if needed (max 2048x2048)
- [ ] Upload processed assets to S3
- [ ] Store asset metadata (type, dimensions, S3 URL)
- [ ] Return list of processed asset URLs

---

## ✅ PR #10, #11, #12 Checklist

Before merging:
- [ ] All Phase 3 schemas defined
- [ ] AssetHandler implemented and tested
- [ ] ReferenceAssetService generates style guide
- [ ] ReferenceAssetService generates product reference (if applicable)
- [ ] Uploaded assets processed correctly
- [ ] All images uploaded to S3
- [ ] Cost tracking works

**Test Commands:**
```python
# In Python shell
from app.phases.phase3_references.service import ReferenceAssetService
from app.phases.phase3_references.asset_handler import AssetHandler

service = ReferenceAssetService()
handler = AssetHandler()

# Test asset validation
handler.validate_image("test_image.jpg")
```

**Next:** Move to `tasks-phase-3b.md`

