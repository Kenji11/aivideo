# Main orchestration task
import time
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic
from app.phases.phase3_references.task import generate_references
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration


@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: list = None):
    """
    Main orchestration task - chains all 6 phases sequentially.
    Currently implements Phase 1 (Validate) -> Phase 2 (Animatic) -> Phase 3 (References).
    
    Args:
        video_id: Unique video generation ID
        prompt: User's video description
        assets: Optional list of uploaded assets
        
    Returns:
        Result dictionary with video_id, status, spec, and cost
        
    Raises:
        Exception: If any phase fails
    """
    if assets is None:
        assets = []
    
    start_time = time.time()
    total_cost = 0.0
    
    try:
        # ============ PHASE 1: VALIDATE & EXTRACT ============
        update_progress(video_id, "validating", 10, current_phase="phase1_validate")
        
        # Run Phase 1 task synchronously (using apply instead of delay().get())
        result1_obj = validate_prompt.apply(args=[video_id, prompt, assets])
        result1 = result1_obj.result  # Get actual result from EagerResult
        
        # Check Phase 1 success
        if result1['status'] != "success":
            raise Exception(f"Phase 1 failed: {result1.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result1['cost_usd']
        update_cost(video_id, "phase1", result1['cost_usd'])
        
        # Extract spec from Phase 1
        spec = result1['output_data']['spec']
        
        # Update progress with spec
        update_progress(
            video_id,
            "validating",
            20,
            current_phase="phase1_validate",
            spec=spec,
            total_cost=total_cost
        )
        
        # ============ PHASE 2: GENERATE ANIMATIC ============
        update_progress(video_id, "generating_animatic", 25, current_phase="phase2_animatic")
        
        # Run Phase 2 task synchronously
        result2_obj = generate_animatic.apply(args=[video_id, spec])
        result2 = result2_obj.result
        
        # Check Phase 2 success
        if result2['status'] != "success":
            raise Exception(f"Phase 2 failed: {result2.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result2['cost_usd']
        update_cost(video_id, "phase2", result2['cost_usd'])
        
        # ============ PHASE 3: GENERATE REFERENCE ASSETS ============
        update_progress(video_id, "generating_references", 30, current_phase="phase3_references")
        
        # Run Phase 3 task synchronously (using apply instead of delay().get())
        result3_obj = generate_references.apply(args=[video_id, spec])
        result3 = result3_obj.result  # Get actual result from EagerResult
        
        # Check Phase 3 success
        if result3['status'] != "success":
            raise Exception(f"Phase 3 failed: {result3.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result3['cost_usd']
        update_cost(video_id, "phase3", result3['cost_usd'])
        
        # Extract reference URLs from Phase 3
        reference_urls = result3['output_data']
        
        # Store Phase 3 output in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                video.phase_outputs['phase3_references'] = result3
                # Mark JSON column as modified so SQLAlchemy detects the change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Update progress
        update_progress(
            video_id,
            "generating_references",
            40,
            current_phase="phase3_references",
            total_cost=total_cost
        )
        
        # TODO: Phase 4 - Generate Video Chunks (needs animatic_urls from Phase 2)
        # TODO: Phase 5 - Refine & Enhance
        # TODO: Phase 6 - Export & Deliver
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Mark as complete (for now, only Phases 1-3 are done)
        update_progress(
            video_id,
            "complete",
            100,
            current_phase="phase3_references",
            total_cost=total_cost,
            generation_time=generation_time
        )
        
        return {
            "video_id": video_id,
            "status": "success",
            "spec": spec,
            "cost_usd": total_cost,
            "generation_time_seconds": generation_time
        }
        
    except Exception as e:
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            total_cost=total_cost
        )
        raise
