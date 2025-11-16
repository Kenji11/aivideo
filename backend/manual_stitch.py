#!/usr/bin/env python3
"""
Manual script to stitch video chunks that failed during automatic stitching.
Usage: docker-compose exec worker python3 manual_stitch.py <video_id> [user_id]
"""
import os
import sys

# Set environment defaults
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/videogen')
os.environ.setdefault('REDIS_URL', 'redis://redis:6379/0')

from app.services.s3 import s3_client
from app.phases.phase4_chunks.stitcher import VideoStitcher
from app.common.constants import get_video_s3_key, MOCK_USER_ID
from app.database import SessionLocal
from app.common.models import VideoGeneration

def stitch_video(video_id: str, user_id: str = None):
    """Manually stitch chunks for a video that failed during automatic stitching."""
    print(f"🔧 Manually stitching chunks for video: {video_id}")
    print()
    
    # Get user_id from database if not provided
    if not user_id:
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video and video.user_id:
                user_id = video.user_id
                print(f"✅ Found user_id from database: {user_id}")
            else:
                user_id = MOCK_USER_ID
                print(f"⚠️  No user_id found, using mock user ID: {user_id}")
        finally:
            db.close()
    
    # Get all chunk URLs from S3 (check new path structure first, fallback to old)
    chunk_urls = []
    chunk_count = 0
    
    # Try new path structure first: {userId}/videos/{videoId}/chunk_{NN}.mp4
    for i in range(30):  # Check up to 30 chunks
        chunk_key = get_video_s3_key(user_id, video_id, f"chunk_{i:02d}.mp4")
        try:
            # Check if chunk exists
            s3_client.client.head_object(Bucket=s3_client.bucket, Key=chunk_key)
            chunk_url = f"s3://{s3_client.bucket}/{chunk_key}"
            chunk_urls.append(chunk_url)
            chunk_count += 1
        except Exception:
            # Try old path structure as fallback
            old_chunk_key = f"chunks/{video_id}/chunk_{i:02d}.mp4"
            try:
                s3_client.client.head_object(Bucket=s3_client.bucket, Key=old_chunk_key)
                chunk_url = f"s3://{s3_client.bucket}/{old_chunk_key}"
                chunk_urls.append(chunk_url)
                chunk_count += 1
            except Exception:
                # Chunk doesn't exist in either location, stop looking
                if i == 0:
                    # If first chunk doesn't exist, try a few more before giving up
                    continue
                break
    
    if chunk_count == 0:
        print(f"❌ No chunks found for video {video_id}")
        print(f"   Checked paths:")
        print(f"   - New: {get_video_s3_key(user_id, video_id, 'chunk_00.mp4')}")
        print(f"   - Old: chunks/{video_id}/chunk_00.mp4")
        return
    
    print(f"Found {chunk_count} chunks to stitch")
    print()
    
    # Stitch them together
    stitcher = VideoStitcher()
    try:
        stitched_url = stitcher.stitch_with_transitions(
            video_id=video_id,
            chunk_urls=chunk_urls,
            transitions=[],  # Simple cuts
            user_id=user_id
        )
        
        print()
        print("✅ Stitching successful!")
        print(f"Stitched video URL: {stitched_url}")
        print()
        
        # Generate presigned URL (use new path structure)
        stitched_key = get_video_s3_key(user_id, video_id, "stitched.mp4")
        presigned_url = s3_client.generate_presigned_url(stitched_key, expiration=3600 * 24 * 7)  # 7 days
        print(f"Presigned URL (7 days):")
        print(presigned_url)
        
    except Exception as e:
        print(f"❌ Stitching failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 manual_stitch.py <video_id> [user_id]")
        print("Example: python3 manual_stitch.py d782ddd0-2e28-417e-81fb-d94f16d9c8a9")
        print("         python3 manual_stitch.py d782ddd0-2e28-417e-81fb-d94f16d9c8a9 user-123")
        sys.exit(1)
    
    video_id = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    stitch_video(video_id, user_id)
