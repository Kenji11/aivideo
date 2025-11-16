#!/usr/bin/env python3
"""
Script to check what files exist in S3 for a video generation.
Usage: docker-compose exec worker python3 check_s3_files.py <video_id>
"""
import os
import sys

# Set environment defaults
os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:postgres@postgres:5432/videogen')
os.environ.setdefault('REDIS_URL', 'redis://redis:6379/0')

from app.config import get_settings
from app.services.s3 import s3_client
import boto3

def check_video_files(video_id: str):
    """Check what files exist in S3 for a video."""
    settings = get_settings()
    
    print(f"Checking S3 for video: {video_id}")
    print(f"Bucket: {settings.s3_bucket}")
    print()
    
    # List all objects for this video
    s3 = boto3.client(
        's3',
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key
    )
    
    # Check chunks
    chunks_prefix = f"chunks/{video_id}/"
    print(f"Checking chunks: {chunks_prefix}")
    try:
        response = s3.list_objects_v2(Bucket=settings.s3_bucket, Prefix=chunks_prefix)
        if 'Contents' in response:
            print(f"✅ Found {len(response['Contents'])} files:")
            chunks = []
            frames = []
            other = []
            
            for obj in response['Contents']:
                size_kb = obj['Size'] / 1024
                key = obj['Key']
                if 'chunk_' in key and key.endswith('.mp4'):
                    chunks.append((key, size_kb))
                elif 'frames/' in key:
                    frames.append((key, size_kb))
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
            
            if other:
                print(f"\n  Other Files ({len(other)}):")
                for key, size_kb in sorted(other):
                    print(f"    - {key} ({size_kb:.1f} KB)")
        else:
            print("❌ No files found")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Check for stitched video
    stitched_key = f"chunks/{video_id}/stitched.mp4"
    print(f"Checking stitched video: {stitched_key}")
    try:
        s3.head_object(Bucket=settings.s3_bucket, Key=stitched_key)
        print(f"✅ Stitched video exists!")
        url = s3_client.generate_presigned_url(stitched_key, expiration=3600)
        print(f"   Presigned URL (1 hour): {url[:80]}...")
    except Exception as e:
        print(f"❌ Stitched video not found")
    
    print()
    
    # Check final video
    final_key = f"final/{video_id}/refined_video.mp4"
    print(f"Checking final video: {final_key}")
    try:
        s3.head_object(Bucket=settings.s3_bucket, Key=final_key)
        print(f"✅ Final video exists!")
        url = s3_client.generate_presigned_url(final_key, expiration=3600)
        print(f"   Presigned URL (1 hour): {url[:80]}...")
    except Exception as e:
        print(f"❌ Final video not found")
    
    print()
    
    # Check animatic frames
    animatic_prefix = f"animatic/{video_id}/"
    print(f"Checking animatic frames: {animatic_prefix}")
    try:
        response = s3.list_objects_v2(Bucket=settings.s3_bucket, Prefix=animatic_prefix)
        if 'Contents' in response:
            print(f"✅ Found {len(response['Contents'])} animatic frames")
        else:
            print("❌ No animatic frames found")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    
    # Check reference assets
    refs_prefix = f"references/{video_id}/"
    print(f"Checking reference assets: {refs_prefix}")
    try:
        response = s3.list_objects_v2(Bucket=settings.s3_bucket, Prefix=refs_prefix)
        if 'Contents' in response:
            print(f"✅ Found {len(response['Contents'])} reference assets")
            for obj in response['Contents']:
                size_kb = obj['Size'] / 1024
                print(f"    - {obj['Key']} ({size_kb:.1f} KB)")
        else:
            print("❌ No reference assets found")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_s3_files.py <video_id>")
        print("Example: python3 check_s3_files.py d782ddd0-2e28-417e-81fb-d94f16d9c8a9")
        sys.exit(1)
    
    video_id = sys.argv[1]
    check_video_files(video_id)
