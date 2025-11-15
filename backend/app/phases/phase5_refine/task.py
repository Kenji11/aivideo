# Phase 5: Refinement Task
import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase5_refine.service import RefinementService
from app.common.exceptions import PhaseException


@celery_app.task(bind=True, name="app.phases.phase5_refine.task.refine_video")
def refine_video(self, video_id: str, stitched_url: str, spec: dict) -> dict:
    """
    Phase 5: Refine and polish video.
    
    Steps:
    - Upscale to 1080p
    - Color grading (optional)
    - Generate background music
    - Mix audio
    - Final encode
    
    Args:
        video_id: Unique video generation ID
        stitched_url: S3 URL of stitched video from Phase 4
        spec: Video specification from Phase 1
        
    Returns:
        PhaseOutput dictionary with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    try:
        print(f"🎬 Phase 5 (Refinement) starting for video {video_id}...")
        
        service = RefinementService()
        refined_url, music_url = service.refine_all(video_id, stitched_url, spec)
        
        duration_seconds = time.time() - start_time
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase5_refine",
            status="success",
            output_data={
                "refined_video_url": refined_url,
                "music_url": music_url
            },
            cost_usd=service.total_cost,
            duration_seconds=duration_seconds
        )
        
        print(f"✅ Phase 5 (Refinement) completed successfully for video {video_id}")
        print(f"   - Duration: {duration_seconds:.2f}s")
        print(f"   - Cost: ${service.total_cost:.4f}")
        
        return output.dict()
        
    except PhaseException as e:
        duration_seconds = time.time() - start_time
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase5_refine",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        print(f"❌ Phase 5 (Refinement) failed for video {video_id}: {str(e)}")
        return output.dict()
        
    except Exception as e:
        duration_seconds = time.time() - start_time
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase5_refine",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=f"An unexpected error occurred: {str(e)}"
        )
        
        print(f"❌ Phase 5 (Refinement) unexpected error for video {video_id}: {str(e)}")
        return output.dict()
