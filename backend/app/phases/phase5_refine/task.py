# Phase 5: Refinement Task
import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase5_refine.service import RefinementService
from app.common.exceptions import PhaseException


@celery_app.task(bind=True, name="app.phases.phase5_refine.task.refine_video")
def refine_video(self, video_id: str, stitched_url: str, spec: dict) -> dict:
    """
    Phase 5: Music Generation & Audio Integration.
    
    Steps:
    - Generate background music using configured model (default: meta/musicgen)
    - Extract audio specs from template (music_style, tempo, mood)
    - Build music prompt from template specs
    - Adjust music to exact video duration using FFmpeg if needed
    - Combine video + music using moviepy (FFmpeg fallback)
    - Set music volume to 70% for balanced audio
    - Upload final video with audio to S3
    
    Args:
        video_id: Unique video generation ID
        stitched_url: S3 URL of stitched video from Phase 4
        spec: Video specification from Phase 1 (contains audio specs)
        
    Returns:
        PhaseOutput dictionary with status, output_data (refined_video_url, music_url), cost, etc.
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
