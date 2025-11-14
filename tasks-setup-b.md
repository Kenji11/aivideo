# Setup Tasks - Part B: Shared Code & Database

**Owner:** Either person (coordinate who does what)  
**Goal:** Implement shared code that both phases will use

---

## PR #3: Configuration & Database Setup

### Task 3.1: Implement app/config.py

**File:** `backend/app/config.py`
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    database_url: str
    
    # Redis
    redis_url: str
    
    # External APIs
    replicate_api_token: str
    openai_api_key: str
    
    # AWS
    aws_access_key_id: str
    aws_secret_access_key: str
    s3_bucket: str
    aws_region: str = "us-east-2"
    
    # Application
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance"""
    return Settings()
```

- [x] Create Settings class with all configuration fields
- [x] Add database configuration
- [x] Add Redis configuration
- [x] Add external API configuration (Replicate, OpenAI)
- [x] Add AWS configuration
- [x] Add application environment settings
- [x] Implement cached `get_settings()` function

### Task 3.2: Implement app/database.py

**File:** `backend/app/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database (create tables)"""
    from app.common.models import VideoGeneration
    Base.metadata.create_all(bind=engine)
```

- [x] Import settings and create SQLAlchemy engine
- [x] Configure connection pool settings
- [x] Create SessionLocal factory
- [x] Create Base class for models
- [x] Implement `get_db()` dependency function
- [x] Implement `init_db()` function to create tables

### Task 3.3: Implement app/common/models.py

**File:** `backend/app/common/models.py`
```python
from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum
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

class VideoGeneration(Base):
    """Video generation record"""
    __tablename__ = "video_generations"
    
    # Primary
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    
    # Input
    prompt = Column(String, nullable=False)
    uploaded_assets = Column(JSON, default=list)
    
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
    reference_urls = Column(JSON, default=dict)
    chunk_urls = Column(JSON, default=list)
    stitched_url = Column(String, nullable=True)
    refined_url = Column(String, nullable=True)
    final_video_url = Column(String, nullable=True)
    
    # Metadata
    cost_usd = Column(Float, default=0.0)
    cost_breakdown = Column(JSON, default=dict)
    generation_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
```

- [x] Create VideoStatus enum with all status values
- [x] Create VideoGeneration model class
- [x] Add primary fields (id, user_id)
- [x] Add input fields (prompt, uploaded_assets)
- [x] Add spec fields from Phase 1
- [x] Add status tracking fields
- [x] Add phase output URL fields
- [x] Add metadata fields (cost, timing, timestamps)

### Task 3.4: Implement app/common/schemas.py

**File:** `backend/app/common/schemas.py`
```python
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
```

- [x] Create PhaseInput schema for phase task inputs
- [x] Create PhaseOutput schema for phase task outputs
- [x] Create GenerateRequest schema for API
- [x] Create GenerateResponse schema for API
- [x] Create StatusResponse schema for status endpoint
- [x] Create VideoResponse schema for video endpoint

### Task 3.5: Implement app/common/exceptions.py

**File:** `backend/app/common/exceptions.py`
```python
class VideoGenException(Exception):
    """Base exception for video generation"""
    pass

class PhaseException(VideoGenException):
    """Exception during phase execution"""
    pass

class ExternalAPIException(VideoGenException):
    """Exception from external API"""
    pass

class ValidationException(VideoGenException):
    """Validation error"""
    pass
```

- [x] Create VideoGenException base class
- [x] Create PhaseException for phase errors
- [x] Create ExternalAPIException for API errors
- [x] Create ValidationException for validation errors

### Task 3.6: Implement app/common/constants.py

**File:** `backend/app/common/constants.py`
```python
# Video specifications
DEFAULT_DURATION = 30  # seconds
DEFAULT_FPS = 30
DEFAULT_RESOLUTION = "1080p"

# Cost per API call (USD)
COST_GPT4_TURBO = 0.01
COST_SDXL_IMAGE = 0.0055
COST_ZEROSCOPE_VIDEO = 0.10
COST_ANIMATEDIFF_VIDEO = 0.20
COST_MUSICGEN = 0.15

# S3 paths
S3_ANIMATIC_PREFIX = "animatic"
S3_REFERENCES_PREFIX = "references"
S3_CHUNKS_PREFIX = "chunks"
S3_FINAL_PREFIX = "final"

# Timeouts (seconds)
PHASE1_TIMEOUT = 60
PHASE2_TIMEOUT = 300
PHASE3_TIMEOUT = 300
PHASE4_TIMEOUT = 600
PHASE5_TIMEOUT = 300
PHASE6_TIMEOUT = 180
```

- [x] Add video specification constants
- [x] Add API cost constants
- [x] Add S3 path prefix constants
- [x] Add phase timeout constants

---

## PR #4: FastAPI Application & Service Clients

### Task 4.1: Implement app/main.py

**File:** `backend/app/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import generate, status, video, health
from app.database import init_db

# Create FastAPI app
app = FastAPI(
    title="Video Generation API",
    description="AI-powered video generation pipeline",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(generate.router, tags=["generation"])
app.include_router(status.router, tags=["status"])
app.include_router(video.router, tags=["video"])

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Video Generation API",
        "docs": "/docs"
    }
```

- [ ] Create FastAPI app instance
- [ ] Add CORS middleware
- [ ] Include health router
- [ ] Include generate router
- [ ] Include status router
- [ ] Include video router
- [ ] Add startup event to initialize database
- [ ] Add root endpoint

### Task 4.2: Implement app/api/health.py

**File:** `backend/app/api/health.py`
```python
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}
```

- [ ] Create APIRouter instance
- [ ] Implement health check endpoint
- [ ] Return simple status response

### Task 4.3: Implement Service Clients

#### 4.3a: app/services/__init__.py
```python
from .replicate import replicate_client
from .openai import openai_client
from .s3 import s3_client
from .ffmpeg import ffmpeg_service

__all__ = [
    "replicate_client",
    "openai_client",
    "s3_client",
    "ffmpeg_service"
]
```

- [ ] Import all service clients
- [ ] Export in `__all__`

#### 4.3b: app/services/replicate.py
```python
import replicate
from app.config import get_settings

settings = get_settings()

class ReplicateClient:
    def __init__(self):
        self.client = replicate.Client(api_token=settings.replicate_api_token)
    
    def run(self, model: str, input: dict):
        """Run a model on Replicate"""
        return self.client.run(model, input=input)

replicate_client = ReplicateClient()
```

- [ ] Import replicate and get settings
- [ ] Create ReplicateClient class
- [ ] Initialize client with API token
- [ ] Implement `run()` method
- [ ] Create singleton instance

#### 4.3c: app/services/openai.py
```python
from openai import OpenAI
from app.config import get_settings

settings = get_settings()

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    @property
    def chat(self):
        return self.client.chat

openai_client = OpenAIClient()
```

- [ ] Import OpenAI and get settings
- [ ] Create OpenAIClient class
- [ ] Initialize client with API key
- [ ] Add chat property
- [ ] Create singleton instance

#### 4.3d: app/services/s3.py
```python
import boto3
from app.config import get_settings

settings = get_settings()

class S3Client:
    def __init__(self):
        self.client = boto3.client(
            's3',
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key
        )
        self.bucket = settings.s3_bucket
    
    def upload_file(self, file_path: str, key: str) -> str:
        """Upload file to S3"""
        self.client.upload_file(file_path, self.bucket, key)
        return f"s3://{self.bucket}/{key}"
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate presigned URL"""
        return self.client.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expiration
        )

s3_client = S3Client()
```

- [ ] Import boto3 and get settings
- [ ] Create S3Client class
- [ ] Initialize boto3 client with credentials
- [ ] Implement `upload_file()` method
- [ ] Implement `generate_presigned_url()` method
- [ ] Create singleton instance

#### 4.3e: app/services/ffmpeg.py
```python
import subprocess

class FFmpegService:
    def run_command(self, command: list) -> str:
        """Run FFmpeg command"""
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout

ffmpeg_service = FFmpegService()
```

- [ ] Import subprocess
- [ ] Create FFmpegService class
- [ ] Implement `run_command()` method
- [ ] Create singleton instance

---

## ✅ PR #3 & #4 Checklist

Before merging:
- [ ] Configuration system working
- [ ] Database models defined
- [ ] All shared schemas created
- [ ] FastAPI app starts without errors
- [ ] Health endpoint accessible at http://localhost:8000/health
- [ ] API docs visible at http://localhost:8000/docs
- [ ] All service clients instantiate without errors

**Test Commands:**
```bash
docker-compose up --build
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

**Next:** Person A → `tasks-phase-1a.md`, Person B → `tasks-phase-2a.md`