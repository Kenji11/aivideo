#!/usr/bin/env python3
"""
Display the 5 most recently added videos from the database.

Usage:
    python backend/scripts/list_recent_videos.py
    or from backend directory:
    python scripts/list_recent_videos.py
"""
import sys
import os
from pathlib import Path

# Add parent directory (backend) to path
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

from sqlalchemy import desc, create_engine, Column, String, Float, DateTime, JSON, Enum as SQLEnum, Integer
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv
import enum
import json

# Load .env file from backend directory
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory as fallback
    load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("="*70)
    print("❌ ERROR: DATABASE_URL environment variable not set")
    print("="*70)
    print("Please set DATABASE_URL in your .env file or as an environment variable.")
    print(f"Expected .env file location: {env_path}")
    print("Example: DATABASE_URL=postgresql://dev:devpass@localhost:5432/videogen")
    print("="*70)
    sys.exit(1)

# Create Base without importing from app.database (which requires full config)
Base = declarative_base()

# Define VideoStatus enum (copied from models to avoid import)
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

# Define VideoGeneration model (copied to avoid importing app.database)
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
    prompt_validated = Column(String, nullable=True)
    reference_assets = Column(JSON, default=list)
    
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
    chunk_urls = Column(JSON, default=list)
    stitched_url = Column(String, nullable=True)
    refined_url = Column(String, nullable=True)
    final_video_url = Column(String, nullable=True)
    phase_outputs = Column(JSON, default=dict)
    
    # Metadata
    cost_usd = Column(Float, default=0.0)
    cost_breakdown = Column(JSON, default=dict)
    generation_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

# Create engine and session
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def list_recent_videos(limit=5):
    """List the most recent videos from the database."""
    db = SessionLocal()
    try:
        # Query for most recent videos
        videos = db.query(VideoGeneration).order_by(
            desc(VideoGeneration.created_at)
        ).limit(limit).all()
        
        if not videos:
            print("No videos found in database.")
            return
        
        print("="*70)
        print(f"📹 MOST RECENT {len(videos)} VIDEOS")
        print("="*70)
        print("")
        
        for i, video in enumerate(videos, 1):
            print(f"#{i} - {video.id}")
            print(f"   Title: {video.title}")
            print(f"   Status: {video.status.value}")
            print(f"   Progress: {video.progress}%")
            print(f"   Current Phase: {video.current_phase or 'N/A'}")
            print(f"   Created: {video.created_at}")
            print(f"   Cost: ${video.cost_usd:.4f}")
            print("")
            print("   📹 URLs:")
            print(f"      Stitched: {video.stitched_url or 'N/A'}")
            print(f"      Refined: {video.refined_url or 'N/A'}")
            print(f"      Final: {video.final_video_url or 'N/A'}")
            print("")
            print("   📝 Prompt:")
            print(f"      {video.prompt[:100]}{'...' if len(video.prompt) > 100 else ''}")
            print("")
            print("   🎬 Template:")
            print(f"      {video.template or 'N/A'}")
            print("")
            if video.spec:
                print("   📋 Spec (duration, beats, etc.):")
                spec_summary = {
                    'duration': video.spec.get('duration', 'N/A'),
                    'template': video.spec.get('template', 'N/A'),
                    'num_beats': len(video.spec.get('beats', [])) if 'beats' in video.spec else 'N/A'
                }
                print(f"      {json.dumps(spec_summary, indent=6)}")
            print("")
            if i < len(videos):
                print("-" * 70)
                print("")
        
        print("="*70)
        
    except Exception as e:
        print("="*70)
        print("❌ DATABASE ERROR")
        print("="*70)
        print(f"Error: {str(e)}")
        print("")
        print("💡 TROUBLESHOOTING:")
        print("   1. Make sure DATABASE_URL environment variable is set correctly")
        print("   2. Make sure Docker postgres container is running:")
        print("      docker-compose up -d postgres")
        print("   3. Check that database is accessible at the URL specified in DATABASE_URL")
        print("="*70)
    finally:
        db.close()


def main():
    """Main entry point."""
    list_recent_videos(limit=5)


if __name__ == "__main__":
    main()

