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
    prompt: str = Field(..., min_length=10, max_length=1000)
    assets: List[Dict[str, str]] = Field(default_factory=list)

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
