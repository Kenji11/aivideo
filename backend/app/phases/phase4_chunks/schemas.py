# Phase 4 Schemas
from pydantic import BaseModel
from typing import Dict, List, Optional


class ChunkSpec(BaseModel):
    """Specification for a single video chunk"""
    video_id: str
    chunk_num: int
    start_time: float
    duration: float
    beat: Dict
    animatic_frame_url: Optional[str] = None  # Optional: if None, use text-to-video mode
    style_guide_url: Optional[str] = None
    product_reference_url: Optional[str] = None
    previous_chunk_last_frame: Optional[str] = None
    uploaded_asset_url: Optional[str] = None  # Specific uploaded image for this chunk (if multiple images provided)
    prompt: str
    fps: int = 24  # FPS for frame calculation
    use_text_to_video: bool = False  # Flag to use text-to-video instead of image-to-video


class ChunkGenerationOutput(BaseModel):
    """Output from Phase 4"""
    stitched_video_url: str
    chunk_urls: List[str]
    total_cost: float
