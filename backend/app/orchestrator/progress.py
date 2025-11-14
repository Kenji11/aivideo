# Update DB progress/status
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus


def update_progress(
    video_id: str,
    status: str,
    progress: Optional[float] = None,
    **kwargs
) -> None:
    """
    Update video generation progress in database.
    
    Args:
        video_id: Unique identifier for the video
        status: Status string (e.g., "validating", "generating_animatic", "complete", "failed")
        progress: Progress percentage (0-100), optional
        **kwargs: Additional fields to update
            - current_phase: str
            - spec: dict
            - error_message: str
            - animatic_urls: list
            - total_cost: float
            - generation_time: float
    """
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        
        if not video:
            # Create new record if it doesn't exist
            video = VideoGeneration(
                id=video_id,
                title=kwargs.get("title", "Untitled Video"),
                prompt=kwargs.get("prompt", ""),
                status=VideoStatus.QUEUED,
                progress=0.0
            )
            db.add(video)
        
        # Update status
        if status in [s.value for s in VideoStatus]:
            video.status = VideoStatus(status)
        else:
            # Map string status to enum
            status_map = {
                "validating": VideoStatus.VALIDATING,
                "generating_animatic": VideoStatus.GENERATING_ANIMATIC,
                "generating_references": VideoStatus.GENERATING_REFERENCES,
                "generating_chunks": VideoStatus.GENERATING_CHUNKS,
                "refining": VideoStatus.REFINING,
                "exporting": VideoStatus.EXPORTING,
                "complete": VideoStatus.COMPLETE,
                "failed": VideoStatus.FAILED
            }
            video.status = status_map.get(status, VideoStatus.QUEUED)
        
        # Update progress
        if progress is not None:
            video.progress = progress
        
        # Update optional fields from kwargs
        if "current_phase" in kwargs:
            video.current_phase = kwargs["current_phase"]
        if "error" in kwargs or "error_message" in kwargs:
            video.error_message = kwargs.get("error") or kwargs.get("error_message")
        if "spec" in kwargs:
            video.spec = kwargs["spec"]
        if "animatic_urls" in kwargs:
            video.animatic_urls = kwargs["animatic_urls"]
        if "final_url" in kwargs or "final_video_url" in kwargs:
            video.final_video_url = kwargs.get("final_url") or kwargs.get("final_video_url")
        if "total_cost" in kwargs:
            video.cost_usd = kwargs["total_cost"]
        if "generation_time" in kwargs:
            video.generation_time_seconds = kwargs["generation_time"]
        
        # Set completed_at if status is complete
        if status == "complete" and video.completed_at is None:
            video.completed_at = datetime.utcnow()
        
        db.commit()
    finally:
        db.close()


def update_cost(video_id: str, phase: str, cost: float) -> None:
    """
    Update cost breakdown for a specific phase.
    
    Args:
        video_id: Unique identifier for the video
        phase: Phase name (e.g., "phase1", "phase2")
        cost: Cost in USD for this phase
    """
    db = SessionLocal()
    
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        
        if video:
            # Initialize cost_breakdown if None
            if video.cost_breakdown is None:
                video.cost_breakdown = {}
            
            # Update phase cost
            video.cost_breakdown[phase] = cost
            
            # Recalculate total cost
            video.cost_usd = sum(video.cost_breakdown.values())
            
            db.commit()
    
    finally:
        db.close()
