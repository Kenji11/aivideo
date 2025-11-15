# Main orchestration task
import time
from app.orchestrator.celery_app import celery_app
from app.orchestrator.progress import update_progress, update_cost
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic


@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: list = None):
    """
    Main orchestration task - chains all 6 phases sequentially.
    Currently implements Phase 1 (Validate) -> Phase 2 (Animatic).
    
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
        
        # Run Phase 1 task directly (we're already in a Celery worker, so no need for .delay())
        result1 = validate_prompt(video_id, prompt, assets)
        
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
        
        # Run Phase 2 task directly (we're already in a Celery worker, so no need for .delay())
        result2 = generate_animatic(video_id, spec)
        
        # Check Phase 2 success
        if result2['status'] != "success":
            raise Exception(f"Phase 2 failed: {result2.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result2['cost_usd']
        update_cost(video_id, "phase2", result2['cost_usd'])
        
        # TODO: Phase 3 - Generate Reference Assets
        # TODO: Phase 4 - Generate Video Chunks
        # TODO: Phase 5 - Refine & Enhance
        # TODO: Phase 6 - Export & Deliver
        
        # Calculate generation time
        generation_time = time.time() - start_time
        # Phase 2 complete = 50% progress (2 out of 6 phases, but only 2 implemented so far)
        # Don't set to 100% until all phases are complete
        update_progress(
            video_id,
            "generating_animatic",  # Keep status as generating_animatic, not "complete"
            50,  # Phase 2 complete = 50% (not 100% since we only have 2 phases implemented)
            current_phase="phase2_animatic",
            animatic_urls=result2['output_data']['animatic_urls'],
            total_cost=total_cost,
            generation_time=generation_time
        )
        
        return {
            "video_id": video_id,
            "status": "generating_animatic",  # Not "complete" - only 2 of 6 phases implemented
            "spec": spec,
            "animatic_urls": result2['output_data']['animatic_urls'],
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
