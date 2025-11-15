from pydantic import BaseModel
from typing import List, Dict


class AnimaticFrameSpec(BaseModel):
    """Specification for a single animatic frame"""
    frame_num: int
    beat_name: str
    shot_type: str
    action: str
    prompt: str


class AnimaticGenerationRequest(BaseModel):
    """Request to generate animatic frames"""
    video_id: str
    beats: List[Dict]
    style: Dict


class AnimaticGenerationResult(BaseModel):
    """Result from animatic generation"""
    video_id: str
    frame_urls: List[str]
    total_frames: int
    cost_usd: float
