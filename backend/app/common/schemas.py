from __future__ import annotations

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
    checkpoint_id: Optional[str] = None  # ID of checkpoint created by this phase

# ============ Checkpoint Schemas (Status-related) ============
# These need to be defined before StatusResponse

class ArtifactResponse(BaseModel):
    """Artifact response schema"""
    id: str
    artifact_type: str
    artifact_key: str
    s3_url: str
    version: int
    metadata: Optional[Dict] = None
    created_at: datetime

class CheckpointResponse(BaseModel):
    """Checkpoint response schema"""
    id: str
    video_id: str
    branch_name: str
    phase_number: int
    version: int
    status: str
    approved_at: Optional[datetime] = None
    created_at: datetime
    cost_usd: float
    parent_checkpoint_id: Optional[str] = None
    artifacts: List[ArtifactResponse] = Field(default_factory=list)
    user_id: str
    edit_description: Optional[str] = None

class CheckpointTreeNode(BaseModel):
    """Checkpoint tree node for hierarchical display"""
    checkpoint: CheckpointResponse
    children: List[CheckpointTreeNode] = Field(default_factory=list)

class BranchInfo(BaseModel):
    """Active branch information"""
    branch_name: str
    latest_checkpoint_id: str
    phase_number: int
    status: str
    can_continue: bool

class CheckpointInfo(BaseModel):
    """Current checkpoint information for status endpoint"""
    checkpoint_id: str
    branch_name: str
    phase_number: int
    version: int
    status: str
    created_at: datetime
    artifacts: Dict[str, ArtifactResponse] = Field(default_factory=dict)  # Keyed by artifact_key

# ============ API Schemas ============

class GenerateRequest(BaseModel):
    """Request to generate video"""
    title: Optional[str] = Field(None, max_length=200)  # Optional, will default to "Untitled Video"
    description: Optional[str] = Field(None, max_length=2000)
    prompt: str = Field(..., min_length=10, max_length=1000)
    reference_assets: List[str] = Field(default_factory=list, description="List of asset IDs to use as references")
    model: Optional[str] = Field(None, description="Video generation model to use (e.g., 'hailuo', 'kling', 'sora'). Defaults to 'hailuo'")
    auto_continue: bool = Field(False, description="YOLO mode: auto-approve checkpoints and run pipeline to completion without pausing")

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
    storyboard_urls: Optional[List[str]] = None  # Phase 2 storyboard images
    reference_assets: Optional[Dict] = None  # Phase 3 reference assets
    chunk_urls: Optional[List[str]] = None  # Phase 3 individual chunk videos
    stitched_video_url: Optional[str] = None  # Phase 4 stitched video
    final_video_url: Optional[str] = None  # Phase 5 final video (with audio)
    current_chunk_index: Optional[int] = None  # Current chunk being processed in Phase 4
    total_chunks: Optional[int] = None  # Total number of chunks in Phase 4

    # Checkpoint fields
    current_checkpoint: Optional[CheckpointInfo] = None
    checkpoint_tree: Optional[List[CheckpointTreeNode]] = None
    active_branches: Optional[List[BranchInfo]] = None

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

# ============ Additional Checkpoint Schemas ============

class ContinueRequest(BaseModel):
    """Request to continue pipeline from checkpoint"""
    checkpoint_id: str

class ContinueResponse(BaseModel):
    """Response from continue endpoint"""
    message: str
    next_phase: int
    branch_name: str
    created_new_branch: bool

class SpecEditRequest(BaseModel):
    """Request to edit Phase 1 spec"""
    beats: Optional[List[Dict]] = None
    style: Optional[Dict] = None
    product: Optional[Dict] = None
    audio: Optional[Dict] = None

class RegenerateBeatRequest(BaseModel):
    """Request to regenerate a beat image at Phase 2"""
    beat_index: int
    prompt_override: Optional[str] = None

class RegenerateChunkRequest(BaseModel):
    """Request to regenerate a video chunk at Phase 3"""
    model_config = {"protected_namespaces": ()}

    chunk_index: int
    model_override: Optional[str] = None

class ArtifactEditResponse(BaseModel):
    """Response from artifact editing endpoints"""
    artifact_id: str
    version: int
    s3_url: Optional[str] = None
    message: str
