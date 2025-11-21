from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import generate, status, video, health, upload, assets
from app.database import init_db
from app.common.logging import setup_logging
from app.services.firebase_auth import initialize_firebase
from app.config import get_settings
import logging

# Initialize logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Video Generation API",
    description="AI-powered video generation pipeline",
    version="1.0.0"
)

# CORS middleware
# In development, allow localhost origins; in production, only allow specific domains
if settings.environment == "development":
    allow_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
else:
    allow_origins = [
        "https://aivideo.gauntlet3.com",
        "https://videoai.gauntlet3.com",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(generate.router, tags=["generation"])
app.include_router(status.router, tags=["status"])
app.include_router(video.router, tags=["video"])
# Register assets router BEFORE upload router to ensure more specific routes match first
app.include_router(assets.router, tags=["assets"])
app.include_router(upload.router, tags=["upload"])

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database, Firebase, and CLIP model on startup"""
    init_db()
    
    # Initialize Firebase Admin SDK
    try:
        initialize_firebase()
    except Exception as e:
        logger.warning(f"Firebase initialization failed: {e}")
        logger.warning("Authentication will not work until Firebase is properly configured")
    
    # Load CLIP model in background (non-blocking)
    # This happens after app is ready to serve requests
    import asyncio
    from app.services.clip_embeddings import clip_service
    
    async def load_clip_model():
        """Background task to load CLIP model"""
        try:
            logger.info("🔄 Loading CLIP model in background...")
            await asyncio.to_thread(clip_service.load_model)
            logger.info("✅ CLIP model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load CLIP model: {e}", exc_info=True)
            logger.warning("CLIP-based semantic search will not be available")
    
    # Start loading in background (don't await - let it run while app serves requests)
    asyncio.create_task(load_clip_model())

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Video Generation API",
        "docs": "/docs"
    }
