from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import VideoResponse, VideoListResponse, VideoListItem
from app.common.models import VideoGeneration
from app.common.auth import get_current_user
from app.database import get_db

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
        # Get stitched_video_url from phase_outputs if available (Phase 4 output)
        stitched_url = video.stitched_url
        if not stitched_url and video.phase_outputs:
            phase4_output = video.phase_outputs.get('phase4_chunks')
            if phase4_output and phase4_output.get('status') == 'success':
                phase4_data = phase4_output.get('output_data', {})
                stitched_url = phase4_data.get('stitched_video_url')
        
        # Use stitched_url as final_video_url if final_video_url is not set
        final_url = video.final_video_url or stitched_url
        
        # Convert S3 URL to presigned URL if needed
        if final_url and final_url.startswith('s3://'):
            from app.services.s3 import s3_client
            s3_path = final_url.replace(f's3://{s3_client.bucket}/', '')
            final_url = s3_client.generate_presigned_url(s3_path, expiration=3600 * 24 * 7)  # 7 days
        
        video_items.append(
            VideoListItem(
                video_id=video.id,
                title=video.title,
                status=video.status.value,
                progress=video.progress,
                current_phase=video.current_phase,
                final_video_url=final_url,
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
    
    return VideoResponse(
        video_id=video.id,
        status=video.status.value,
        final_video_url=final_video_url,
        cost_usd=video.cost_usd,
        generation_time_seconds=video.generation_time_seconds,
        created_at=video.created_at,
        completed_at=video.completed_at,
        spec=video.spec
    )
