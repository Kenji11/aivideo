# Phase 4: Chunk Generation Task
import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase4_chunks_storyboard.service import ChunkGenerationService
from app.phases.phase4_chunks_storyboard.stitcher import VideoStitcher
from app.common.exceptions import PhaseException
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration
from sqlalchemy.orm.attributes import flag_modified


@celery_app.task(bind=True, name="app.phases.phase4_chunks_storyboard.task.generate_chunks")
def generate_chunks(
    self,
    phase3_output: dict,
    user_id: str = None,
    model: str = 'hailuo'
) -> dict:
    """
    Phase 4: Generate video chunks in parallel and stitch them together.
    
    Args:
        self: Celery task instance
        phase3_output: PhaseOutput dict from Phase 3 (contains spec and reference_urls)
        user_id: User ID for organizing outputs in S3 (required for new structure)
        model: Video generation model to use (default: 'hailuo')
        
    Returns:
        PhaseOutput dictionary with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    # Check if Phase 3 succeeded
    if phase3_output.get('status') != 'success':
        error_msg = phase3_output.get('error_message', 'Phase 3 failed')
        video_id = phase3_output.get('video_id', 'unknown')
        
        # Update progress
        update_progress(video_id, "failed", 0, error_message=f"Phase 3 failed: {error_msg}", current_phase="phase4_chunks")
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks_storyboard",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=0.0,
            error_message=f"Phase 3 failed: {error_msg}"
        ).dict()
    
    # Extract data from Phase 3 output
    # Phase 3 returns reference_urls and spec (passed through from Phase 2)
    video_id = phase3_output.get('video_id', 'unknown')
    phase3_data = phase3_output.get('output_data', {})
    spec = phase3_data.get('spec')
    reference_urls = {
        'style_guide_url': phase3_data.get('style_guide_url'),
        'product_reference_url': phase3_data.get('product_reference_url')
    }
    
    if not spec:
        raise PhaseException("Spec not found in Phase 3 output")
    
    # Add model to spec for chunk generation
    spec['model'] = model
    
    # Set empty animatic_urls (Phase 2 animatic is disabled)
    animatic_urls = []
    
    try:
        # Update progress at start
        update_progress(video_id, "generating_chunks", 50, current_phase="phase4_chunks")
        # Initialize services
        chunk_service = ChunkGenerationService()
        stitcher = VideoStitcher()
        
        # Generate all chunks using storyboard logic
        print(f"🚀 Phase 4 (Chunks - Storyboard Mode) starting for video {video_id}")
        chunk_results = chunk_service.generate_all_chunks(
            video_id=video_id,
            spec=spec,
            animatic_urls=animatic_urls,  # Not used in storyboard mode, but kept for compatibility
            reference_urls=reference_urls,
            user_id=user_id
        )
        
        chunk_urls = chunk_results['chunk_urls']
        total_cost = chunk_results['total_cost']
        
        # Update progress before stitching
        update_progress(
            video_id,
            "generating_chunks",
            70,  # 70% = all chunks done, starting to stitch
            current_phase="phase4_chunks"
        )
        
        # Stitch chunks together with transitions
        print(f"Stitching {len(chunk_urls)} chunks with transitions...")
        transitions = spec.get('transitions', [])
        stitched_video_url = stitcher.stitch_with_transitions(
            video_id=video_id,
            chunk_urls=chunk_urls,
            transitions=transitions,
            user_id=user_id
        )
        
        # Update progress after stitching
        update_progress(
            video_id,
            "generating_chunks",
            75,  # 75% = stitching complete
            current_phase="phase4_chunks"
        )
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create success output
        # Pass through spec for Phase 5 (needs it for music generation)
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks_storyboard",
            status="success",
            output_data={
                'stitched_video_url': stitched_video_url,
                'chunk_urls': chunk_urls,
                'total_cost': total_cost,
                'spec': spec  # Pass through spec for Phase 5
            },
            cost_usd=total_cost,
            duration_seconds=duration_seconds,
            error_message=None
        )
        
        # Update cost tracking
        update_cost(video_id, "phase4", total_cost)
        
        # Update progress
        update_progress(
            video_id,
            "generating_chunks",
            90,
            current_phase="phase4_chunks",
            total_cost=total_cost
        )
        
        # Store Phase 4 output in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                video.phase_outputs['phase4_chunks'] = output.dict()
                video.stitched_url = stitched_video_url
                video.chunk_urls = chunk_urls
                video.final_video_url = stitched_video_url
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        print(f"✅ Phase 4 (Chunks) completed successfully for video {video_id}")
        print(f"   - Generated chunks: {len(chunk_urls)}")
        print(f"   - Stitched video: {stitched_video_url}")
        print(f"   - Total cost: ${total_cost:.4f}")
        print(f"   - Duration: {duration_seconds:.2f}s")
        
        return output.dict()
        
    except PhaseException as e:
        # Phase-specific exception
        duration_seconds = time.time() - start_time
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase4_chunks"
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
                    "phase": "phase4_chunks_storyboard",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": str(e)
                }
                video.phase_outputs['phase4_chunks'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks_storyboard",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        print(f"❌ Phase 4 (Chunks) failed for video {video_id}: {str(e)}")
        return output.dict()
        
    except Exception as e:
        # Unexpected exception
        duration_seconds = time.time() - start_time
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase4_chunks"
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
                    "phase": "phase4_chunks_storyboard",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": f"An unexpected error occurred: {str(e)}"
                }
                video.phase_outputs['phase4_chunks'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks_storyboard",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=f"An unexpected error occurred: {str(e)}"
        )
        
        print(f"❌ Phase 4 (Chunks) unexpected error for video {video_id}: {str(e)}")
        return output.dict()