from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import VideoResponse, VideoListResponse, VideoListItem
from app.common.models import VideoGeneration
from app.common.auth import get_current_user
from app.common.constants import get_video_s3_prefix
from app.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/videos")
async def list_videos(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> VideoListResponse:
    """Get list of videos for the authenticated user"""
    
    # Only return videos owned by the authenticated user, ordered by most recent first
    videos = db.query(VideoGeneration).filter(
        VideoGeneration.user_id == user_id
    ).order_by(VideoGeneration.created_at.desc()).all()
    
    video_items = []
    for video in videos:
        # Get stitched_video_url from phase_outputs if available (Phase 3 output)
        stitched_url = video.stitched_url
        if not stitched_url and video.phase_outputs:
            phase3_output = video.phase_outputs.get('phase3_chunks')
            if phase3_output and phase3_output.get('status') == 'success':
                phase3_data = phase3_output.get('output_data', {})
                stitched_url = phase3_data.get('stitched_video_url')
        
        # Use stitched_url as final_video_url if final_video_url is not set
        final_url = video.final_video_url or stitched_url
        
        # Convert S3 URL to presigned URL if needed
        if final_url and final_url.startswith('s3://'):
            from app.services.s3 import s3_client
            s3_path = final_url.replace(f's3://{s3_client.bucket}/', '')
            final_url = s3_client.generate_presigned_url(s3_path, expiration=3600 * 24 * 7)  # 7 days
        
        # Convert thumbnail S3 URL to presigned URL if needed
        thumbnail_url = video.thumbnail_url
        if thumbnail_url and thumbnail_url.startswith('s3://'):
            from app.services.s3 import s3_client
            s3_path = thumbnail_url.replace(f's3://{s3_client.bucket}/', '')
            thumbnail_url = s3_client.generate_presigned_url(s3_path, expiration=3600 * 24 * 7)  # 7 days
        
        video_items.append(
            VideoListItem(
                video_id=video.id,
                title=video.title,
                status=video.status.value,
                progress=video.progress,
                current_phase=video.current_phase,
                final_video_url=final_url,
                thumbnail_url=thumbnail_url,
                cost_usd=video.cost_usd,
                created_at=video.created_at,
                completed_at=video.completed_at
            )
        )
    
    return VideoListResponse(
        videos=video_items,
        total=len(video_items)
    )

@router.get("/api/video/{video_id}")
async def get_video(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> VideoResponse:
    """Get video details"""
    
    # Only allow access to videos owned by the authenticated user
    video = db.query(VideoGeneration).filter(
        VideoGeneration.id == video_id,
        VideoGeneration.user_id == user_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Convert S3 URL to presigned URL if needed
    final_video_url = video.final_video_url
    if final_video_url and final_video_url.startswith('s3://'):
        from app.services.s3 import s3_client
        s3_path = final_video_url.replace(f's3://{s3_client.bucket}/', '')
        final_video_url = s3_client.generate_presigned_url(s3_path, expiration=3600 * 24 * 7)  # 7 days
    
    # Convert thumbnail S3 URL to presigned URL if needed
    thumbnail_url = video.thumbnail_url
    if thumbnail_url and thumbnail_url.startswith('s3://'):
        from app.services.s3 import s3_client
        s3_path = thumbnail_url.replace(f's3://{s3_client.bucket}/', '')
        thumbnail_url = s3_client.generate_presigned_url(s3_path, expiration=3600 * 24 * 7)  # 7 days
    
    return VideoResponse(
        video_id=video.id,
        title=video.title,
        status=video.status.value,
        final_video_url=final_video_url,
        thumbnail_url=thumbnail_url,
        cost_usd=video.cost_usd,
        generation_time_seconds=video.generation_time_seconds,
        created_at=video.created_at,
        completed_at=video.completed_at,
        spec=video.spec
    )

@router.delete("/api/video/{video_id}")
async def delete_video(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a video and all associated files
    
    Deletion order:
    1. Delete S3 files (all files associated with video)
    2. Delete database entry
    3. Delete cache entries (Redis)
    
    Returns 404 if video not found, 403 if user doesn't own video.
    """
    # Verify video exists and belongs to authenticated user
    video = db.query(VideoGeneration).filter(
        VideoGeneration.id == video_id,
        VideoGeneration.user_id == user_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    logger.info(f"Deleting video {video_id} for user {user_id}")
    
    # Step 1: Delete S3 files
    try:
        from app.services.s3 import s3_client
        s3_prefix = get_video_s3_prefix(user_id, video_id)
        logger.info(f"Deleting S3 files with prefix: {s3_prefix}")
        s3_success = s3_client.delete_directory(s3_prefix)
        if not s3_success:
            logger.warning(f"Some S3 files may not have been deleted for video {video_id}")
        else:
            logger.info(f"Successfully deleted S3 files for video {video_id}")
    except Exception as e:
        logger.error(f"Error deleting S3 files for video {video_id}: {str(e)}")
        # Continue with deletion even if S3 deletion fails
    
    # Step 2: Delete database entry
    try:
        db.delete(video)
        db.commit()
        logger.info(f"Successfully deleted database entry for video {video_id}")
    except Exception as e:
        logger.error(f"Error deleting database entry for video {video_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete video from database")
    
    # Step 3: Delete Redis cache entries
    try:
        from app.services.redis import RedisClient
        redis_client = RedisClient()
        cache_success = redis_client.delete_video_data(video_id)
        if cache_success:
            logger.info(f"Successfully deleted Redis cache entries for video {video_id}")
        else:
            logger.warning(f"Failed to delete Redis cache entries for video {video_id} (may not exist)")
    except Exception as e:
        logger.warning(f"Error deleting Redis cache entries for video {video_id}: {str(e)}")
        # Don't fail entire operation if cache deletion fails (cache will expire)
    
    return {
        "message": "Video deleted successfully",
        "video_id": video_id
    }
