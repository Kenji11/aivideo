from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import generate, status, video, health, upload
from app.database import init_db
from app.common.logging import setup_logging
from app.services.firebase_auth import initialize_firebase
import logging

# Initialize logging
setup_logging("INFO")
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Video Generation API",
    description="AI-powered video generation pipeline",
    version="1.0.0"
)

# CORS middleware
# Allow both frontend domains to access both API domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aivideo.gauntlet3.com",
        "https://videoai.gauntlet3.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(generate.router, tags=["generation"])
app.include_router(status.router, tags=["status"])
app.include_router(video.router, tags=["video"])
app.include_router(upload.router, tags=["upload"])

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and Firebase on startup"""
    init_db()
    
    # Initialize Firebase Admin SDK
    try:
        initialize_firebase()
    except Exception as e:
        logger.warning(f"Firebase initialization failed: {e}")
        logger.warning("Authentication will not work until Firebase is properly configured")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Video Generation API",
        "docs": "/docs"
    }
