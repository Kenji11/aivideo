#!/usr/bin/env python3
"""
Migration script to generate thumbnails for existing videos.

Usage:
    python scripts/generate_video_thumbnails.py [--dry-run] [--limit N]
"""

import sys
import os
import tempfile
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from backend directory
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try loading from current directory as fallback
    load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.common.models import VideoGeneration
from app.services.thumbnail import thumbnail_service
from app.services.s3 import s3_client
from app.common.constants import get_video_s3_key
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_thumbnails_for_existing_videos(dry_run: bool = False, limit: int = None):
    """
    Generate thumbnails for all videos that don't have one.
    
    Args:
        dry_run: If True, only show what would be processed without making changes
        limit: If set, only process first N videos (for testing)
    """
    db = SessionLocal()
    
    try:
        # Query all videos
        query = db.query(VideoGeneration).filter(
            VideoGeneration.thumbnail_url.is_(None)  # Only videos without thumbnails
        ).order_by(VideoGeneration.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        videos = query.all()
        total_videos = len(videos)
        
        logger.info(f"Found {total_videos} videos without thumbnails")
        
        if dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            for video in videos:
                chunk_key = get_video_s3_key(video.user_id, video.id, "chunk_00.mp4")
                logger.info(f"Would process: {video.id} - {video.title} (chunk: {chunk_key})")
            logger.info(f"DRY RUN: Would process {total_videos} videos")
            return
        
        # Process each video
        success_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, video in enumerate(videos, 1):
            logger.info(f"Processing {i}/{total_videos}: {video.id} - {video.title}")
            
            try:
                # Check if first chunk exists
                chunk_key = get_video_s3_key(video.user_id, video.id, "chunk_00.mp4")
                
                # Check if chunk exists in S3
                try:
                    s3_client.client.head_object(Bucket=s3_client.bucket, Key=chunk_key)
                    chunk_exists = True
                except s3_client.client.exceptions.ClientError as e:
                    if e.response['Error']['Code'] == '404':
                        chunk_exists = False
                    else:
                        raise
                
                if not chunk_exists:
                    logger.warning(f"  ⚠️  Chunk not found: {chunk_key} - skipping")
                    skipped_count += 1
                    continue
                
                # Download chunk from S3
                first_chunk_path = None
                try:
                    first_chunk_path = s3_client.download_temp(chunk_key)
                    
                    if not os.path.exists(first_chunk_path):
                        logger.warning(f"  ⚠️  Failed to download chunk - skipping")
                        skipped_count += 1
                        continue
                    
                    # Generate thumbnail
                    thumbnail_url = thumbnail_service.generate_video_thumbnail(
                        video_path=first_chunk_path,
                        user_id=video.user_id or 'system',
                        video_id=video.id
                    )
                    
                    # Update database
                    video.thumbnail_url = thumbnail_url
                    db.commit()
                    
                    logger.info(f"  ✅ Generated thumbnail: {thumbnail_url}")
                    success_count += 1
                    
                    # Cleanup
                    if first_chunk_path and os.path.exists(first_chunk_path):
                        try:
                            os.remove(first_chunk_path)
                        except Exception:
                            pass
                    
                except Exception as e:
                    logger.error(f"  ❌ Error processing video {video.id}: {str(e)}", exc_info=True)
                    error_count += 1
                    db.rollback()
                    
                    # Cleanup on error
                    if first_chunk_path and os.path.exists(first_chunk_path):
                        try:
                            os.remove(first_chunk_path)
                        except Exception:
                            pass
                    
            except Exception as e:
                logger.error(f"  ❌ Unexpected error for video {video.id}: {str(e)}", exc_info=True)
                error_count += 1
                db.rollback()
        
        # Summary
        logger.info("=" * 60)
        logger.info("Migration Summary:")
        logger.info(f"  Total videos processed: {total_videos}")
        logger.info(f"  ✅ Successfully generated: {success_count}")
        logger.info(f"  ⚠️  Skipped (no chunk): {skipped_count}")
        logger.info(f"  ❌ Errors: {error_count}")
        logger.info("=" * 60)
        
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate thumbnails for existing videos")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be processed without making changes")
    parser.add_argument("--limit", type=int, help="Process only first N videos (for testing)")
    
    args = parser.parse_args()
    
    generate_thumbnails_for_existing_videos(dry_run=args.dry_run, limit=args.limit)

