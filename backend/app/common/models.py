from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum, Integer
from sqlalchemy.sql import func
from app.database import Base
import enum

class VideoStatus(str, enum.Enum):
    """Video generation status"""
    QUEUED = "queued"
    VALIDATING = "validating"
    GENERATING_ANIMATIC = "generating_animatic"
    GENERATING_REFERENCES = "generating_references"
    GENERATING_CHUNKS = "generating_chunks"
    REFINING = "refining"
    EXPORTING = "exporting"
    COMPLETE = "complete"
    FAILED = "failed"

class AssetType(str, enum.Enum):
    """Asset type"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

class AssetSource(str, enum.Enum):
    """Asset source"""
    USER_UPLOAD = "user_upload"
    SYSTEM_GENERATED = "system_generated"

class Asset(Base):
    """Asset record for uploaded and generated assets"""
    __tablename__ = "assets"
    
    # Primary
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)  # Null if system-generated
    
    # Asset details
    s3_key = Column(String, nullable=False)  # S3 key/path
    s3_url = Column(String, nullable=True)  # Full S3 URL or presigned URL
    asset_type = Column(SQLEnum(AssetType), nullable=False)
    source = Column(SQLEnum(AssetSource), nullable=False)
    
    # Metadata
    file_name = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    asset_metadata = Column(JSON, default=dict)  # Additional metadata (dimensions, duration, etc.)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VideoGeneration(Base):
    """Video generation record"""
    __tablename__ = "video_generations"
    
    # Primary
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    
    # Video details
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    # Input
    prompt = Column(String, nullable=False)
    prompt_validated = Column(String, nullable=True)  # Validated/cleaned prompt after Phase 1
    reference_assets = Column(JSON, default=list)  # List of asset IDs
    
    # Spec (from Phase 1)
    spec = Column(JSON, nullable=True)
    template = Column(String, nullable=True)
    
    # Status
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.QUEUED)
    progress = Column(Float, default=0.0)
    current_phase = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Phase Outputs
    animatic_urls = Column(JSON, default=list)
    # storyboard_images removed - storyboard images are stored in phase_outputs['phase2_storyboard'] and spec['beats'][]['image_url']
    chunk_urls = Column(JSON, default=list)
    stitched_url = Column(String, nullable=True)
    refined_url = Column(String, nullable=True)
    final_video_url = Column(String, nullable=True)
    final_music_url = Column(String, nullable=True)  # Music URL from Phase 5 (saved even if combining fails)
    phase_outputs = Column(JSON, default=dict)  # Store outputs from each phase
    
    # Note: creativity_level, selected_archetype, num_beats, num_chunks stored in spec JSON
    
    # Metadata
    cost_usd = Column(Float, default=0.0)
    cost_breakdown = Column(JSON, default=dict)
    generation_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
