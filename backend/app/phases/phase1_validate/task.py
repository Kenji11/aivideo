import time
import traceback
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase1_validate.service import PromptValidationService
from app.common.constants import COST_GPT4_TURBO
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration
from sqlalchemy.orm.attributes import flag_modified


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
    
    # Log phase start
    print(f"🚀 Phase 1 (Validation) starting for video {video_id}")
    print(f"   Input:")
    print(f"   - Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"   - Prompt length: {len(prompt)} characters")
    print(f"   - Assets provided: {len(assets)}")
    if assets:
        # Assets can be either list of strings (asset IDs) or list of dicts (with s3_key, asset_id)
        if assets and isinstance(assets[0], dict):
            asset_ids = [asset.get('asset_id', 'unknown') for asset in assets[:5]]
        else:
            asset_ids = assets[:5]
        print(f"   - Asset IDs: {', '.join(str(aid) for aid in asset_ids)}{'...' if len(assets) > 5 else ''}")
    
    try:
        # Update progress at start
        update_progress(video_id, "validating", 10, current_phase="phase1_validate")
        
        # Initialize validation service
        service = PromptValidationService()
        
        # Validate and extract specification
        spec = service.validate_and_extract(prompt, assets)
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Update cost tracking
        update_cost(video_id, "phase1", COST_GPT4_TURBO)
        
        # Update progress with spec
        update_progress(
            video_id,
            "validating",
            20,
            current_phase="phase1_validate",
            spec=spec,
            total_cost=COST_GPT4_TURBO
        )
        
        # Store Phase 1 output in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                # Create output dict for storage
                output_dict = {
                    "video_id": video_id,
                    "phase": "phase1_validate",
                    "status": "success",
                    "output_data": {"spec": spec},
                    "cost_usd": COST_GPT4_TURBO,
                    "duration_seconds": duration_seconds,
                    "error_message": None
                }
                video.phase_outputs['phase1_validate'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Log successful phase completion
        template_name = spec.get('template', 'unknown')
        beats_count = len(spec.get('beats', []))
        duration = spec.get('duration', 'unknown')
        fps = spec.get('fps', 'unknown')
        resolution = spec.get('resolution', 'unknown')
        style_aesthetic = spec.get('style', {}).get('aesthetic', 'unknown')
        
        print(f"✅ Phase 1 (Validation) completed successfully for video {video_id}")
        print(f"   Output:")
        print(f"   - Template: {template_name}")
        print(f"   - Beats: {beats_count}")
        print(f"   - Video duration: {duration}s")
        print(f"   - FPS: {fps}")
        print(f"   - Resolution: {resolution}")
        print(f"   - Style: {style_aesthetic}")
        print(f"   - Cost: ${COST_GPT4_TURBO:.4f}")
        print(f"   - Processing time: {duration_seconds:.2f}s")
        
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
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Log error details
        print(f"❌ Phase 1 (Validation) failed for video {video_id}")
        print(f"   Error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Duration before failure: {duration_seconds:.2f}s")
        print(f"   Traceback:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                print(f"   {line}")
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase1_validate"
        )
        
        # Store failure in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                output_dict = {
                    "video_id": video_id,
                    "phase": "phase1_validate",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": str(e)
                }
                video.phase_outputs['phase1_validate'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
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
