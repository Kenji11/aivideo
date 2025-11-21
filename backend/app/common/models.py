from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum, Integer, Boolean, ARRAY, Text
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
    """Asset type (legacy - for backward compatibility)"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"

class ReferenceAssetType(str, enum.Enum):
    """Reference asset content type"""
    PRODUCT = "product"
    LOGO = "logo"
    PERSON = "person"
    ENVIRONMENT = "environment"
    TEXTURE = "texture"
    PROP = "prop"

class AssetSource(str, enum.Enum):
    """
    Asset source enum.
    
    NOTE: There's a mismatch between Python enum values (lowercase) and PostgreSQL enum labels (uppercase).
    - Python: USER_UPLOAD = "user_upload"
    - PostgreSQL: 'USER_UPLOAD' (enum label)
    
    For raw SQL queries, use .name (e.g., AssetSource.USER_UPLOAD.name) to get "USER_UPLOAD".
    For SQLAlchemy ORM, use the enum directly (e.g., AssetSource.USER_UPLOAD) - it handles conversion.
    
    TODO: Migrate to align values or change to VARCHAR for consistency.
    """
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
    asset_type = Column(SQLEnum(AssetType), nullable=False)  # Legacy: IMAGE/VIDEO/AUDIO
    source = Column(String(20), nullable=False)  # user_upload/system_generated - stored as string to avoid enum name issues
    
    # Metadata
    file_name = Column(String, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    asset_metadata = Column(JSON, default=dict)  # Additional metadata (dimensions, duration, etc.)
    
    # Reference Asset Fields (new)
    # User-defined metadata
    name = Column(String, nullable=True)  # User-defined name (editable, defaults to filename)
    description = Column(Text, nullable=True)  # Optional user description
    reference_asset_type = Column(String(20), nullable=True)  # product/logo/person/etc - stored as string to avoid enum name issues
    
    # Storage
    thumbnail_url = Column(String, nullable=True)  # Optimized thumbnail S3 URL
    
    # Image properties
    width = Column(Integer, nullable=True)  # Image width in pixels
    height = Column(Integer, nullable=True)  # Image height in pixels
    has_transparency = Column(Boolean, default=False)  # Whether image has alpha channel
    
    # AI Analysis (from GPT-4V)
    analysis = Column(JSON, nullable=True)  # Full GPT-4V analysis response
    primary_object = Column(String, nullable=True)  # "Nike Air Max sneaker"
    colors = Column(ARRAY(String), nullable=True)  # ["white", "red", "black"]
    dominant_colors_rgb = Column(JSON, nullable=True)  # [[255,255,255], [220,20,60]]
    style_tags = Column(ARRAY(String), nullable=True)  # ["athletic", "modern", "clean"]
    recommended_shot_types = Column(ARRAY(String), nullable=True)  # ["close_up", "hero_shot"]
    usage_contexts = Column(ARRAY(String), nullable=True)  # ["product shots", "action scenes"]
    
    # Logo-specific
    is_logo = Column(Boolean, default=False)  # Logo detection flag
    logo_position_preference = Column(String, nullable=True)  # "bottom-right", "top-left", etc.
    
    # Semantic Search (pgvector)
    # Note: embedding column will be added via migration (requires pgvector extension)
    # embedding = Column(Vector(512), nullable=True)  # CLIP embedding for semantic search (ViT-B/32 produces 512-dim vectors)
    
    # Metadata
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    usage_count = Column(Integer, default=0)  # Track how often used in videos
    
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
