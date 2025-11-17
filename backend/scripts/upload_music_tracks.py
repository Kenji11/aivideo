#!/usr/bin/env python3
"""
Script to upload music tracks to S3.

The tracks will be stored in S3, and Phase 5 will crop them to match video duration.
"""

import os
import sys
from pathlib import Path

# Import only what we need
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# S3 prefix for music library
S3_MUSIC_PREFIX = "music-library"


def get_s3_client():
    """Create S3 client from environment variables."""
    return boto3.client(
        's3',
        region_name=os.getenv('AWS_REGION', 'us-east-2'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
    )


def get_s3_bucket() -> str:
    """Get S3 bucket name from environment."""
    return os.getenv('S3_BUCKET', 'videogen-outputs-dev')


def detect_genre(filename: str) -> str:
    """Try to detect genre from filename."""
    filename_lower = filename.lower()
    
    if any(word in filename_lower for word in ['upbeat', 'happy', 'energetic', 'party', 'celebration']):
        return 'upbeat'
    elif any(word in filename_lower for word in ['cinematic', 'epic', 'dramatic', 'orchestral']):
        return 'cinematic'
    elif any(word in filename_lower for word in ['corporate', 'business', 'professional']):
        return 'corporate'
    elif any(word in filename_lower for word in ['calm', 'peaceful', 'relaxing', 'ambient', 'chill']):
        return 'calm'
    elif any(word in filename_lower for word in ['energetic', 'fast', 'intense', 'action', 'power']):
        return 'energetic'
    elif any(word in filename_lower for word in ['background', 'ambient', 'atmospheric']):
        return 'background'
    elif any(word in filename_lower for word in ['advertising', 'commercial', 'promotional']):
        return 'advertising'
    else:
        # Default to 'upbeat' for Musicbed tracks
        return 'upbeat'


def upload_music_directory(music_dir: str, s3_client, bucket: str):
    """Upload all music files to S3, organized by genre."""
    music_path = Path(music_dir)
    
    if not music_path.exists():
        print(f"❌ Directory not found: {music_dir}")
        return
    
    print(f"📁 Scanning directory: {music_dir}")
    print("=" * 60)
    
    # Find all audio files
    audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.aac'}
    audio_files = [f for f in music_path.iterdir() 
                   if f.is_file() and f.suffix.lower() in audio_extensions]
    
    if not audio_files:
        print(f"   ⚠️  No audio files found in {music_dir}")
        return
    
    print(f"📊 Found {len(audio_files)} audio file(s)")
    print("=" * 60)
    
    total_uploaded = 0
    total_failed = 0
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"\n🎵 Processing {i}/{len(audio_files)}: {audio_file.name}")
        
        # Detect genre
        genre = detect_genre(audio_file.name)
        print(f"   🎼 Genre: {genre}")
        
        # Upload to S3 (keep original filename)
        s3_key = f"{S3_MUSIC_PREFIX}/{genre}/{audio_file.name}"
        
        try:
            file_size = os.path.getsize(audio_file)
            print(f"   📤 Uploading ({file_size / 1024 / 1024:.2f} MB)...")
            s3_client.upload_file(str(audio_file), bucket, s3_key)
            print(f"   ✅ Uploaded: {s3_key}")
            total_uploaded += 1
        except Exception as e:
            print(f"   ❌ Upload failed: {str(e)}")
            total_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Upload Summary")
    print("=" * 60)
    print(f"✅ Successfully uploaded: {total_uploaded}")
    print(f"❌ Failed: {total_failed}")
    print(f"📁 S3 location: s3://{bucket}/{S3_MUSIC_PREFIX}/")
    print("\n💡 Note: Phase 5 will crop these tracks to match video duration automatically.")
    print("=" * 60)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Upload music tracks to S3 (will be cropped to video duration in Phase 5)'
    )
    parser.add_argument(
        '--music-dir',
        type=str,
        default='./music',
        help='Directory containing music tracks (default: ./music)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎵 Music Track Uploader")
    print("=" * 60)
    print("Uploading tracks to S3 - Phase 5 will crop to match video duration")
    print("=" * 60)
    
    # Get S3 client and bucket
    try:
        s3_client = get_s3_client()
        bucket = get_s3_bucket()
        print(f"✅ S3 configured: {bucket}")
    except Exception as e:
        print(f"\n❌ ERROR: S3 configuration failed!")
        print(f"   Make sure you have AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET in your .env file")
        print(f"   Error: {str(e)}")
        sys.exit(1)
    
    # Upload music
    upload_music_directory(args.music_dir, s3_client, bucket)
    
    print("\n✅ Done!")


if __name__ == "__main__":
    main()

