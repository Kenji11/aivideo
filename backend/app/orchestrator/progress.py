from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus


def update_progress(
    video_id: str,
    status: str,
    progress: float,
    **kwargs
) -> None:
    """
    Update video generation progress in database.
    
    Args:
        video_id: Video generation ID
        status: Current status (from VideoStatus enum)
        progress: Progress percentage (0-100)
        **kwargs: Additional fields to update
            - current_phase: str
            - spec: dict
            - error_message: str
            - total_cost: float
            - generation_time: float
    """
    db = SessionLocal()
    
    try:
        # Query for existing video
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        
        if not video:
            # Create new record if doesn't exist
            video = VideoGeneration(
                id=video_id,
                title="Untitled",
                prompt="",
                status=status,
                progress=progress
            )
            db.add(video)
        else:
            # Update existing record
            video.status = status
            video.progress = progress
        
        # Update optional fields
        if 'current_phase' in kwargs:
            video.current_phase = kwargs['current_phase']
        
        if 'spec' in kwargs:
            video.spec = kwargs['spec']
        
        if 'error_message' in kwargs:
            video.error_message = kwargs['error_message']
        
        if 'total_cost' in kwargs:
            video.cost_usd = kwargs['total_cost']
        
        if 'generation_time' in kwargs:
            video.generation_time_seconds = kwargs['generation_time']
        
        # Set completion time if status is complete
        if status == VideoStatus.COMPLETE.value:
            video.completed_at = datetime.utcnow()
        
        db.commit()
        
    finally:
        db.close()


def update_cost(video_id: str, phase: str, cost: float) -> None:
    """
    Update cost breakdown for a specific phase.
    
    Args:
        video_id: Video generation ID
        phase: Phase name (e.g., 'phase1_validate')
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
