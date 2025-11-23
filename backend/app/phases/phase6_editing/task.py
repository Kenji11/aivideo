"""
Celery task wrapper for Phase 6 editing operations.
"""
import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.common.exceptions import PhaseException
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration
from sqlalchemy.orm.attributes import flag_modified
from app.phases.phase6_editing.service import EditingService
from app.phases.phase6_editing.schemas import EditingRequest, EditingResponse
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.phases.phase6_editing.task.edit_chunks")
def edit_chunks(
    self,
    editing_request: dict
) -> dict:
    """
    Phase 6: Edit video chunks (replace, reorder, delete, split).
    
    Args:
        self: Celery task instance
        editing_request: EditingRequest dictionary with video_id and actions
        
    Returns:
        PhaseOutput dictionary with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    try:
        # Parse editing request
        video_id = editing_request.get('video_id')
        actions = editing_request.get('actions', [])
        estimate_cost_only = editing_request.get('estimate_cost_only', False)
        
        # Log received actions for debugging
        logger.info(f"Received editing request for video {video_id}")
        logger.info(f"Actions received: {actions}")
        for i, action in enumerate(actions):
            logger.info(f"  Action {i}: {action}")
            if isinstance(action, dict) and action.get('action_type') == 'split':
                logger.info(f"    Split action - split_time: {action.get('split_time')}, split_frame: {action.get('split_frame')}, split_percentage: {action.get('split_percentage')}")
        
        if not video_id:
            raise PhaseException("video_id is required")
        
        # Update progress at start
        update_progress(video_id, "editing", 0, current_phase="phase6_editing")
        
        # Initialize editing service
        db = SessionLocal()
        try:
            editing_service = EditingService(db)
            
            # If only estimating cost, return estimate
            if estimate_cost_only:
                # Extract model from first replace action
                model = 'hailuo_fast'
                chunk_indices = []
                for action in actions:
                    if action.get('action_type') == 'replace':
                        chunk_indices = action.get('chunk_indices', [])
                        model = action.get('new_model', 'hailuo_fast')
                        break
                
                if chunk_indices:
                    cost_estimate = editing_service.estimate_regeneration_cost(
                        video_id, chunk_indices, model
                    )
                    return {
                        'status': 'success',
                        'estimated_cost': cost_estimate.estimated_cost,
                        'estimated_time_seconds': cost_estimate.estimated_time_seconds,
                        'cost_per_chunk': cost_estimate.cost_per_chunk,
                    }
                else:
                    return {
                        'status': 'success',
                        'estimated_cost': 0.0,
                        'estimated_time_seconds': 0.0,
                        'cost_per_chunk': {},
                    }
            
            # Process edits
            try:
                result = editing_service.process_edits(video_id, actions)
            except Exception as e:
                logger.error(f"Error processing edits for video {video_id}: {e}", exc_info=True)
                # Update progress with failure
                update_progress(
                    video_id,
                    "failed",
                    0,
                    error_message=str(e),
                    current_phase="phase6_editing"
                )
                # Update phase_outputs with failure
                video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                if video:
                    if not video.phase_outputs:
                        video.phase_outputs = {}
                    video.phase_outputs['phase6_editing'] = {
                        'status': 'failed',
                        'error_message': str(e),
                    }
                    flag_modified(video, 'phase_outputs')
                    db.commit()
                raise
            
            # Calculate duration
            duration_seconds = time.time() - start_time
            
            # Update video record
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                video.chunk_urls = result['updated_chunk_urls']
                video.stitched_url = result['updated_stitched_url']
                video.final_video_url = result['updated_stitched_url']
                
                # Update phase_outputs
                if not video.phase_outputs:
                    video.phase_outputs = {}
                video.phase_outputs['phase6_editing'] = {
                    'status': 'success',
                    'updated_chunk_urls': result['updated_chunk_urls'],
                    'updated_stitched_url': result['updated_stitched_url'],
                    'total_cost': result['total_cost'],
                }
                
                # Update cost
                video.cost_usd += result['total_cost']
                if not video.cost_breakdown:
                    video.cost_breakdown = {}
                video.cost_breakdown['phase6_editing'] = result['total_cost']
                
                flag_modified(video, 'phase_outputs')
                flag_modified(video, 'chunk_urls')
                db.commit()
                
                # Update Redis cache with updated phase_outputs (for real-time status updates)
                try:
                    from app.services.redis import RedisClient
                    redis_client = RedisClient()
                    if redis_client._client:
                        redis_client.set_video_phase_outputs(video_id, video.phase_outputs)
                        logger.debug(f"Updated Redis cache with phase_outputs for video {video_id}")
                except Exception as e:
                    logger.warning(f"Failed to update Redis cache for video {video_id}: {e}")
                    # Non-critical, continue execution
            
            # Update cost tracking
            update_cost(video_id, "phase6", result['total_cost'])
            
            # Update progress (this also updates Redis)
            update_progress(
                video_id,
                "editing",
                100,
                current_phase="phase6_editing",
                total_cost=result['total_cost'],
                phase_outputs=video.phase_outputs if video else None
            )
            
            # Create success output
            output = PhaseOutput(
                video_id=video_id,
                phase="phase6_editing",
                status="success",
                output_data={
                    'updated_chunk_urls': result['updated_chunk_urls'],
                    'updated_stitched_url': result['updated_stitched_url'],
                    'total_cost': result['total_cost'],
                },
                cost_usd=result['total_cost'],
                duration_seconds=duration_seconds,
                error_message=None
            )
            
            logger.info(f"✅ Phase 6 (Editing) completed successfully for video {video_id}")
            logger.info(f"   - Updated chunks: {len(result['updated_chunk_urls'])}")
            logger.info(f"   - Total cost: ${result['total_cost']:.4f}")
            logger.info(f"   - Duration: {duration_seconds:.2f}s")
            
            return output.dict()
            
        finally:
            db.close()
            
    except PhaseException as e:
        error_msg = str(e)
        logger.error(f"❌ Phase 6 (Editing) failed for video {video_id}: {error_msg}")
        
        # Update progress
        update_progress(
            video_id,
            "failed",
            0,
            error_message=error_msg,
            current_phase="phase6_editing"
        )
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase6_editing",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=error_msg
        ).dict()
        
    except Exception as e:
        error_msg = f"Unexpected error in Phase 6: {str(e)}"
        logger.error(f"❌ Phase 6 (Editing) failed for video {video_id}: {error_msg}")
        
        # Update progress
        update_progress(
            video_id,
            "failed",
            0,
            error_message=error_msg,
            current_phase="phase6_editing"
        )
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase6_editing",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=error_msg
        ).dict()

