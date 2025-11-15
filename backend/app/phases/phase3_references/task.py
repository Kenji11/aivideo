import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase3_references.service import ReferenceAssetService
from app.common.constants import COST_SDXL_IMAGE


@celery_app.task(bind=True)
def generate_references(self, video_id: str, spec: dict):
    """
    Phase 3: Generate reference assets (style guide, product references).
    
    Args:
        video_id: Unique video generation ID
        spec: Video specification from Phase 1
        
    Returns:
        PhaseOutput dict with reference URLs or error
    """
    start_time = time.time()
    
    try:
        # Initialize reference service
        service = ReferenceAssetService()
        
        # Generate all references
        references = service.generate_all_references(video_id, spec)
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create success output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase3_references",
            status="success",
            output_data=references,
            cost_usd=service.total_cost,
            duration_seconds=duration_seconds,
            error_message=None
        )
        
        return output.dict()
        
    except Exception as e:
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create failure output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase3_references",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        return output.dict()
