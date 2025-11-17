#!/usr/bin/env python3
"""Re-run Phase 5 on an existing video to test music library."""

from app.database import get_db
from app.common.models import VideoGeneration
from app.phases.phase5_refine.service import RefinementService

# Video ID to test
VIDEO_ID = "2112d63b-f819-4cb2-85c7-1ba982cee54b"

def main():
    db = next(get_db())
    video = db.query(VideoGeneration).filter(VideoGeneration.id == VIDEO_ID).first()
    
    if not video:
        print(f"❌ Video {VIDEO_ID} not found")
        return
    
    if not video.stitched_url:
        print(f"❌ Video {VIDEO_ID} has no stitched URL")
        return
    
    print(f"✅ Found video: {VIDEO_ID}")
    print(f"   Title: {video.title}")
    print(f"   Stitched URL: {video.stitched_url}")
    print(f"   Status: {video.status.value}")
    print()
    print("🎬 Re-running Phase 5 with music library...")
    print()
    
    # Run Phase 5
    service = RefinementService()
    try:
        final_url, music_url = service.refine_all(
            video_id=video.id,
            stitched_url=video.stitched_url,
            spec=video.spec,
            user_id=video.user_id
        )
        
        print()
        print("✅ Phase 5 completed successfully!")
        print(f"   Final video URL: {final_url}")
        print(f"   Music URL: {music_url}")
        
        # Update database
        video.final_video_url = final_url
        video.final_music_url = music_url
        db.commit()
        print()
        print("✅ Database updated with new final video and music URLs")
        
    except Exception as e:
        print(f"❌ Phase 5 failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

