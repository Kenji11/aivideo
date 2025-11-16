#!/usr/bin/env python3
"""
Standalone Phase 5 Test - Works without database
Just needs a stitched video URL to test audio generation
"""
import sys
import os
import uuid
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

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.phases.phase5_refine.service import RefinementService
from app.common.constants import MOCK_USER_ID

def test_phase5_standalone(stitched_url: str = None, user_id: str = None):
    """Test Phase 5 with a stitched video URL"""
    
    print("=" * 80)
    print("🎵 Phase 5 Standalone Test - Audio Generation")
    print("=" * 80)
    print()
    
    # Get stitched URL from argument or prompt
    if not stitched_url:
        if len(sys.argv) > 1:
            stitched_url = sys.argv[1]
        else:
            print("❌ Please provide a stitched video URL")
            print()
            print("Usage:")
            print("  python test_phase5_standalone.py <stitched_video_url> [user_id]")
            print()
            print("Example:")
            print("  python test_phase5_standalone.py s3://bucket/user123/videos/abc123/stitched.mp4 user123")
            print("  python test_phase5_standalone.py s3://bucket/user123/videos/abc123/stitched.mp4")
            print()
            print("Or get from last video:")
            print("  # Check docker logs or database for stitched_url")
            return 1
    
    # Create test video ID
    video_id = str(uuid.uuid4())
    
    # Use provided user_id or default to mock
    if not user_id:
        user_id = MOCK_USER_ID
        print(f"⚠️  No user_id provided, using mock user ID: {user_id}")
    
    # Create minimal spec with audio
    spec = {
        'duration': 30,
        'audio': {
            'music_style': 'orchestral',
            'tempo': 'moderate',
            'mood': 'sophisticated'
        }
    }
    
    print(f"📹 Test Configuration:")
    print(f"   Video ID: {video_id}")
    print(f"   User ID: {user_id}")
    print(f"   Stitched URL: {stitched_url}")
    print(f"   Duration: {spec['duration']}s")
    print(f"   Audio Style: {spec['audio']['music_style']}")
    print(f"   Tempo: {spec['audio']['tempo']}")
    print(f"   Mood: {spec['audio']['mood']}")
    print()
    print("🚀 Starting Phase 5 (Audio Generation)...")
    print()
    
    try:
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

if __name__ == "__main__":
    stitched_url = sys.argv[1] if len(sys.argv) > 1 else None
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    # Example with old path structure (for backward compatibility testing)
    # exit(test_phase5_standalone("s3://ai-video-assets-dev/chunks/695dd358-fa93-47ba-99b5-8b14dff9c0fd/stitched.mp4", "user-123"))
    exit(test_phase5_standalone(stitched_url, user_id))

