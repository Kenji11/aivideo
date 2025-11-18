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

logger = logging.getLogger(__name__)


def _generate_storyboard_impl(video_id: str, spec: dict, user_id: str = None):
    """
    Core implementation of storyboard generation (without Celery wrapper).
    
    This function contains the actual logic and can be called directly for testing.
    """
    start_time = time.time()
    
    try:
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
            
            # Generate image for this beat
            beat_image_info = generate_beat_image(
                video_id=video_id,
                beat_index=beat_index,
                beat=beat,
                style=style,
                product=product,
                user_id=user_id
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
        
        logger.info(
            f"✅ Phase 2 complete: {len(storyboard_images)} storyboard images generated, "
            f"cost=${total_cost:.4f}, duration={duration_seconds:.2f}s"
        )
        
        # Create success output
        # Note: spec is updated in-place with image_url added to each beat
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
        
        return output.dict()
        
    except Exception as e:
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        logger.error(f"❌ Phase 2 failed for video {video_id}: {str(e)}")
        
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
def generate_storyboard(self, video_id: str, spec: dict, user_id: str = None):
    """
    Phase 2: Generate storyboard images (one per beat).
    
    Celery task wrapper that calls the core implementation.
    
    Args:
        self: Celery task instance (from bind=True)
        video_id: Unique video generation ID
        spec: Video specification from Phase 1 (must contain 'beats' list)
        user_id: User ID for organizing outputs in S3 (required)
        
    Returns:
        PhaseOutput dict with storyboard_images list and updated spec
    """
    return _generate_storyboard_impl(video_id, spec, user_id)

