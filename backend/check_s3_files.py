#!/usr/bin/env python3
"""
Script to check what files exist in S3 for a video generation.
Usage: docker-compose exec worker python3 check_s3_files.py <video_id> [user_id]
"""
import os
import sys

# Set environment defaults
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/videogen')
os.environ.setdefault('REDIS_URL', 'redis://redis:6379/0')

from app.config import get_settings
from app.services.s3 import s3_client
from app.common.constants import get_video_s3_prefix, MOCK_USER_ID
from app.database import SessionLocal
from app.common.models import VideoGeneration
import boto3

def check_video_files(video_id: str, user_id: str = None):
    """Check what files exist in S3 for a video."""
    settings = get_settings()
    
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
    
    print(f"Checking S3 for video: {video_id}")
    print(f"User ID: {user_id}")
    print(f"Bucket: {settings.s3_bucket}")
    print()
    
    # List all objects for this video
    s3 = boto3.client(
        's3',
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key
    )
    
    # Check new path structure: {userId}/videos/{videoId}/
    video_prefix = get_video_s3_prefix(user_id, video_id) + "/"
    print(f"Checking new path structure: {video_prefix}")
    try:
        response = s3.list_objects_v2(Bucket=settings.s3_bucket, Prefix=video_prefix)
        if 'Contents' in response:
            print(f"✅ Found {len(response['Contents'])} files in new structure:")
            chunks = []
            frames = []
            references = []
            other = []
            
            for obj in response['Contents']:
                size_kb = obj['Size'] / 1024
                key = obj['Key']
                if 'chunk_' in key and key.endswith('.mp4'):
                    chunks.append((key, size_kb))
                elif 'chunk_' in key and key.endswith('_last_frame.png'):
                    frames.append((key, size_kb))
                elif key.endswith('.png') and ('style_guide' in key or 'product_reference' in key or 'uploaded_asset' in key):
                    references.append((key, size_kb))
                else:
                    other.append((key, size_kb))
            
            if chunks:
                print(f"\n  Video Chunks ({len(chunks)}):")
                for key, size_kb in sorted(chunks):
                    print(f"    - {key} ({size_kb:.1f} KB)")
            
            if frames:
                print(f"\n  Last Frames ({len(frames)}):")
                for key, size_kb in sorted(frames):
                    print(f"    - {key} ({size_kb:.1f} KB)")
            
            if references:
                print(f"\n  Reference Images ({len(references)}):")
                for key, size_kb in sorted(references):
                    print(f"    - {key} ({size_kb:.1f} KB)")
            
            if other:
                print(f"\n  Other Files ({len(other)}):")
                for key, size_kb in sorted(other):
                    print(f"    - {key} ({size_kb:.1f} KB)")
        else:
            print("❌ No files found in new structure")
    except Exception as e:
        print(f"Error checking new structure: {e}")
    
    print()
    
    # Check for stitched video (new structure)
    stitched_key = f"{video_prefix}stitched.mp4"
    print(f"Checking stitched video: {stitched_key}")
    try:
        s3.head_object(Bucket=settings.s3_bucket, Key=stitched_key)
        print(f"✅ Stitched video exists!")
        url = s3_client.generate_presigned_url(stitched_key, expiration=3600)
        print(f"   Presigned URL (1 hour): {url[:80]}...")
    except Exception as e:
        print(f"❌ Stitched video not found in new structure")
    
    print()
    
    # Check final video (new structure)
    final_key = f"{video_prefix}final_draft.mp4"
    print(f"Checking final video: {final_key}")
    try:
        s3.head_object(Bucket=settings.s3_bucket, Key=final_key)
        print(f"✅ Final video exists!")
        url = s3_client.generate_presigned_url(final_key, expiration=3600)
        print(f"   Presigned URL (1 hour): {url[:80]}...")
    except Exception as e:
        print(f"❌ Final video not found in new structure")
    
    print()
    
    # Check music (new structure)
    music_key = f"{video_prefix}background.mp3"
    print(f"Checking music: {music_key}")
    try:
        s3.head_object(Bucket=settings.s3_bucket, Key=music_key)
        print(f"✅ Music exists!")
        url = s3_client.generate_presigned_url(music_key, expiration=3600)
        print(f"   Presigned URL (1 hour): {url[:80]}...")
    except Exception as e:
        print(f"❌ Music not found in new structure")
    
    print()
    print("=" * 70)
    print("Checking old path structures (for backward compatibility)...")
    print("=" * 70)
    print()
    
    # Check old chunks path (for backward compatibility)
    chunks_prefix = f"chunks/{video_id}/"
    print(f"Checking old chunks path: {chunks_prefix}")
    try:
        response = s3.list_objects_v2(Bucket=settings.s3_bucket, Prefix=chunks_prefix)
        if 'Contents' in response:
            print(f"⚠️  Found {len(response['Contents'])} files in old chunks path (legacy)")
        else:
            print("✅ No files in old chunks path (expected for new videos)")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Check old references path (for backward compatibility)
    refs_prefix = f"references/{video_id}/"
    print(f"Checking old references path: {refs_prefix}")
    try:
        response = s3.list_objects_v2(Bucket=settings.s3_bucket, Prefix=refs_prefix)
        if 'Contents' in response:
            print(f"⚠️  Found {len(response['Contents'])} files in old references path (legacy)")
        else:
            print("✅ No files in old references path (expected for new videos)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_s3_files.py <video_id> [user_id]")
        print("Example: python3 check_s3_files.py d782ddd0-2e28-417e-81fb-d94f16d9c8a9")
        print("         python3 check_s3_files.py d782ddd0-2e28-417e-81fb-d94f16d9c8a9 user-123")
        sys.exit(1)
    
    video_id = sys.argv[1]
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    check_video_files(video_id, user_id)
