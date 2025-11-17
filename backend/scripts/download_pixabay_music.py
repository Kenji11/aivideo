#!/usr/bin/env python3
"""
Script to download music tracks from Pixabay and upload to S3.

Pixabay provides free music tracks that can be used for personal projects.
This script downloads tracks, organizes them by genre, and stores them in S3.
"""

import os
import sys
import requests
import tempfile
from typing import List, Dict, Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import only what we need, avoiding full app imports
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Pixabay API endpoints
# Note: Pixabay's audio API might not be as straightforward as images/videos
# We'll try the audio endpoint, but may need to use alternative methods
PIXABAY_AUDIO_API = "https://pixabay.com/api/audio/"
PIXABAY_MAIN_API = "https://pixabay.com/api/"

# Music genres/categories to download
MUSIC_GENRES = {
    'upbeat': ['upbeat', 'happy', 'energetic', 'positive'],
    'cinematic': ['cinematic', 'epic', 'dramatic', 'orchestral'],
    'corporate': ['corporate', 'business', 'professional', 'modern'],
    'calm': ['calm', 'peaceful', 'relaxing', 'ambient'],
    'energetic': ['energetic', 'fast', 'intense', 'action'],
    'background': ['background', 'ambient', 'atmospheric'],
    'advertising': ['advertising', 'commercial', 'promotional'],
}

# S3 prefix for music library
S3_MUSIC_PREFIX = "music-library"


def get_pixabay_api_key() -> Optional[str]:
    """Get Pixabay API key from environment."""
    return os.getenv('PIXABAY_API_KEY')


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


def search_pixabay_audio(query: str, api_key: str, per_page: int = 20) -> List[Dict]:
    """
    Search Pixabay for audio tracks.
    
    Note: Pixabay's audio API structure may vary. This function tries multiple approaches.
    
    Args:
        query: Search query (genre/keywords)
        api_key: Pixabay API key
        per_page: Number of results per page (max 200)
        
    Returns:
        List of audio track dictionaries
    """
    # Try audio-specific endpoint first
    endpoints_to_try = [
        (PIXABAY_AUDIO_API, {'key': api_key, 'q': query, 'audio_type': 'music', 'per_page': min(per_page, 200)}),
        (PIXABAY_AUDIO_API, {'key': api_key, 'q': query, 'category': 'music', 'per_page': min(per_page, 200)}),
        (PIXABAY_MAIN_API, {'key': api_key, 'q': query, 'image_type': 'all', 'category': 'music', 'per_page': min(per_page, 200)}),
    ]
    
    for endpoint, params in endpoints_to_try:
        try:
            print(f"   🔍 Searching Pixabay ({endpoint}) for: '{query}'...")
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            hits = data.get('hits', [])
            
            if hits:
                print(f"   ✅ Found {len(hits)} tracks for '{query}'")
                return hits
            else:
                print(f"   ⚠️  No results from {endpoint}, trying next...")
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"   ⚠️  Endpoint {endpoint} not found, trying next...")
                continue
            else:
                print(f"   ⚠️  HTTP error: {str(e)}")
                continue
        except Exception as e:
            print(f"   ⚠️  Error with {endpoint}: {str(e)}")
            continue
    
    print(f"   ❌ Could not find audio tracks for '{query}' via API")
    print(f"   💡 Note: Pixabay's audio API may require manual download from their website")
    return []


def download_audio_track(track_url: str, output_path: str) -> bool:
    """
    Download an audio track from URL.
    
    Args:
        track_url: URL to the audio file
        output_path: Local path to save the file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"      📥 Downloading: {track_url[:80]}...")
        response = requests.get(track_url, timeout=60, stream=True)
        response.raise_for_status()
        
        # Save to file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = os.path.getsize(output_path)
        print(f"      ✅ Downloaded {file_size / 1024:.1f} KB")
        return True
        
    except Exception as e:
        print(f"      ❌ Download failed: {str(e)}")
        return False


def upload_to_s3(local_path: str, s3_key: str, s3_client, bucket: str) -> Optional[str]:
    """
    Upload audio file to S3.
    
    Args:
        local_path: Local file path
        s3_key: S3 key (path) for the file
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        
    Returns:
        S3 URL if successful, None otherwise
    """
    try:
        s3_client.upload_file(local_path, bucket, s3_key)
        s3_url = f"s3://{bucket}/{s3_key}"
        print(f"      ☁️  Uploaded to S3: {s3_key}")
        return s3_url
    except Exception as e:
        print(f"      ❌ S3 upload failed: {str(e)}")
        return None


def download_genre_music(genre: str, keywords: List[str], api_key: str, s3_client, bucket: str, max_tracks: int = 10) -> List[Dict]:
    """
    Download music tracks for a specific genre.
    
    Args:
        genre: Genre name (e.g., 'upbeat')
        keywords: List of search keywords for this genre
        api_key: Pixabay API key
        max_tracks: Maximum number of tracks to download per genre
        
    Returns:
        List of track metadata dictionaries
    """
    print(f"\n🎵 Downloading {genre} music...")
    
    # Search for tracks using all keywords
    all_tracks = []
    seen_track_ids = set()
    
    for keyword in keywords:
        tracks = search_pixabay_audio(keyword, api_key, per_page=20)
        
        for track in tracks:
            track_id = track.get('id')
            if track_id and track_id not in seen_track_ids:
                seen_track_ids.add(track_id)
                all_tracks.append(track)
                
                if len(all_tracks) >= max_tracks:
                    break
        
        if len(all_tracks) >= max_tracks:
            break
    
    # Limit to max_tracks
    all_tracks = all_tracks[:max_tracks]
    
    print(f"   📊 Selected {len(all_tracks)} unique tracks for {genre}")
    
    # Download and upload each track
    downloaded_tracks = []
    temp_dir = tempfile.mkdtemp()
    
    try:
        for i, track in enumerate(all_tracks, 1):
            track_id = track.get('id')
            track_url = track.get('url')  # Full URL to audio file
            
            if not track_url:
                print(f"   ⚠️  Track {i} has no URL, skipping")
                continue
            
            # Get file extension from URL or default to mp3
            file_ext = '.mp3'
            if '.mp3' in track_url.lower():
                file_ext = '.mp3'
            elif '.wav' in track_url.lower():
                file_ext = '.wav'
            elif '.ogg' in track_url.lower():
                file_ext = '.ogg'
            
            # Local temp file
            local_path = os.path.join(temp_dir, f"{genre}_{track_id}{file_ext}")
            
            # Download track
            if not download_audio_track(track_url, local_path):
                continue
            
            # Upload to S3
            s3_key = f"{S3_MUSIC_PREFIX}/{genre}/{track_id}{file_ext}"
            s3_url = upload_to_s3(local_path, s3_key, s3_client, bucket)
            
            if s3_url:
                # Store metadata
                track_metadata = {
                    'id': track_id,
                    'genre': genre,
                    'title': track.get('title', f'{genre}_track_{track_id}'),
                    'tags': track.get('tags', ''),
                    'duration': track.get('duration', 0),
                    's3_key': s3_key,
                    's3_url': s3_url,
                }
                downloaded_tracks.append(track_metadata)
                
                # Clean up local file
                if os.path.exists(local_path):
                    os.remove(local_path)
        
        print(f"   ✅ Successfully downloaded {len(downloaded_tracks)}/{len(all_tracks)} tracks for {genre}")
        
    finally:
        # Clean up temp directory
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except Exception:
                pass
    
    return downloaded_tracks


def main():
    """Main function to download all music genres."""
    print("=" * 60)
    print("🎵 Pixabay Music Downloader")
    print("=" * 60)
    
    # Get API key
    api_key = get_pixabay_api_key()
    if not api_key:
        print("\n❌ ERROR: PIXABAY_API_KEY not found!")
        print("\nTo get a free API key:")
        print("1. Go to https://pixabay.com/api/docs/")
        print("2. Sign up for a free account")
        print("3. Get your API key")
        print("4. Set it as environment variable: export PIXABAY_API_KEY='your-key'")
        print("\nOr add it to your .env file: PIXABAY_API_KEY=your-key")
        sys.exit(1)
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
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
    
    # Download music for each genre
    all_tracks = []
    for genre, keywords in MUSIC_GENRES.items():
        tracks = download_genre_music(genre, keywords, api_key, s3_client, bucket, max_tracks=10)
        all_tracks.extend(tracks)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Download Summary")
    print("=" * 60)
    print(f"Total tracks downloaded: {len(all_tracks)}")
    
    # Group by genre
    by_genre = {}
    for track in all_tracks:
        genre = track['genre']
        if genre not in by_genre:
            by_genre[genre] = []
        by_genre[genre].append(track)
    
    print("\nBy genre:")
    for genre, tracks in by_genre.items():
        print(f"  {genre}: {len(tracks)} tracks")
    
    print(f"\n✅ All tracks stored in S3 under: {S3_MUSIC_PREFIX}/")
    print("=" * 60)


if __name__ == "__main__":
    main()

