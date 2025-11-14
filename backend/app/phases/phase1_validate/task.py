from typing import Dict, List
import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.common.constants import COST_GPT4_TURBO
from app.phases.phase1_validate.service import PromptValidationService


@celery_app.task(bind=True)
def validate_prompt(self, video_id: str, prompt: str, assets: List[str]) -> Dict:
    """
    Phase 1: Validate prompt and extract structured specification.
    
    Args:
        video_id: Unique identifier for the video
        prompt: User's natural language prompt
        assets: List of asset IDs to use as references
        
    Returns:
        Dictionary representation of PhaseOutput with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    try:
        # Initialize service
        service = PromptValidationService()
        
        # Validate and extract spec
        spec = service.validate_and_extract(prompt, assets)
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create success output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase1_validate",
            status="success",
            output_data={"spec": spec},
            cost_usd=COST_GPT4_TURBO,
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
            phase="phase1_validate",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        return output.dict()
