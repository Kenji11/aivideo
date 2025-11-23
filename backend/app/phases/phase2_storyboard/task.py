"""
Phase 2: Storyboard Generation Task

Generates one storyboard image per beat from Phase 1 spec.
Each image is uploaded to S3 and the URL is saved to the beat in the spec.
"""

import time
import logging
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase2_storyboard.image_generation import generate_beat_image
from app.common.constants import COST_FLUX_DEV_IMAGE
from app.common.exceptions import PhaseException
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from sqlalchemy.orm.attributes import flag_modified
from app.database.checkpoint_queries import create_checkpoint, create_artifact, approve_checkpoint, update_checkpoint_phase_output

logger = logging.getLogger(__name__)


def _generate_storyboard_impl(
    video_id: str,
    spec: dict,
    user_id: str = None,
    branch_name: str = 'main',
    parent_checkpoint_id: str = None,
    version: int = 1
):
    """
    Core implementation of storyboard generation (without Celery wrapper).

    This function contains the actual logic and can be called directly for testing.

    Args:
        video_id: Video generation ID
        spec: Video specification from Phase 1
        user_id: User ID for S3 organization
        branch_name: Branch name for checkpoint tree (default: 'main')
        parent_checkpoint_id: Parent checkpoint ID (from Phase 1)
        version: Version number for artifact versioning (default: 1)
    """
    start_time = time.time()
    
    try:
        # Update progress at start
        update_progress(video_id, "generating_storyboard", 25, current_phase="phase2_storyboard")
        
        # Extract required information from spec
        beats = spec.get('beats', [])
        style = spec.get('style', {})
        product = spec.get('product', {})
        spec_duration = spec.get('duration', 'unknown')
        
        # Log received spec details
        logger.info(f"📥 Phase 2 received spec:")
        logger.info(f"   - Duration: {spec_duration}s")
        logger.info(f"   - Beats count: {len(beats)}")
        logger.info(f"   - Beat details:")
        for i, beat in enumerate(beats, 1):
            logger.info(f"      {i}. {beat.get('beat_id', 'unknown')} - {beat.get('duration', '?')}s (start: {beat.get('start', 0)}s)")
        
        if not beats:
            raise PhaseException("Spec must contain at least one beat")
        
        if not user_id:
            raise PhaseException("user_id is required for S3 uploads")
        
        logger.info(
            f"Starting Phase 2 storyboard generation for video {video_id}: "
            f"{len(beats)} beats to generate"
        )
        
        # Initialize tracking
        storyboard_images = []
        total_cost = 0.0
        
        # Generate one image per beat
        for beat_index, beat in enumerate(beats):
            logger.info(
                f"Generating storyboard image {beat_index + 1}/{len(beats)}: "
                f"beat_id={beat.get('beat_id')}, duration={beat.get('duration')}s"
            )
            
            # Generate image for this beat with versioning
            beat_image_info = generate_beat_image(
                video_id=video_id,
                beat_index=beat_index,
                beat=beat,
                style=style,
                product=product,
                user_id=user_id,
                version=version  # Pass version for S3 path
            )
            
            # Add image URL to the beat in spec
            beat['image_url'] = beat_image_info['image_url']
            
            # Track storyboard image info
            storyboard_images.append(beat_image_info)
            
            # Track cost (FLUX Dev: $0.025 per image)
            total_cost += COST_FLUX_DEV_IMAGE
            
            logger.info(
                f"✅ Generated storyboard image {beat_index + 1}/{len(beats)}: "
                f"{beat_image_info['image_url'][:80]}..."
            )
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Update cost tracking
        update_cost(video_id, "phase2_storyboard", total_cost)
        
        # Update progress
        update_progress(
            video_id,
            "generating_storyboard",
            40,
            current_phase="phase2_storyboard",
            total_cost=total_cost
        )
        
        logger.info(
            f"✅ Phase 2 complete: {len(storyboard_images)} storyboard images generated, "
            f"cost=${total_cost:.4f}, duration={duration_seconds:.2f}s"
        )
        
        # Extract storyboard URLs from beats and persist to Redis
        storyboard_urls = []
        for beat in beats:
            image_url = beat.get('image_url')
            if image_url:
                storyboard_urls.append(image_url)
        
        if storyboard_urls:
            from app.services.redis import RedisClient
            redis_client = RedisClient()
            redis_client.set_video_storyboard_urls(video_id, storyboard_urls)
            logger.info(f"✅ Persisted {len(storyboard_urls)} storyboard URLs to Redis")
        
        # Build PhaseOutput
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="success",
            output_data={
                "storyboard_images": storyboard_images,
                "spec": spec  # Return updated spec with image_urls in beats
            },
            cost_usd=total_cost,
            duration_seconds=duration_seconds,
            error_message=None
        )

        # Create checkpoint and artifacts
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                logger.error(f"Video {video_id} not found")
                raise PhaseException(f"Video {video_id} not found")

            # Create checkpoint record
            logger.info(f"Creating Phase 2 checkpoint for video {video_id} on branch '{branch_name}'")
            checkpoint_id = create_checkpoint(
                video_id=video_id,
                branch_name=branch_name,
                phase_number=2,
                version=version,
                phase_output=output.dict(),
                cost_usd=total_cost,
                user_id=user_id,
                parent_checkpoint_id=parent_checkpoint_id
            )
            logger.info(f"✅ Created checkpoint {checkpoint_id}")

            # Create artifacts for each beat image
            for beat_image_info in storyboard_images:
                artifact_id = create_artifact(
                    checkpoint_id=checkpoint_id,
                    artifact_type='beat_image',
                    artifact_key=f"beat_{beat_image_info['beat_index']}",
                    s3_url=beat_image_info['image_url'],
                    s3_key=beat_image_info['s3_key'],
                    version=version,
                    metadata={
                        'beat_id': beat_image_info['beat_id'],
                        'prompt_used': beat_image_info['prompt_used'],
                        'shot_type': beat_image_info['shot_type']
                    }
                )
            logger.info(f"✅ Created {len(storyboard_images)} beat artifacts")

            # Add checkpoint_id to output
            output.checkpoint_id = checkpoint_id

            # Update checkpoint's phase_output to include checkpoint_id for next phase
            update_checkpoint_phase_output(checkpoint_id, {'checkpoint_id': checkpoint_id})

            # Update video status to paused
            video.status = VideoStatus.PAUSED_AT_PHASE2
            video.current_phase = 'phase2'
            video.progress = 40.0  # Phase 2 complete (40% of total pipeline)
            if video.phase_outputs is None:
                video.phase_outputs = {}
            video.phase_outputs['phase2_storyboard'] = output.dict()
            flag_modified(video, 'phase_outputs')
            db.commit()
            logger.info(f"✅ Updated video status to PAUSED_AT_PHASE2")

            # Update progress in Redis
            update_progress(
                video_id,
                status='paused_at_phase2',
                current_phase='phase2',
                progress=40.0,
                phase_outputs=video.phase_outputs
            )

            # Check YOLO mode (auto_continue)
            if hasattr(video, 'auto_continue') and video.auto_continue:
                logger.info(f"🚀 YOLO mode enabled - auto-continuing to Phase 3")
                approve_checkpoint(checkpoint_id)

                # Import here to avoid circular dependency
                from app.orchestrator.pipeline import dispatch_next_phase
                dispatch_next_phase(video_id, checkpoint_id)
            else:
                logger.info(f"⏸️  Pipeline paused at Phase 2 - awaiting user approval")

        finally:
            db.close()

        # Return PhaseOutput with checkpoint_id
        return output.dict()
        
    except Exception as e:
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        logger.error(f"❌ Phase 2 failed for video {video_id}: {str(e)}")
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase2_storyboard"
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
                    "phase": "phase2_storyboard",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": str(e)
                }
                video.phase_outputs['phase2_storyboard'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Create failure output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        return output.dict()


@celery_app.task(bind=True)
def generate_storyboard(self, phase1_output: dict, user_id: str = None):
    """
    Phase 2: Generate storyboard images (one per beat).
    
    Receives Phase 1 output and extracts spec from it.
    
    Args:
        self: Celery task instance (from bind=True)
        phase1_output: PhaseOutput dict from Phase 1 (contains spec in output_data)
        user_id: User ID for organizing outputs in S3 (required)
        
    Returns:
        PhaseOutput dict with storyboard_images list and updated spec
    """
    # Check if Phase 1 succeeded
    if phase1_output.get('status') != 'success':
        error_msg = phase1_output.get('error_message', 'Phase 1 failed')
        video_id = phase1_output.get('video_id', 'unknown')
        logger.error(f"Phase 1 failed, cannot proceed with Phase 2: {error_msg}")
        
        # Update progress
        update_progress(video_id, "failed", 0, error_message=f"Phase 1 failed: {error_msg}", current_phase="phase2_storyboard")
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=0.0,
            error_message=f"Phase 1 failed: {error_msg}"
        ).dict()
    
    # Extract spec and video_id from Phase 1 output
    video_id = phase1_output['video_id']
    spec = phase1_output['output_data']['spec']

    # Extract branch context from Phase 1 output (for checkpoint tree)
    branch_name = phase1_output.get('_branch_name', 'main')
    parent_checkpoint_id = phase1_output.get('checkpoint_id')
    version = phase1_output.get('_version', 1)

    logger.info(f"Phase 2 starting with branch context: branch={branch_name}, version={version}, parent_checkpoint={parent_checkpoint_id}")

    # Call core implementation with branch context
    return _generate_storyboard_impl(
        video_id,
        spec,
        user_id,
        branch_name=branch_name,
        parent_checkpoint_id=parent_checkpoint_id,
        version=version
    )
