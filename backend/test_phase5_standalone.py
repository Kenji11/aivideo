#!/usr/bin/env python3
"""
Standalone Phase 5 Test - Fetches video from database
Prompts for video ID and runs Phase 5 refinement on existing video
"""
import sys
import os
from pathlib import Path

# Load .env if exists
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}")
    print("   Make sure environment variables are set")

# Override database URL for local testing (connects to Docker Compose postgres on localhost)
os.environ['DATABASE_URL'] = 'postgresql://dev:devpass@localhost:5434/videogen'

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import SessionLocal
from app.common.models import VideoGeneration
from app.phases.phase5_refine.service import RefinementService

def test_phase5_standalone(video_id: str = None):
    """Test Phase 5 by fetching video from database"""
    
    print("=" * 80)
    print("🎵 Phase 5 Standalone Test - Audio Generation")
    print("=" * 80)
    print()
    
    # Get video ID from argument or prompt
    if not video_id:
        if len(sys.argv) > 1:
            video_id = sys.argv[1]
        else:
            video_id = input("Enter video ID: ").strip()
            if not video_id:
                print("❌ Video ID is required")
                print()
                print("Usage:")
                print("  python test_phase5_standalone.py <video_id>")
                print()
                print("Example:")
                print("  python test_phase5_standalone.py 550e8400-e29b-41d4-a716-446655440000")
                return 1
    
    # Fetch video from database
    print(f"🔍 Fetching video {video_id} from database...")
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        
        if not video:
            print(f"❌ Video not found: {video_id}")
            print()
            print("💡 Tip: Use scripts/list_recent_videos.py to see available videos")
            return 1
        
        # Check if video has stitched URL
        if not video.stitched_url:
            print(f"❌ Video {video_id} does not have a stitched_url")
            print(f"   Current status: {video.status}")
            print()
            print("💡 Video must have completed Phase 4 (stitching) before running Phase 5")
            return 1
        
        # Extract necessary information
        stitched_url = video.stitched_url
        spec = video.spec or {}
        user_id = video.user_id
        
        print("✅ Video found!")
        print()
        print(f"📹 Video Information:")
        print(f"   Video ID: {video_id}")
        print(f"   User ID: {user_id}")
        print(f"   Title: {video.title}")
        print(f"   Status: {video.status}")
        print(f"   Prompt: {video.prompt[:100]}..." if len(video.prompt) > 100 else f"   Prompt: {video.prompt}")
        print(f"   Stitched URL: {stitched_url}")
        
        # Show audio config if available
        if 'audio' in spec:
            audio = spec['audio']
            print(f"   Audio Config:")
            print(f"     - Style: {audio.get('music_style', 'N/A')}")
            print(f"     - Tempo: {audio.get('tempo', 'N/A')}")
            print(f"     - Mood: {audio.get('mood', 'N/A')}")
        else:
            print(f"   ⚠️  No audio config in spec (will use defaults)")
        
        print()
        print("🚀 Starting Phase 5 (Audio Generation)...")
        print()
        
        # Run Phase 5
        service = RefinementService()
        refined_url, music_url = service.refine_all(video_id, stitched_url, spec, user_id)
        
        print()
        print("=" * 80)
        print("✅ Phase 5 Test: SUCCESS!")
        print("=" * 80)
        print(f"   Video ID: {video_id}")
        print(f"   Refined Video URL: {refined_url}")
        print(f"   Music URL: {music_url or 'N/A'}")
        print(f"   Total Cost: ${service.total_cost:.4f}")
        print("=" * 80)
        return 0
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Phase 5 Test: FAILED")
        print("=" * 80)
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        print()
        print("   Full Traceback:")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    video_id = sys.argv[1] if len(sys.argv) > 1 else None
    exit(test_phase5_standalone(video_id))

