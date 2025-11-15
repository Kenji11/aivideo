import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase1_validate.service import PromptValidationService
from app.common.constants import COST_GPT4_TURBO


@celery_app.task(bind=True)
def validate_prompt(self, video_id: str, prompt: str, assets: list = None):
    """
    Phase 1: Validate and extract video specification from user prompt.
    
    Args:
        video_id: Unique video generation ID
        prompt: User's video description
        assets: Optional list of uploaded assets
        
    Returns:
        PhaseOutput dict with spec or error
    """
    start_time = time.time()
    
    if assets is None:
        assets = []
    
    try:
        # Initialize validation service
        service = PromptValidationService()
        
        # Validate and extract specification
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
        
        # Log successful phase completion
        template_name = spec.get('template', 'unknown')
        beats_count = len(spec.get('beats', []))
        print(f"✅ Phase 1 (Validation) completed successfully for video {video_id}")
        print(f"   - Template: {template_name}")
        print(f"   - Beats: {beats_count}")
        print(f"   - Cost: ${COST_GPT4_TURBO:.4f}")
        print(f"   - Duration: {duration_seconds:.2f}s")
        
        return output.dict()
        
    except Exception as e:
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create failure output
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
