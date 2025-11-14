import time
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import validate_prompt
from app.orchestrator.progress import update_progress, update_cost


@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: list = None):
    """
    Main orchestration task - chains all 6 phases sequentially.
    Currently implements Phase 1 only.
    
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
        
        # Run Phase 1 task
        result1 = validate_prompt.delay(video_id, prompt, assets).get(timeout=60)
        
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
        
        # TODO: Phase 2 - Generate Animatic
        # TODO: Phase 3 - Generate Reference Assets
        # TODO: Phase 4 - Generate Video Chunks
        # TODO: Phase 5 - Refine & Enhance
        # TODO: Phase 6 - Export & Deliver
        
        # Mark as complete (for now, only Phase 1 is done)
        generation_time = time.time() - start_time
        update_progress(
            video_id,
            "complete",
            100,
            current_phase="phase1_validate",
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
