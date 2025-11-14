from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import StatusResponse
from app.common.models import VideoGeneration
from app.database import get_db

router = APIRouter()

@router.get("/api/status/{video_id}")
async def get_status(video_id: str, db: Session = Depends(get_db)) -> StatusResponse:
    """Get video generation status"""
    
    video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Calculate estimated time remaining (rough estimate)
    estimated_time_remaining = None
    if video.status.value not in ["complete", "failed"]:
        # Rough estimate: 10 minutes total, based on progress
        if video.progress > 0:
            estimated_time_remaining = int((100 - video.progress) / video.progress * 600)  # seconds
    
    return StatusResponse(
        video_id=video.id,
        status=video.status.value,
        progress=video.progress,
        current_phase=video.current_phase,
        estimated_time_remaining=estimated_time_remaining,
        error=video.error_message
    )
