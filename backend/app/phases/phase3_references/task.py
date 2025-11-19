# ============================================================================
# PHASE 3 DISABLED - REPLACED BY PHASE 2 STORYBOARD GENERATION (TDD v2.0)
# ============================================================================
# This phase is kept in codebase for backward compatibility with old videos
# but is NOT used for new video generation.
# 
# OLD System: Phase 3 generated 1 reference image per video
# NEW System: Phase 2 generates N storyboard images (1 per beat)
# 
# DO NOT DELETE - May be needed for legacy video playback/debugging
# ============================================================================

import time
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration
from sqlalchemy.orm.attributes import flag_modified


@celery_app.task(bind=True)
def generate_references(self, phase2_output: dict, user_id: str = None):
    """
    Phase 3: Generate reference assets (style guide, product references).
    
    ⚠️ DISABLED: This phase is disabled in TDD v2.0. Phase 2 storyboard generation
    replaces this functionality. This function checks if storyboard images exist and
    skips if they do, otherwise returns success with empty references.
    
    Args:
        self: Celery task instance (from bind=True)
        phase2_output: PhaseOutput dict from Phase 2 (contains spec and storyboard_images)
        user_id: User ID for organizing outputs in S3 (required for new structure)
        
    Returns:
        PhaseOutput dict with reference_urls (empty if storyboard mode)
    """
    start_time = time.time()
    
    # Check if Phase 2 succeeded
    if phase2_output.get('status') != 'success':
        error_msg = phase2_output.get('error_message', 'Phase 2 failed')
        video_id = phase2_output.get('video_id', 'unknown')
        
        # Update progress
        update_progress(video_id, "failed", 0, error_message=f"Phase 2 failed: {error_msg}", current_phase="phase3_references")
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_references",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=0.0,
            error_message=f"Phase 2 failed: {error_msg}"
        ).dict()
    
    # Extract data from Phase 2 output
    video_id = phase2_output['video_id']
    spec = phase2_output['output_data']['spec']  # Keep spec to pass through to Phase 4
    storyboard_images = phase2_output['output_data'].get('storyboard_images', [])
    
    # Update progress
    has_storyboard_images = len(storyboard_images) > 0
    
    if has_storyboard_images:
        # Storyboard images exist - skip Phase 3
        update_progress(
            video_id,
            "skipped_phase3_storyboard_mode",
            40,
            current_phase="phase3_references"
        )
        print(f"🎨 Storyboard images detected ({len(storyboard_images)}) - skipping Phase 3 reference generation")
    else:
        # No storyboard images - Phase 3 would generate references (but it's disabled)
        update_progress(video_id, "generating_references", 30, current_phase="phase3_references")
    
    duration_seconds = time.time() - start_time
    
    # Create reference_urls dict
    reference_urls = {
        'style_guide_url': None,
        'product_reference_url': None
    }
    
    # Store Phase 3 output in database
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        if video:
            if video.phase_outputs is None:
                video.phase_outputs = {}
            
            if has_storyboard_images:
                # Store skip info
                output_dict = {
                    'status': 'skipped',
                    'reason': 'storyboard_mode',
                    'storyboard_images_count': len(storyboard_images)
                }
            else:
                # Store success with empty references
                output_dict = {
                    "video_id": video_id,
                    "phase": "phase3_references",
                    "status": "success",
                    "output_data": reference_urls,
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": None
                }
            
            video.phase_outputs['phase3_references'] = output_dict
            video.reference_assets = reference_urls
            flag_modified(video, 'phase_outputs')
            db.commit()
    finally:
        db.close()
    
    # Return success status with empty references - Phase 3 is disabled but pipeline expects success
    # Phase 2 storyboard images are used instead of Phase 3 references
    # Pass through spec from Phase 2 so Phase 4 doesn't need to query database
    output = PhaseOutput(
        video_id=video_id,
        phase="phase3_references",
        status="success",
        output_data={
            **reference_urls,  # Include reference_urls
            "spec": spec  # Pass through spec from Phase 2
        },
        cost_usd=0.0,
        duration_seconds=duration_seconds,
        error_message=None
    )
    
    return output.dict()
    
    # ============================================================================
    # OLD IMPLEMENTATION (COMMENTED OUT - DO NOT DELETE)
    # ============================================================================
    # try:
    #     # Initialize reference service
    #     service = ReferenceAssetService()
    #     
    #     # Generate all references
    #     references = service.generate_all_references(video_id, spec, user_id)
    #     
    #     # Calculate duration
    #     duration_seconds = time.time() - start_time
    #     
    #     # Create success output
    #     output = PhaseOutput(
    #         video_id=video_id,
    #         phase="phase3_references",
    #         status="success",
    #         output_data=references,
    #         cost_usd=service.total_cost,
    #         duration_seconds=duration_seconds,
    #         error_message=None
    #     )
    #     
    #     return output.dict()
    #     
    # except Exception as e:
    #     # Calculate duration
    #     duration_seconds = time.time() - start_time
    #     
    #     # Create failure output
    #     output = PhaseOutput(
    #         video_id=video_id,
    #         phase="phase3_references",
    #         status="failed",
    #         output_data={},
    #         cost_usd=0.0,
    #         duration_seconds=duration_seconds,
    #         error_message=str(e)
    #     )
    #     
    #     return output.dict()
    # ============================================================================
