#!/usr/bin/env python3
"""
Test utility to reuse last generated video for Phase 5 testing.

This script loads the most recent video generation from the database and
runs Phase 5 (music generation) directly, skipping Phases 1-4.

Usage:
    python test_with_last_video.py

This saves time and cost during iterative testing (~$2-3 per test avoided).
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.common.models import VideoGeneration, VideoStatus
from app.phases.phase5_refine.service import RefinementService
from sqlalchemy import desc, create_engine
from sqlalchemy.orm import sessionmaker
import time

# Hardcoded database URL for local testing (Docker postgres exposed on port 5433)
DATABASE_URL = "postgresql://dev:devpass@localhost:5433/videogen"

# Create engine and session for test script
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_last_video():
    """Get the most recent completed video generation from database."""
    try:
        db = SessionLocal()
    except Exception as e:
        print("="*70)
        print("❌ DATABASE CONNECTION ERROR")
        print("="*70)
        print(f"Error: {str(e)}")
        print("")
        print("💡 TROUBLESHOOTING:")
        print("   1. If using Docker, make sure the database container is running:")
        print("      docker-compose up -d postgres")
        print("")
        print("   2. For local testing, update DATABASE_URL in .env:")
        print("      Change: postgresql://dev:devpass@postgres:5432/videogen")
        print("      To:     postgresql://dev:devpass@localhost:5433/videogen")
        print("      (Note: port 5433 is exposed from Docker container)")
        print("")
        print("   3. Or run the script inside Docker:")
        print("      docker-compose exec api python test_with_last_video.py")
        print("="*70)
        return None
    
    try:
        # Query for most recent video that has a stitched_url (Phase 4 completed)
        video = db.query(VideoGeneration).filter(
            VideoGeneration.stitched_url.isnot(None)
        ).order_by(desc(VideoGeneration.created_at)).first()
        
        if not video:
            print("❌ No video found with stitched_url. Run a full pipeline first.")
            return None
        
        print("="*70)
        print("📹 LAST GENERATED VIDEO FOUND")
        print("="*70)
        print(f"Video ID: {video.id}")
        print(f"Title: {video.title}")
        print(f"Status: {video.status.value}")
        print(f"Created: {video.created_at}")
        print(f"Progress: {video.progress}%")
        print(f"Current Phase: {video.current_phase}")
        print(f"Cost: ${video.cost_usd:.4f}")
        print("")
        print("📹 VIDEO URLS:")
        print(f"   Stitched URL: {video.stitched_url}")
        print(f"   Refined URL: {video.refined_url or 'N/A'}")
        print(f"   Final URL: {video.final_video_url or 'N/A'}")
        print("")
        print("📋 SPEC:")
        if video.spec:
            import json
            spec_str = json.dumps(video.spec, indent=2)
            print(spec_str)
        else:
            print("   ❌ No spec found")
        print("")
        print("📝 PROMPT:")
        print(f"   Original: {video.prompt}")
        print(f"   Validated: {video.prompt_validated or 'N/A'}")
        print("")
        print("🎬 TEMPLATE:")
        print(f"   {video.template or 'N/A'}")
        print("")
        print("📊 PHASE OUTPUTS:")
        if video.phase_outputs:
            for phase, output in video.phase_outputs.items():
                status = output.get('status', 'unknown')
                cost = output.get('cost_usd', 0)
                print(f"   {phase}: {status} (${cost:.4f})")
        else:
            print("   No phase outputs")
        print("="*70)
        
        if not video.spec:
            print("⚠️  Warning: Video has no spec. Phase 5 may fail.")
        
        return video
    finally:
        db.close()


def run_phase5_test(video_id: str, stitched_url: str, spec: dict):
    """Run Phase 5 directly with existing video."""
    import json
    
    print("\n" + "="*70)
    print("🎵 PHASE 5 INPUTS")
    print("="*70)
    print(f"Video ID: {video_id}")
    print("")
    print("📹 STITCHED VIDEO URL:")
    print(f"   {stitched_url}")
    print("")
    print("📋 SPEC:")
    if spec:
        spec_str = json.dumps(spec, indent=2)
        print(spec_str)
    else:
        print("   ⚠️  Empty spec - using defaults")
    print("")
    print("🎵 AUDIO SPEC (from template):")
    audio_spec = spec.get('audio', {}) if spec else {}
    print(f"   Music Style: {audio_spec.get('music_style', 'N/A')}")
    print(f"   Tempo: {audio_spec.get('tempo', 'N/A')}")
    print(f"   Mood: {audio_spec.get('mood', 'N/A')}")
    print("")
    print("⏱️  VIDEO DURATION:")
    duration = spec.get('duration', 30) if spec else 30
    print(f"   {duration} seconds")
    print("="*70)
    print("")
    print("🚀 Starting Phase 5 execution...")
    print("")
    
    # Run Phase 5 service directly (avoiding circular import with Celery)
    start_time = time.time()
    service = RefinementService()
    
    try:
        final_url, music_url = service.refine_all(video_id, stitched_url, spec)
        duration_seconds = time.time() - start_time
        
        result_dict = {
            'status': 'success',
            'duration_seconds': duration_seconds,
            'cost_usd': service.total_cost,
            'output_data': {
                'refined_video_url': final_url,
                'music_url': music_url
            }
        }
    except Exception as e:
        duration_seconds = time.time() - start_time
        result_dict = {
            'status': 'failed',
            'duration_seconds': duration_seconds,
            'cost_usd': service.total_cost,
            'error_message': str(e),
            'output_data': {}
        }
    
    print("\n" + "="*70)
    if result_dict['status'] == 'success':
        print("✅ Phase 5 completed successfully!")
        print(f"   - Duration: {result_dict.get('duration_seconds', 0):.2f}s")
        print(f"   - Cost: ${result_dict.get('cost_usd', 0):.4f}")
        output_data = result_dict.get('output_data', {})
        if 'refined_video_url' in output_data:
            print(f"   - Final video: {output_data['refined_video_url']}")
        if 'music_url' in output_data:
            print(f"   - Music: {output_data['music_url']}")
    else:
        print("❌ Phase 5 failed!")
        print(f"   Error: {result_dict.get('error_message', 'Unknown error')}")
    print("="*70)
    
    return result_dict


def main():
    """Main entry point."""
    print("🔍 Loading last generated video from database...")
    
    video = get_last_video()
    if not video:
        return 1
    
    if not video.stitched_url:
        print("❌ Video has no stitched_url. Cannot run Phase 5.")
        return 1
    
    if not video.spec:
        print("⚠️  Warning: Video has no spec. Attempting to continue...")
        spec = {}
    else:
        spec = video.spec
    
    # Run Phase 5
    result = run_phase5_test(video.id, video.stitched_url, spec)
    
    if result['status'] == 'success':
        print("\n✅ Test completed successfully!")
        return 0
    else:
        print("\n❌ Test failed!")
        return 1


if __name__ == "__main__":
    exit(main())
