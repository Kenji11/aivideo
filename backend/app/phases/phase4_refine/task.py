# Phase 4: Refinement Task
import time
from datetime import datetime, timezone
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase4_refine.service import RefinementService
from app.common.exceptions import PhaseException
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from sqlalchemy.orm.attributes import flag_modified
from app.database.checkpoint_queries import create_checkpoint, create_artifact, approve_checkpoint


@celery_app.task(bind=True, name="app.phases.phase4_refine.task.refine_video")
def refine_video(self, phase3_output: dict, user_id: str = None) -> dict:
    """
    Phase 4: Music Generation & Audio Integration.
    
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
        phase3_output: PhaseOutput dict from Phase 3 (contains stitched_video_url)
        user_id: User ID for organizing outputs in S3 (required for new structure)
        
    Returns:
        PhaseOutput dictionary with status, output_data (refined_video_url, music_url), cost, etc.
    """
    start_time = time.time()
    
    # Check if Phase 3 succeeded
    if phase3_output.get('status') != 'success':
        error_msg = phase3_output.get('error_message', 'Phase 3 failed')
        video_id = phase3_output.get('video_id', 'unknown')
        
        # Update progress
        update_progress(video_id, "failed", 0, error_message=f"Phase 3 failed: {error_msg}", current_phase="phase4_refine")
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase4_refine",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=0.0,
            error_message=f"Phase 3 failed: {error_msg}"
        ).dict()
    
    # Extract data from Phase 3 output
    video_id = phase3_output['video_id']
    phase3_data = phase3_output['output_data']
    stitched_video_url = phase3_data.get('stitched_video_url')
    spec = phase3_data.get('spec')  # Spec passed through from Phase 2

    # Extract branch context from Phase 3 output (for checkpoint tree)
    branch_name = phase3_output.get('_branch_name', 'main')
    parent_checkpoint_id = phase3_output.get('checkpoint_id')
    version = phase3_output.get('_version', 1)

    print(f"Phase 4 starting with branch context: branch={branch_name}, version={version}, parent_checkpoint={parent_checkpoint_id}")

    if not stitched_video_url:
        # Phase 4 skipped - no stitched video
        # Update final status in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                video.status = VideoStatus.COMPLETE
                video.progress = 100.0
                video.current_phase = "phase3_chunks"
                if video.completed_at is None:
                    video.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
        
        # Update Redis to "complete" status after DB update
        update_progress(video_id, "complete", 100, current_phase="phase3_chunks")
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase4_refine",
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
        update_progress(video_id, "refining", 90, current_phase="phase4_refine")
        
        print(f"🎬 Phase 4 (Refinement) starting for video {video_id}...")
        
        service = RefinementService()
        refined_url, music_url = service.refine_all(video_id, stitched_video_url, spec, user_id)
        
        duration_seconds = time.time() - start_time
        
        # Update cost tracking
        update_cost(video_id, "phase5", service.total_cost)
        
        # Update progress
        update_progress(video_id, "refining", 100, current_phase="phase4_refine", total_cost=service.total_cost)
        
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

                # Build output dictionary
                output_dict = {
                    "video_id": video_id,
                    "phase": "phase4_refine",
                    "status": "success",
                    "output_data": {
                        "refined_video_url": refined_url,
                        "music_url": music_url
                    },
                    "cost_usd": service.total_cost,
                    "duration_seconds": duration_seconds,
                    "error_message": None
                }

                # Create Phase 4 checkpoint (terminal phase - auto-approved)
                print(f"Creating Phase 4 checkpoint for video {video_id} on branch '{branch_name}'")
                checkpoint_id = create_checkpoint(
                    video_id=video_id,
                    branch_name=branch_name,
                    phase_number=4,
                    version=version,
                    phase_output=output_dict,
                    cost_usd=service.total_cost,
                    user_id=user_id,
                    parent_checkpoint_id=parent_checkpoint_id
                )
                print(f"✅ Created checkpoint {checkpoint_id}")

                # Create artifact for final video
                final_s3_key = refined_url.split('.com/')[-1] if '.com/' in refined_url else f"{user_id}/videos/{video_id}/final_v{version}.mp4"
                final_artifact_id = create_artifact(
                    checkpoint_id=checkpoint_id,
                    artifact_type='final_video',
                    artifact_key='final',
                    s3_url=refined_url,
                    s3_key=final_s3_key,
                    version=version,
                    metadata={'with_audio': True}
                )
                print(f"✅ Created final video artifact")

                # Create artifact for music (if present)
                if music_url:
                    music_s3_key = music_url.split('.com/')[-1] if '.com/' in music_url else f"{user_id}/videos/{video_id}/music_v{version}.mp3"
                    music_artifact_id = create_artifact(
                        checkpoint_id=checkpoint_id,
                        artifact_type='music',
                        artifact_key='music',
                        s3_url=music_url,
                        s3_key=music_s3_key,
                        version=version,
                        metadata={'music_style': spec.get('audio', {}).get('music_style', 'cinematic')}
                    )
                    print(f"✅ Created music artifact")

                # Auto-approve Phase 4 checkpoint (terminal phase)
                approve_checkpoint(checkpoint_id)
                print(f"✅ Auto-approved Phase 4 checkpoint (terminal phase)")

                # Add checkpoint_id to output
                output_dict['checkpoint_id'] = checkpoint_id

                # Store Phase 4 output
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                video.phase_outputs['phase4_refine'] = output_dict
                video.refined_url = refined_url
                video.final_video_url = refined_url
                if music_url:
                    video.final_music_url = music_url
                video.progress = 100.0
                video.current_phase = "phase4_refine"
                video.status = VideoStatus.COMPLETE
                video.cost_usd = total_cost
                video.generation_time_seconds = generation_time
                if video.completed_at is None:
                    video.completed_at = datetime.now(timezone.utc)
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Update Redis to "complete" status after DB update
        update_progress(
            video_id, 
            "complete", 
            100, 
            current_phase="phase4_refine",
            total_cost=total_cost,
            generation_time=generation_time,
            final_video_url=refined_url
        )
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_refine",
            status="success",
            output_data={
                "refined_video_url": refined_url,
                "music_url": music_url
            },
            cost_usd=service.total_cost,
            duration_seconds=duration_seconds,
            checkpoint_id=checkpoint_id
        )
        
        print(f"✅ Phase 4 (Refinement) completed successfully for video {video_id}")
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
            current_phase="phase4_refine"
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
                    "phase": "phase4_refine",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": str(e)
                }
                video.phase_outputs['phase4_refine'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_refine",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        print(f"❌ Phase 4 (Refinement) failed for video {video_id}: {str(e)}")
        return output.dict()
        
    except Exception as e:
        duration_seconds = time.time() - start_time
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase4_refine"
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
                    "phase": "phase4_refine",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": f"An unexpected error occurred: {str(e)}"
                }
                video.phase_outputs['phase4_refine'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_refine",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=f"An unexpected error occurred: {str(e)}"
        )
        
        print(f"❌ Phase 4 (Refinement) unexpected error for video {video_id}: {str(e)}")
        return output.dict()
