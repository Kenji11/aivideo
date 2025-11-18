# Phase 5: Refinement Task
import time
from datetime import datetime, timezone
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase5_refine.service import RefinementService
from app.common.exceptions import PhaseException
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from sqlalchemy.orm.attributes import flag_modified


@celery_app.task(bind=True, name="app.phases.phase5_refine.task.refine_video")
def refine_video(self, phase4_output: dict, user_id: str = None) -> dict:
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
        self: Celery task instance
        phase4_output: PhaseOutput dict from Phase 4 (contains stitched_video_url)
        user_id: User ID for organizing outputs in S3 (required for new structure)
        
    Returns:
        PhaseOutput dictionary with status, output_data (refined_video_url, music_url), cost, etc.
    """
    start_time = time.time()
    
    # Check if Phase 4 succeeded
    if phase4_output.get('status') != 'success':
        error_msg = phase4_output.get('error_message', 'Phase 4 failed')
        video_id = phase4_output.get('video_id', 'unknown')
        
        # Update progress
        update_progress(video_id, "failed", 0, error_message=f"Phase 4 failed: {error_msg}", current_phase="phase5_refine")
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase5_refine",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=0.0,
            error_message=f"Phase 4 failed: {error_msg}"
        ).dict()
    
    # Extract data from Phase 4 output
    video_id = phase4_output['video_id']
    phase4_data = phase4_output['output_data']
    stitched_video_url = phase4_data.get('stitched_video_url')
    spec = phase4_data.get('spec')  # Spec passed through from Phase 3
    
    if not stitched_video_url:
        # Phase 5 skipped - no stitched video
        update_progress(video_id, "skipped", 100, current_phase="phase5_refine")
        
        # Update final status in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                video.status = VideoStatus.COMPLETE
                video.progress = 100.0
                video.current_phase = "phase4_chunks"
                if video.completed_at is None:
                    video.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase5_refine",
            status="skipped",
            output_data={},
            cost_usd=0.0,
            duration_seconds=0.0,
            error_message=None
        ).dict()
    
    if not spec:
        raise PhaseException("Spec not found in Phase 4 output")
    
    try:
        # Update progress at start
        update_progress(video_id, "refining", 90, current_phase="phase5_refine")
        
        print(f"🎬 Phase 5 (Refinement) starting for video {video_id}...")
        
        service = RefinementService()
        refined_url, music_url = service.refine_all(video_id, stitched_video_url, spec, user_id)
        
        duration_seconds = time.time() - start_time
        
        # Update cost tracking
        update_cost(video_id, "phase5", service.total_cost)
        
        # Update progress
        update_progress(video_id, "refining", 100, current_phase="phase5_refine", total_cost=service.total_cost)
        
        # Calculate total cost from all phases
        db = SessionLocal()
        total_cost = 0.0
        generation_time = 0.0
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                # Calculate total cost from all phase outputs
                for phase_name, phase_output in (video.phase_outputs or {}).items():
                    if isinstance(phase_output, dict) and phase_output.get('status') == 'success':
                        total_cost += phase_output.get('cost_usd', 0.0)
                
                # Get generation time (calculate from start if available, or use current time)
                if video.created_at:
                    generation_time = (datetime.now(timezone.utc) - video.created_at).total_seconds()
                
                # Store Phase 5 output
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                output_dict = {
                    "video_id": video_id,
                    "phase": "phase5_refine",
                    "status": "success",
                    "output_data": {
                        "refined_video_url": refined_url,
                        "music_url": music_url
                    },
                    "cost_usd": service.total_cost,
                    "duration_seconds": duration_seconds,
                    "error_message": None
                }
                video.phase_outputs['phase5_refine'] = output_dict
                video.refined_url = refined_url
                video.final_video_url = refined_url
                if music_url:
                    video.final_music_url = music_url
                video.progress = 100.0
                video.current_phase = "phase5_refine"
                video.status = VideoStatus.COMPLETE
                video.cost_usd = total_cost
                video.generation_time_seconds = generation_time
                if video.completed_at is None:
                    video.completed_at = datetime.now(timezone.utc)
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
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
        print(f"   - Total cost: ${total_cost:.4f}")
        
        return output.dict()
        
    except PhaseException as e:
        duration_seconds = time.time() - start_time
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase5_refine"
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
                    "phase": "phase5_refine",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": str(e)
                }
                video.phase_outputs['phase5_refine'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
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
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase5_refine"
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
                    "phase": "phase5_refine",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": f"An unexpected error occurred: {str(e)}"
                }
                video.phase_outputs['phase5_refine'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
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
