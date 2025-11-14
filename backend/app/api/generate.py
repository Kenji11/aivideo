from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import GenerateRequest, GenerateResponse
from app.common.models import VideoGeneration, VideoStatus
from app.database import get_db
from app.orchestrator.pipeline import run_pipeline
import uuid

router = APIRouter()

@router.post("/api/generate")
async def generate_video(request: GenerateRequest, db: Session = Depends(get_db)) -> GenerateResponse:
    """Submit video generation job"""
    
    # Create video record
    video_id = str(uuid.uuid4())
    
    # Create database record
    video_record = VideoGeneration(
        id=video_id,
        title=request.prompt[:100],  # Use first 100 chars as title
        description=request.prompt,
        prompt=request.prompt,
        status=VideoStatus.QUEUED,
        progress=0.0
    )
    
    db.add(video_record)
    db.commit()
    db.refresh(video_record)
    
    # Enqueue job
    try:
        run_pipeline.delay(video_id, request.prompt, request.assets)
    except Exception as e:
        # If enqueue fails, update status
        video_record.status = VideoStatus.FAILED
        video_record.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")
    
    return GenerateResponse(
        video_id=video_id,
        status="queued",
        message="Video generation started"
    )
