# Phase 4: Chunk Generation Task
import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase4_chunks.service import ChunkGenerationService
from app.phases.phase4_chunks.stitcher import VideoStitcher
from app.common.exceptions import PhaseException


@celery_app.task(bind=True, name="app.phases.phase4_chunks.task.generate_chunks")
def generate_chunks(
    self,
    video_id: str,
    spec: dict,
    animatic_urls: list,
    reference_urls: dict,
    user_id: str = None
) -> dict:
    """
    Phase 4: Generate video chunks in parallel and stitch them together.
    
    Args:
        self: Celery task instance
        video_id: Unique video generation ID
        spec: Video specification from Phase 1
        animatic_urls: List of animatic frame S3 URLs from Phase 2
        reference_urls: Dictionary with style_guide_url and product_reference_url from Phase 3
        user_id: User ID for organizing outputs in S3 (required for new structure)
        
    Returns:
        PhaseOutput dictionary with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    try:
        # Initialize services
        chunk_service = ChunkGenerationService()
        stitcher = VideoStitcher()
        
        # Generate all chunks in parallel
        print(f"🚀 Phase 4 (Chunks) starting for video {video_id}")
        chunk_results = chunk_service.generate_all_chunks(
            video_id=video_id,
            spec=spec,
            animatic_urls=animatic_urls,
            reference_urls=reference_urls,
            user_id=user_id
        )
        
        chunk_urls = chunk_results['chunk_urls']
        total_cost = chunk_results['total_cost']
        
        # Update progress before stitching
        from app.orchestrator.progress import update_progress
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
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks",
            status="success",
            output_data={
                'stitched_video_url': stitched_video_url,
                'chunk_urls': chunk_urls,
                'total_cost': total_cost
            },
            cost_usd=total_cost,
            duration_seconds=duration_seconds,
            error_message=None
        )
        
        print(f"✅ Phase 4 (Chunks) completed successfully for video {video_id}")
        print(f"   - Generated chunks: {len(chunk_urls)}")
        print(f"   - Stitched video: {stitched_video_url}")
        print(f"   - Total cost: ${total_cost:.4f}")
        print(f"   - Duration: {duration_seconds:.2f}s")
        
        return output.dict()
        
    except PhaseException as e:
        # Phase-specific exception
        duration_seconds = time.time() - start_time
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks",
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
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase4_chunks",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=f"An unexpected error occurred: {str(e)}"
        )
        
        print(f"❌ Phase 4 (Chunks) unexpected error for video {video_id}: {str(e)}")
        return output.dict()