from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import VideoResponse, VideoListResponse, VideoListItem
from app.common.models import VideoGeneration
from app.database import get_db

router = APIRouter()

@router.get("/api/videos")
async def list_videos(
    db: Session = Depends(get_db)
) -> VideoListResponse:
    """Get list of all videos"""
    
    # Order by most recent first
    videos = db.query(VideoGeneration).order_by(VideoGeneration.created_at.desc()).all()
    
    video_items = [
        VideoListItem(
            video_id=video.id,
            title=video.title,
            status=video.status.value,
            progress=video.progress,
            current_phase=video.current_phase,
            final_video_url=video.final_video_url,
            cost_usd=video.cost_usd,
            created_at=video.created_at,
            completed_at=video.completed_at
        )
        for video in videos
    ]
    
    return VideoListResponse(
        videos=video_items,
        total=len(video_items)
    )

@router.get("/api/video/{video_id}")
async def get_video(video_id: str, db: Session = Depends(get_db)) -> VideoResponse:
    """Get video details"""
    
    video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoResponse(
        video_id=video.id,
        status=video.status.value,
        final_video_url=video.final_video_url,
        cost_usd=video.cost_usd,
        generation_time_seconds=video.generation_time_seconds,
        created_at=video.created_at,
        completed_at=video.completed_at,
        spec=video.spec
    )
