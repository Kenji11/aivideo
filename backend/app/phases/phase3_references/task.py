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
from app.phases.phase3_references.service import ReferenceAssetService
from app.common.constants import COST_SDXL_IMAGE


@celery_app.task(bind=True)
def generate_references(self, video_id: str, spec: dict, user_id: str = None):
    """
    Phase 3: Generate reference assets (style guide, product references).
    
    ⚠️ DISABLED: This phase is disabled in TDD v2.0. Phase 2 storyboard generation
    replaces this functionality. This function returns immediately with "skipped" status.
    
    Args:
        video_id: Unique video generation ID
        spec: Video specification from Phase 1
        user_id: User ID for organizing outputs in S3 (required for new structure)
        
    Returns:
        PhaseOutput dict with "skipped" status
    """
    start_time = time.time()
    duration_seconds = time.time() - start_time
    
    # Return skipped status immediately - Phase 3 is disabled
    output = PhaseOutput(
        video_id=video_id,
        phase="phase3_references",
        status="skipped",
        output_data={"message": "Phase 3 disabled - using Phase 2 storyboard instead"},
        cost_usd=0.0,
        duration_seconds=duration_seconds,
        error_message="Phase 3 is disabled in TDD v2.0"
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
