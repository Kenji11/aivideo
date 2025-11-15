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
