# Main orchestration task
import time
import logging
from celery import chain
from celery.exceptions import Retry
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import plan_video_intelligent
from app.phases.phase2_storyboard.task import generate_storyboard
from app.phases.phase3_chunks.task import generate_chunks
from app.phases.phase4_refine.task import refine_video
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.orchestrator.progress import update_progress
from app.services.redis import RedisClient
from app.database.checkpoint_queries import get_checkpoint

logger = logging.getLogger(__name__)

# Initialize Redis client
redis_client = RedisClient()


@celery_app.task(bind=True, name="app.orchestrator.pipeline.run_pipeline")
def run_pipeline(self, video_id: str, prompt: str, assets: list = None, model: str = 'hailuo'):
    """
    Main orchestration task - dispatches pipeline as Celery chain and returns immediately.
    Worker thread is freed to handle more videos concurrently.
    
    Writes to DB only at start (video creation). All mid-pipeline updates go to Redis.
    Spec is written to DB only on completion/failure (final submission).
    
    Args:
        video_id: Unique video generation ID
        prompt: User's video description
        assets: Optional list of uploaded assets
        model: Video generation model to use (default: 'hailuo')
        
    Returns:
        Dictionary with video_id, workflow_id, and status
    """
    if assets is None:
        assets = []
    
    print(f"🚀 run_pipeline task executing for video {video_id}")
    print(f"   - Prompt: {prompt[:100]}...")
    print(f"   - Assets: {len(assets)}")
    print(f"   - Model: {model}")
    
    # Get user_id from video record for S3 path organization
    # Note: Video record is already created in generate.py endpoint
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found in DB - should have been created in generate.py")
            raise Exception(f"Video {video_id} not found")
        
        user_id = video.user_id if video else None
        if not user_id:
            # Fallback to mock user ID if not set (for development/testing)
            from app.common.constants import MOCK_USER_ID
            user_id = MOCK_USER_ID
            print(f"⚠️  No user_id found for video {video_id}, using mock user ID: {user_id}")
        
        # Update status to validating (Phase 1 will start)
        # This is a critical update (initial state), so write to DB
        video.status = VideoStatus.VALIDATING
        db.commit()
        print(f"✅ Updated video {video_id} status to VALIDATING in DB")
        
        # Also update Redis (video should already be in Redis from generate.py, but update status)
        if redis_client._client:
            try:
                redis_client.set_video_status(video_id, VideoStatus.VALIDATING.value)
                print(f"✅ Updated video {video_id} status in Redis")
            except Exception as e:
                logger.warning(f"Failed to update Redis: {e}")
    finally:
        db.close()
    
    print(f"🚀 Dispatching Phase 1 (checkpoint-enabled pipeline)...")

    # NEW: Dispatch only Phase 1 instead of entire chain
    # Subsequent phases will be dispatched via continue API or auto-continue
    result = plan_video_intelligent.delay(video_id, prompt)

    print(f"✅ Phase 1 dispatched for video {video_id}")
    print(f"   - Task ID: {result.id}")
    print(f"   - Pipeline will pause at Phase 1 checkpoint")
    print(f"   - Subsequent phases dispatch via /continue endpoint or auto_continue")
    print(f"   - Worker thread freed - can process more videos concurrently")

    # Return immediately - worker thread freed!
    return {
        "video_id": video_id,
        "task_id": result.id,
        "status": "processing"
    }


def get_auto_continue_flag(video_id: str) -> bool:
    """
    Check if video has auto_continue enabled (YOLO mode).

    Args:
        video_id: Video generation ID

    Returns:
        bool: True if auto_continue is enabled, False otherwise
    """
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        if not video:
            logger.warning(f"Video {video_id} not found when checking auto_continue flag")
            return False
        return video.auto_continue if hasattr(video, 'auto_continue') else False
    finally:
        db.close()


def dispatch_next_phase(video_id: str, checkpoint_id: str):
    """
    Dispatch the next phase based on current checkpoint.
    Used by both manual continue and YOLO auto-continue.

    Args:
        video_id: Video generation ID
        checkpoint_id: Current checkpoint ID
    """
    checkpoint = get_checkpoint(checkpoint_id)
    if not checkpoint:
        logger.error(f"Checkpoint {checkpoint_id} not found")
        return

    phase_output = checkpoint['phase_output']
    phase_number = checkpoint['phase_number']
    user_id = checkpoint['user_id']

    # Get video model preference from spec or default to hailuo
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        # Model preference might be stored in spec or phase outputs
        model = 'hailuo'  # Default
        if video and video.spec:
            model = video.spec.get('model', 'hailuo')
    finally:
        db.close()

    logger.info(f"Dispatching Phase {phase_number + 1} for video {video_id}")

    if phase_number == 1:
        # Dispatch Phase 2: Storyboard generation
        generate_storyboard.delay(phase_output, user_id)
    elif phase_number == 2:
        # Dispatch Phase 3: Chunk generation
        generate_chunks.delay(phase_output, user_id, model)
    elif phase_number == 3:
        # Dispatch Phase 4: Refinement
        refine_video.delay(phase_output, user_id)
    elif phase_number == 4:
        logger.info(f"Phase 4 is terminal - no next phase to dispatch")
    else:
        logger.error(f"Invalid phase number: {phase_number}")
