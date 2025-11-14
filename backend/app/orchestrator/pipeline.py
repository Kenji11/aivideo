# Main orchestration task
import time
from app.orchestrator.celery_app import celery_app
from app.orchestrator.progress import update_progress, update_cost
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic
from app.common.constants import PHASE1_TIMEOUT, PHASE2_TIMEOUT


@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: list):
    """
    Main orchestration task - chains all 6 phases sequentially.
    Each person implements their phase tasks independently.
    """
    start_time = time.time()
    total_cost = 0.0
    
    try:
        # Phase 1: Validate Prompt
        update_progress(video_id, "validating", 10)
        result1 = validate_prompt.delay(video_id, prompt, assets).get(timeout=PHASE1_TIMEOUT)
        if result1['status'] != "success":
            raise Exception(f"Phase 1 failed: {result1.get('error_message', 'Unknown error')}")
        total_cost += result1['cost_usd']
        update_cost(video_id, "phase1", result1['cost_usd'])
        
        # Phase 2: Generate Animatic
        update_progress(video_id, "generating_animatic", 25)
        result2 = generate_animatic.delay(video_id, result1['output_data']['spec']).get(timeout=PHASE2_TIMEOUT)
        if result2['status'] != "success":
            raise Exception(f"Phase 2 failed: {result2.get('error_message', 'Unknown error')}")
        total_cost += result2['cost_usd']
        update_cost(video_id, "phase2", result2['cost_usd'])
        
        # TODO: Implement Phase 3-6
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Update final progress with animatic URLs
        update_progress(
            video_id,
            "complete",
            100,
            animatic_urls=result2['output_data']['animatic_urls'],
            total_cost=total_cost,
            generation_time=generation_time
        )
        
        return {
            "video_id": video_id,
            "status": "complete",
            "animatic_urls": result2['output_data']['animatic_urls'],
            "cost_usd": total_cost,
            "generation_time_seconds": generation_time
        }
        
    except Exception as e:
        update_progress(video_id, "failed", None, error_message=str(e))
        raise
