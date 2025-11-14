from typing import Dict
import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase2_animatic.service import AnimaticGenerationService


@celery_app.task(bind=True)
def generate_animatic(self, video_id: str, spec: Dict) -> Dict:
    """
    Generate animatic frames for a video specification.
    
    Args:
        video_id: Unique identifier for the video
        spec: Dictionary containing 'beats' and 'style' keys
        
    Returns:
        Dictionary representation of PhaseOutput with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    try:
        # Initialize service
        service = AnimaticGenerationService()
        
        # Generate frames
        frame_urls = service.generate_frames(video_id, spec)
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create success output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="success",
            output_data={"animatic_urls": frame_urls},
            cost_usd=service.total_cost,
            duration_seconds=duration_seconds,
            error_message=None
        )
        
        return output.dict()
        
    except Exception as e:
        # Calculate duration even on error
        duration_seconds = time.time() - start_time
        
        # Create error output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        return output.dict()
