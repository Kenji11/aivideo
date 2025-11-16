#!/usr/bin/env python3
"""
Test Phase 5 (Audio Generation) directly
Bypasses Phase 4 to test if audio generation works
"""
import sys
import os
import uuid

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.phases.phase5_refine.task import refine_video
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.services.s3 import s3_client

def test_phase5():
    """Test Phase 5 audio generation with a test video"""
    
    print("=" * 80)
    print("🎵 Testing Phase 5: Audio Generation")
    print("=" * 80)
    print()
    
    # Option 1: Use existing video's stitched URL
    # Option 2: Use a test video URL
    # Let's check if there's a recent video with a stitched URL
    
    db = SessionLocal()
    try:
        # Get the most recent video with a stitched URL
        video = db.query(VideoGeneration).filter(
            VideoGeneration.stitched_url.isnot(None)
        ).order_by(VideoGeneration.created_at.desc()).first()
        
        if video:
            video_id = video.id
            stitched_url = video.stitched_url
            print(f"📹 Found video: {video_id}")
            print(f"   Title: {video.title}")
            print(f"   Stitched URL: {stitched_url[:80]}...")
            
            # Get spec from video
            if video.spec:
                spec = video.spec
            else:
                # Create minimal spec with audio
                spec = {
                    'duration': 30,
                    'audio': {
                        'music_style': 'orchestral',
                        'tempo': 'moderate',
                        'mood': 'sophisticated'
                    }
                }
        else:
            print("⚠️  No video with stitched URL found.")
            print("   Creating test video...")
            
            # Create a test video record
            video_id = str(uuid.uuid4())
            test_video = VideoGeneration(
                id=video_id,
                title="Phase 5 Test Video",
                status=VideoStatus.QUEUED,
                progress=75.0,
                current_phase="phase4_chunks"
            )
            db.add(test_video)
            db.commit()
            
            # Use a test stitched URL (you'll need to provide a real S3 URL or create a test video)
            print("   ⚠️  Please provide a stitched video URL to test with.")
            print("   Or generate a video first to get a stitched URL.")
            print()
            print("   Usage:")
            print("   python test_phase5.py <stitched_video_url>")
            return
            
    finally:
        db.close()
    
    # Create spec with audio if not present
    if 'audio' not in spec:
        spec['audio'] = {
            'music_style': 'orchestral',
            'tempo': 'moderate',
            'mood': 'sophisticated'
        }
    
    print()
    print(f"📋 Spec:")
    print(f"   Duration: {spec.get('duration', 30)}s")
    print(f"   Audio: {spec.get('audio', {})}")
    print()
    print("🚀 Running Phase 5...")
    print()
    
    try:
        # Run Phase 5 task directly
        result = refine_video(video_id, stitched_url, spec)
        
        print()
        print("=" * 80)
        if result.get('status') == 'success':
            print("✅ Phase 5 Test: SUCCESS!")
            print("=" * 80)
            print(f"   Video ID: {video_id}")
            print(f"   Refined Video URL: {result.get('output_data', {}).get('refined_video_url', 'N/A')}")
            print(f"   Music URL: {result.get('output_data', {}).get('music_url', 'N/A')}")
            print(f"   Cost: ${result.get('cost_usd', 0):.4f}")
            print(f"   Duration: {result.get('duration_seconds', 0):.2f}s")
        else:
            print("❌ Phase 5 Test: FAILED")
            print("=" * 80)
            print(f"   Error: {result.get('error_message', 'Unknown error')}")
        print("=" * 80)
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Phase 5 Test: EXCEPTION")
        print("=" * 80)
        print(f"   Error: {str(e)}")
        import traceback
        print()
        print("   Full traceback:")
        traceback.print_exc()
        print("=" * 80)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use provided stitched URL
        stitched_url = sys.argv[1]
        video_id = str(uuid.uuid4())
        
        spec = {
            'duration': 30,
            'audio': {
                'music_style': 'orchestral',
                'tempo': 'moderate',
                'mood': 'sophisticated'
            }
        }
        
        print("=" * 80)
        print("🎵 Testing Phase 5 with provided URL")
        print("=" * 80)
        print(f"   Video ID: {video_id}")
        print(f"   Stitched URL: {stitched_url[:80]}...")
        print()
        
        try:
            result = refine_video(video_id, stitched_url, spec)
            
            print()
            print("=" * 80)
            if result.get('status') == 'success':
                print("✅ Phase 5 Test: SUCCESS!")
                print("=" * 80)
                print(f"   Refined Video URL: {result.get('output_data', {}).get('refined_video_url', 'N/A')}")
                print(f"   Music URL: {result.get('output_data', {}).get('music_url', 'N/A')}")
                print(f"   Cost: ${result.get('cost_usd', 0):.4f}")
                print(f"   Duration: {result.get('duration_seconds', 0):.2f}s")
            else:
                print("❌ Phase 5 Test: FAILED")
                print("=" * 80)
                print(f"   Error: {result.get('error_message', 'Unknown error')}")
            print("=" * 80)
        except Exception as e:
            print()
            print("=" * 80)
            print("❌ Phase 5 Test: EXCEPTION")
            print("=" * 80)
            print(f"   Error: {str(e)}")
            import traceback
            traceback.print_exc()
            print("=" * 80)
    else:
        test_phase5()

