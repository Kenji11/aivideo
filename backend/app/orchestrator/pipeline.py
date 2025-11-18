# Main orchestration task
import time
from celery import chain
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_storyboard.task import generate_storyboard
from app.phases.phase3_references.task import generate_references
from app.phases.phase4_chunks_storyboard.task import generate_chunks as generate_chunks_storyboard
from app.phases.phase5_refine.task import refine_video
from app.database import SessionLocal
from app.common.models import VideoGeneration


@celery_app.task(bind=True, name="app.orchestrator.pipeline.run_pipeline")
def run_pipeline(self, video_id: str, prompt: str, assets: list = None, model: str = 'hailuo'):
    """
    Main orchestration task - dispatches pipeline as Celery chain and returns immediately.
    Worker thread is freed to handle more videos concurrently.
    
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
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        user_id = video.user_id if video else None
        if not user_id:
            # Fallback to mock user ID if not set (for development/testing)
            from app.common.constants import MOCK_USER_ID
            user_id = MOCK_USER_ID
            print(f"⚠️  No user_id found for video {video_id}, using mock user ID: {user_id}")
        
        # Update status to validating (Phase 1 will start)
        if video:
            from app.common.models import VideoStatus
            video.status = VideoStatus.VALIDATING
            db.commit()
            print(f"✅ Updated video {video_id} status to VALIDATING")
    finally:
        db.close()
    
    print(f"🔗 Creating chain workflow for video {video_id}...")
    
    # Create chain workflow - each phase receives previous phase's PhaseOutput as first arg
    workflow = chain(
        # Phase 1: Validate prompt and extract spec
        validate_prompt.s(video_id, prompt, assets),
        
        # Phase 2: Generate storyboard images (receives Phase 1 output)
        generate_storyboard.s(user_id),
        
        # Phase 3: Generate references (receives Phase 2 output, may skip if storyboard exists)
        generate_references.s(user_id),
        
        # Phase 4: Generate chunks and stitch (receives Phase 3 output)
        generate_chunks_storyboard.s(user_id, model),
        
        # Phase 5: Refine video with music (receives Phase 4 output)
        refine_video.s(user_id)
    )
    
    print(f"🔗 Chain created, dispatching with apply_async()...")
    result = workflow.apply_async()
    
    print(f"✅ Pipeline chain dispatched for video {video_id}")
    print(f"   - Workflow ID: {result.id}")
    print(f"   - Worker thread freed - can process more videos concurrently")
    
    # Return immediately - worker thread freed!
    return {
        "video_id": video_id,
        "workflow_id": result.id,
        "status": "processing"
    }
