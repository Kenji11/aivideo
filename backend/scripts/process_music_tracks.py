#!/usr/bin/env python3
"""
Script to process music tracks: extract random 30-second segments and upload to S3.

This script:
1. Finds all audio files in the music directory
2. Extracts a random 30-second segment from each (avoiding watermarks if possible)
3. Organizes them by genre (or puts in 'general' folder)
4. Uploads to S3 under music-library/
"""

import os
import sys
import random
import tempfile
import subprocess
from pathlib import Path
from typing import Optional

# Import only what we need
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# S3 prefix for music library
S3_MUSIC_PREFIX = "music-library"
SEGMENT_DURATION = 30  # 30 seconds


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


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds using ffprobe."""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        duration = float(result.stdout.strip())
        return duration
    except Exception as e:
        print(f"   ⚠️  Could not get duration: {str(e)}, assuming 120 seconds")
        return 120.0  # Default fallback


def extract_random_segment(input_path: str, output_path: str, duration: float = SEGMENT_DURATION) -> bool:
    """
    Extract a random 30-second segment from an audio file.
    
    Args:
        input_path: Path to input audio file
        output_path: Path to save extracted segment
        duration: Duration of segment to extract (default 30 seconds)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get total duration
        total_duration = get_audio_duration(input_path)
        
        if total_duration <= duration:
            print(f"   ⚠️  Track is shorter than {duration}s ({total_duration:.1f}s), using full track")
            # Just copy the file
            subprocess.run(['cp', input_path, output_path], check=True)
            return True
        
        # Calculate random start time (avoid first 5 seconds and last 5 seconds to skip intro/outro)
        # Also avoid very end where watermarks might be
        safe_start = 5.0
        safe_end = total_duration - duration - 5.0
        
        if safe_end <= safe_start:
            # Track is too short, use from start
            start_time = 0.0
        else:
            # Random start time in safe range
            start_time = random.uniform(safe_start, safe_end)
        
        print(f"   ✂️  Extracting {duration}s segment starting at {start_time:.1f}s (total: {total_duration:.1f}s)")
        
        # Use ffmpeg to extract segment
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            '-i', input_path,
            '-ss', str(start_time),  # Start time
            '-t', str(duration),  # Duration
            '-acodec', 'copy',  # Copy audio codec (faster, no re-encoding)
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"   ⚠️  FFmpeg copy failed, trying with re-encoding...")
            # Fallback: re-encode if copy fails
            cmd = [
                'ffmpeg',
                '-y',
                '-i', input_path,
                '-ss', str(start_time),
                '-t', str(duration),
                '-acodec', 'libmp3lame',  # Re-encode to MP3
                '-b:a', '192k',  # Bitrate
                output_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            file_size = os.path.getsize(output_path)
            print(f"   ✅ Extracted segment: {file_size / 1024:.1f} KB")
            return True
        else:
            print(f"   ❌ FFmpeg failed: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error extracting segment: {str(e)}")
        return False


def detect_genre(filename: str) -> str:
    """
    Try to detect genre from filename.
    
    Musicbed tracks often have descriptive names that hint at genre.
    """
    filename_lower = filename.lower()
    
    # Genre detection based on keywords
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
        # Default to 'upbeat' for Musicbed tracks (they're usually energetic)
        return 'upbeat'


def process_music_directory(music_dir: str, s3_client, bucket: str):
    """Process all music files in directory."""
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
    
    temp_dir = tempfile.mkdtemp()
    total_processed = 0
    total_failed = 0
    
    try:
        for i, audio_file in enumerate(audio_files, 1):
            print(f"\n🎵 Processing {i}/{len(audio_files)}: {audio_file.name}")
            
            # Detect genre
            genre = detect_genre(audio_file.name)
            print(f"   🎼 Detected genre: {genre}")
            
            # Extract random 30-second segment
            segment_path = os.path.join(temp_dir, f"{audio_file.stem}_30s.mp3")
            
            if not extract_random_segment(str(audio_file), segment_path, SEGMENT_DURATION):
                print(f"   ❌ Failed to extract segment")
                total_failed += 1
                continue
            
            # Upload to S3
            s3_key = f"{S3_MUSIC_PREFIX}/{genre}/{audio_file.stem}_30s.mp3"
            
            try:
                file_size = os.path.getsize(segment_path)
                print(f"   📤 Uploading to S3 ({file_size / 1024:.1f} KB)...")
                s3_client.upload_file(segment_path, bucket, s3_key)
                print(f"   ✅ Uploaded: {s3_key}")
                total_processed += 1
            except Exception as e:
                print(f"   ❌ S3 upload failed: {str(e)}")
                total_failed += 1
            
            # Clean up segment file
            if os.path.exists(segment_path):
                os.remove(segment_path)
    
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Processing Summary")
    print("=" * 60)
    print(f"✅ Successfully processed: {total_processed}")
    print(f"❌ Failed: {total_failed}")
    print(f"📁 S3 location: s3://{bucket}/{S3_MUSIC_PREFIX}/")
    print("=" * 60)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Process music tracks: extract 30-second segments and upload to S3'
    )
    parser.add_argument(
        '--music-dir',
        type=str,
        default='./music',
        help='Directory containing music tracks (default: ./music)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎵 Music Track Processor")
    print("=" * 60)
    print(f"Extracting random {SEGMENT_DURATION}-second segments from tracks")
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
    
    # Process music
    process_music_directory(args.music_dir, s3_client, bucket)
    
    print("\n✅ Done! Your 30-second music segments are now in S3.")
    print("\n💡 Note: Watermarks in original tracks will still be present in segments.")
    print("   For watermark-free music, use free sources like YouTube Audio Library.")


if __name__ == "__main__":
    main()

