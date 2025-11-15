from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from datetime import datetime

# ============ Phase Contracts ============

class PhaseInput(BaseModel):
    """Standard input for every phase task"""
    video_id: str
    spec: Dict

class PhaseOutput(BaseModel):
    """Standard output from every phase task"""
    video_id: str
    phase: str
    status: str  # "success" or "failed"
    output_data: Dict
    cost_usd: float
    duration_seconds: float
    error_message: Optional[str] = None

# ============ API Schemas ============

class GenerateRequest(BaseModel):
    """Request to generate video"""
    title: Optional[str] = Field(None, max_length=200)  # Optional, will default to "Untitled Video"
    description: Optional[str] = Field(None, max_length=2000)
    prompt: str = Field(..., min_length=10, max_length=1000)
    reference_assets: List[str] = Field(default_factory=list, description="List of asset IDs to use as references")

class GenerateResponse(BaseModel):
    """Response from generate endpoint"""
    video_id: str
    status: str
    message: str

class StatusResponse(BaseModel):
    """Response from status endpoint"""
    video_id: str
    status: str
    progress: float
    current_phase: Optional[str]
    estimated_time_remaining: Optional[int]
    error: Optional[str]
    animatic_urls: Optional[List[str]] = None  # Phase 2 animatic frames
    reference_assets: Optional[Dict] = None  # Phase 3 reference assets
    stitched_video_url: Optional[str] = None  # Phase 4 stitched video

class VideoResponse(BaseModel):
    """Response from video endpoint"""
    video_id: str
    status: str
    final_video_url: Optional[str]
    cost_usd: float
    generation_time_seconds: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    spec: Optional[Dict]

class VideoListItem(BaseModel):
    """Video item in list response"""
    video_id: str
    title: str
    status: str
    progress: float
    current_phase: Optional[str] = None
    final_video_url: Optional[str]
    cost_usd: float
    created_at: datetime
    completed_at: Optional[datetime]

class VideoListResponse(BaseModel):
    """Response from videos list endpoint"""
    videos: List[VideoListItem]
    total: int

class UploadedAsset(BaseModel):
    """Single uploaded asset response"""
    asset_id: str
    filename: str
    asset_type: str
    file_size_bytes: int
    s3_url: str

class UploadResponse(BaseModel):
    """Response from upload endpoint"""
    assets: List[UploadedAsset]
    total: int
    errors: Optional[List[str]] = None
    partial_success: Optional[bool] = False

class AssetListItem(BaseModel):
    """Asset item in list response"""
    asset_id: str
    filename: str
    asset_type: str
    file_size_bytes: int
    s3_url: str
    created_at: Optional[str] = None

class AssetListResponse(BaseModel):
    """Response from assets list endpoint"""
    assets: List[AssetListItem]
    total: int
    user_id: str
