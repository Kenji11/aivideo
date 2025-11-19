# Update progress/status with Redis caching and DB fallback
from datetime import datetime
from typing import Optional
import logging
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.common.constants import MOCK_USER_ID
from app.services.redis import RedisClient

logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = RedisClient()


def update_progress(
    video_id: str,
    status: str,
    progress: Optional[float] = None,
    **kwargs
) -> None:
    """
    Update video generation progress in Redis (primary) and DB (fallback/critical updates).
    
    Args:
        video_id: Unique identifier for the video
        status: Status string (e.g., "validating", "generating_animatic", "complete", "failed")
        progress: Progress percentage (0-100), optional
        **kwargs: Additional fields to update
            - current_phase: str
            - spec: dict (stored in Redis only, not DB until final submission)
            - error_message: str
            - animatic_urls: list
            - total_cost: float
            - generation_time: float
            - phase_outputs: dict (nested JSON structure)
    """
    redis_write_failed = False
    
    # Try Redis first (if available)
    if redis_client._client:
        try:
            # Set basic fields
            if progress is not None:
                redis_client.set_video_progress(video_id, progress)
            redis_client.set_video_status(video_id, status)
            
            if "current_phase" in kwargs:
                redis_client.set_video_phase(video_id, kwargs["current_phase"])
            
            # Build metadata dict
            metadata = {}
            if "title" in kwargs:
                metadata["title"] = kwargs["title"]
            if "prompt" in kwargs:
                metadata["prompt"] = kwargs["prompt"]
            if "description" in kwargs:
                metadata["description"] = kwargs["description"]
            if "total_cost" in kwargs:
                metadata["total_cost"] = kwargs["total_cost"]
            if "generation_time" in kwargs:
                metadata["generation_time"] = kwargs["generation_time"]
            if metadata:
                redis_client.set_video_metadata(video_id, metadata)
            
            # Set error message
            if "error" in kwargs or "error_message" in kwargs:
                error_msg = kwargs.get("error") or kwargs.get("error_message")
                if error_msg:
                    redis_client._client.set(
                        redis_client._key(video_id, "error_message"),
                        error_msg,
                        ex=3600
                    )
            
            # Set spec (Redis only, not DB until final submission)
            if "spec" in kwargs:
                redis_client.set_video_spec(video_id, kwargs["spec"])
            
            # Set phase outputs (nested JSON structure)
            if "phase_outputs" in kwargs:
                redis_client.set_video_phase_outputs(video_id, kwargs["phase_outputs"])
            elif "current_chunk_index" in kwargs:
                # Handle Phase 4 chunk progress tracking
                # Get existing phase_outputs from Redis or create new
                existing_data = redis_client.get_video_data(video_id)
                phase_outputs = existing_data.get("phase_outputs", {}) if existing_data else {}
                
                if "phase4_chunks" not in phase_outputs:
                    phase_outputs["phase4_chunks"] = {}
                phase_outputs["phase4_chunks"]["current_chunk_index"] = kwargs["current_chunk_index"]
                if "total_chunks" in kwargs:
                    phase_outputs["phase4_chunks"]["total_chunks"] = kwargs["total_chunks"]
                
                redis_client.set_video_phase_outputs(video_id, phase_outputs)
            
        except Exception as e:
            logger.warning(f"Redis update failed, falling back to DB: {e}")
            redis_write_failed = True
    
    # Fallback to DB (always write if Redis failed or unavailable, or for critical updates)
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        
        # Check if this is initial creation (video doesn't exist)
        is_initial_creation = not video
        
        if is_initial_creation:
            # Create new record if it doesn't exist
            video = VideoGeneration(
                id=video_id,
                user_id=MOCK_USER_ID,  # TODO: Get from auth token in future
                title=kwargs.get("title", "Untitled Video"),
                prompt=kwargs.get("prompt", ""),
                status=VideoStatus.QUEUED,
                progress=0.0
            )
            db.add(video)
        
        # Always write to DB if status is "complete" or "failed" (final states)
        # Or if Redis failed/unavailable
        should_write_to_db = (
            not redis_client._client or 
            redis_write_failed or 
            is_initial_creation or
            status in ["complete", "failed"]
        )
        
        if should_write_to_db:
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
            # Note: spec is NOT written to DB here (only on final submission)
            if "animatic_urls" in kwargs:
                video.animatic_urls = kwargs["animatic_urls"]
            if "final_url" in kwargs or "final_video_url" in kwargs:
                video.final_video_url = kwargs.get("final_url") or kwargs.get("final_video_url")
            if "total_cost" in kwargs:
                video.cost_usd = kwargs["total_cost"]
            if "generation_time" in kwargs:
                video.generation_time_seconds = kwargs["generation_time"]
            
            # Handle phase_outputs
            if "phase_outputs" in kwargs:
                video.phase_outputs = kwargs["phase_outputs"]
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
            elif "current_chunk_index" in kwargs:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                if "phase4_chunks" not in video.phase_outputs:
                    video.phase_outputs["phase4_chunks"] = {}
                video.phase_outputs["phase4_chunks"]["current_chunk_index"] = kwargs["current_chunk_index"]
                video.phase_outputs["phase4_chunks"]["total_chunks"] = kwargs.get("total_chunks")
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
            
            # Set completed_at if status is complete
            if status == "complete" and video.completed_at is None:
                video.completed_at = datetime.utcnow()
            
            db.commit()
    finally:
        db.close()


def update_cost(video_id: str, phase: str, cost: float) -> None:
    """
    Update cost breakdown for a specific phase.
    Stores cost in Redis metadata and updates DB cost_breakdown (for final persistence).
    
    Args:
        video_id: Unique identifier for the video
        phase: Phase name (e.g., "phase1", "phase2")
        cost: Cost in USD for this phase
    """
    # Update Redis metadata with cost
    if redis_client._client:
        try:
            existing_data = redis_client.get_video_data(video_id)
            metadata = existing_data.get("metadata", {}) if existing_data else {}
            metadata["total_cost"] = metadata.get("total_cost", 0) + cost
            redis_client.set_video_metadata(video_id, metadata)
        except Exception as e:
            logger.warning(f"Failed to update cost in Redis: {e}")
    
    # Update DB cost_breakdown (for final persistence)
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
            
            # Log cost update to terminal
            print(f"   💰 {phase.upper()} cost updated: ${cost:.4f} | Running total: ${video.cost_usd:.4f}")
    
    finally:
        db.close()
