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
from app.common.models import VideoGeneration
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)


def _generate_storyboard_impl(video_id: str, spec: dict, user_id: str = None, reference_mapping: dict = None, user_assets: list = None):
    """
    Core implementation of storyboard generation (without Celery wrapper).
    
    This function contains the actual logic and can be called directly for testing.
    
    Args:
        video_id: Video generation ID
        spec: Video specification from Phase 1
        user_id: User ID for S3 uploads
        reference_mapping: Optional dict mapping beat_id to reference assets (from Phase 1)
        user_assets: Optional list of user asset dicts (from Phase 0) for metadata lookup
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
        
        # Log reference mapping if present
        if reference_mapping:
            logger.info(f"Reference mapping available for {len(reference_mapping)} beats")
            for beat_id, ref_info in reference_mapping.items():
                logger.info(f"  {beat_id}: {ref_info.get('usage_type')} - {ref_info.get('asset_ids')}")
        
        # Initialize tracking
        storyboard_images = []
        total_cost = 0.0
        all_referenced_asset_ids = set()  # Track all assets used across beats
        
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
                user_id=user_id,
                reference_mapping=reference_mapping,
                user_assets=user_assets
            )
            
            # Add image URL to the beat in spec
            beat['image_url'] = beat_image_info['image_url']
            
            # Track storyboard image info
            storyboard_images.append(beat_image_info)
            
            # Track referenced assets
            referenced_assets = beat_image_info.get('referenced_asset_ids', [])
            if referenced_assets:
                all_referenced_asset_ids.update(referenced_assets)
                logger.info(f"  Referenced assets: {referenced_assets}")
            
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
        
        # Log asset usage summary
        if all_referenced_asset_ids:
            logger.info(f"Total unique assets referenced: {len(all_referenced_asset_ids)}")
            logger.info(f"Asset IDs: {list(all_referenced_asset_ids)}")
        
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
        
        # Store Phase 2 output in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                output_dict = {
                    "video_id": video_id,
                    "phase": "phase2_storyboard",
                    "status": "success",
                    "output_data": {
                        "storyboard_images": storyboard_images,
                        "spec": spec,
                        "referenced_asset_ids": list(all_referenced_asset_ids)  # Track for usage counting
                    },
                    "cost_usd": total_cost,
                    "duration_seconds": duration_seconds,
                    "error_message": None
                }
                video.phase_outputs['phase2_storyboard'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Create success output
        # Note: spec is updated in-place with image_url added to each beat
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="success",
            output_data={
                "storyboard_images": storyboard_images,
                "spec": spec,  # Return updated spec with image_urls in beats
                "referenced_asset_ids": list(all_referenced_asset_ids)  # Track for usage counting
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
    output_data = phase1_output['output_data']
    spec = output_data['spec']
    
    # Extract reference mapping if present (from Phase 1)
    reference_mapping = output_data.get('reference_mapping')
    
    # Extract user_assets from Phase 0 output if present
    # Phase 1 stores phase0_output in its output_data
    user_assets = None
    if 'phase0_output' in output_data:
        phase0_data = output_data['phase0_output']
        if phase0_data and phase0_data.get('status') == 'success':
            user_assets = phase0_data.get('output_data', {}).get('user_assets')
    
    # Call core implementation
    return _generate_storyboard_impl(video_id, spec, user_id, reference_mapping, user_assets)
