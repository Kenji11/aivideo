# Main orchestration task
import time
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic
from app.phases.phase3_references.task import generate_references
from app.phases.phase4_chunks.task import generate_chunks
from app.phases.phase5_refine.task import refine_video
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.services.s3 import s3_client


@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: list = None, model: str = 'hailuo'):
    """
    Main orchestration task - chains phases sequentially.
    Currently implements Phase 1 (Validate) -> Phase 3 (References) -> Phase 4 (Chunks).
    Phase 2 (Animatic) is skipped for cost/time optimization - Phase 4 uses text-to-video mode.
    
    Args:
        video_id: Unique video generation ID
        prompt: User's video description
        assets: Optional list of uploaded assets
        model: Video generation model to use (default: 'hailuo')
        
    Returns:
        Result dictionary with video_id, status, spec, and cost
        
    Raises:
        Exception: If any phase fails
    """
    if assets is None:
        assets = []
    
    start_time = time.time()
    total_cost = 0.0
    
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
    finally:
        db.close()
    
    try:
        # ============ PHASE 1: VALIDATE & EXTRACT ============
        update_progress(video_id, "validating", 10, current_phase="phase1_validate")
        
        # Run Phase 1 task synchronously (using apply instead of delay().get())
        result1_obj = validate_prompt.apply(args=[video_id, prompt, assets])
        result1 = result1_obj.result  # Get actual result from EagerResult
        
        # Check if result1 is an exception/error
        if isinstance(result1, Exception):
            raise result1
        
        # Check Phase 1 success
        if result1.get('status') != "success":
            raise Exception(f"Phase 1 failed: {result1.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result1['cost_usd']
        update_cost(video_id, "phase1", result1['cost_usd'])
        print(f"💰 Phase 1 Cost: ${result1['cost_usd']:.4f} | Total: ${total_cost:.4f}")
        
        # Extract spec from Phase 1
        spec = result1['output_data']['spec']
        
        # Add model selection to spec for Phase 4
        spec['model'] = model
        
        # Update progress with spec
        update_progress(
            video_id,
            "validating",
            20,
            current_phase="phase1_validate",
            spec=spec,
            total_cost=total_cost
        )
        
        # ============================================================================
        # Phase 2 & 3 temporarily disabled for MVP
        # Phase 2 (Animatic) and Phase 3 (References) are commented out to simplify
        # the pipeline for MVP. Phase 1 output goes directly to Phase 4 (Chunks).
        # To re-enable: uncomment Phase 2 & 3 sections below and update Phase 4 call.
        # ============================================================================
        
        # ============ PHASE 2: GENERATE ANIMATIC ============
        # Phase 2 & 3 temporarily disabled for MVP
        # update_progress(video_id, "generating_animatic", 25, current_phase="phase2_animatic")
        # 
        # # Run Phase 2 task synchronously
        # result2_obj = generate_animatic.apply(args=[video_id, spec])
        # result2 = result2_obj.result
        # 
        # # Check Phase 2 success
        # if result2['status'] != "success":
        #     raise Exception(f"Phase 2 failed: {result2.get('error_message', 'Unknown error')}")
        # 
        # # Update cost tracking
        # total_cost += result2['cost_usd']
        # update_cost(video_id, "phase2", result2['cost_usd'])
        # print(f"💰 Phase 2 Cost: ${result2['cost_usd']:.4f} | Total: ${total_cost:.4f}")
        # 
        # # Extract animatic URLs from Phase 2
        # animatic_urls = result2['output_data'].get('animatic_urls', [])
        # 
        # # Store Phase 2 output in database
        # db = SessionLocal()
        # try:
        #     video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        #     if video:
        #         if video.phase_outputs is None:
        #             video.phase_outputs = {}
        #         video.phase_outputs['phase2_animatic'] = result2
        #         video.animatic_urls = animatic_urls
        #         # Mark JSON column as modified so SQLAlchemy detects the change
        #         from sqlalchemy.orm.attributes import flag_modified
        #         flag_modified(video, 'phase_outputs')
        #         db.commit()
        # finally:
        #     db.close()
        
        # Set empty animatic_urls for Phase 4 (since Phase 2 is disabled)
        animatic_urls = []
        
        # ============ PHASE 3: GENERATE REFERENCE ASSETS ============
        # Skip Phase 3 if user uploaded images - use them directly instead of generating references
        # Check both assets parameter and spec['uploaded_assets'] (Phase 1 adds assets to spec)
        spec_uploaded_assets = spec.get('uploaded_assets', [])
        has_uploaded_assets = (assets and len(assets) > 0) or (spec_uploaded_assets and len(spec_uploaded_assets) > 0)
        
        # Use assets from spec if available (more reliable), otherwise use assets parameter
        assets_to_use = spec_uploaded_assets if spec_uploaded_assets else (assets or [])
        
        print(f"🔍 Phase 3 Skip Check:")
        print(f"   - assets parameter: {len(assets) if assets else 0} items")
        print(f"   - spec['uploaded_assets']: {len(spec_uploaded_assets) if spec_uploaded_assets else 0} items")
        print(f"   - has_uploaded_assets: {has_uploaded_assets}")
        print(f"   - Will use: {len(assets_to_use)} uploaded asset(s)")
        
        if has_uploaded_assets:
            # User uploaded images - skip Phase 3 generation, use uploaded assets directly
            print(f"📸 User uploaded {len(assets_to_use)} image(s) - skipping Phase 3 reference generation")
            print(f"   Will use uploaded images directly for video generation")
            print(f"   ❌ DO NOT GENERATE NEW REFERENCE IMAGES - using uploaded images only")
            
            # Create reference_urls dict with uploaded assets
            # Format: {uploaded_assets: [{s3_key: ..., asset_id: ...}, ...]}
            uploaded_assets_list = []
            for asset in assets_to_use:
                # Handle both dict format (from API) and direct format (from spec)
                if isinstance(asset, dict):
                    s3_key = asset.get('s3_key')
                    asset_id = asset.get('asset_id')
                else:
                    # Fallback if asset is in different format
                    s3_key = getattr(asset, 's3_key', None) if hasattr(asset, 's3_key') else None
                    asset_id = getattr(asset, 'asset_id', None) if hasattr(asset, 'asset_id') else None
                
                if s3_key:
                    uploaded_assets_list.append({
                        's3_key': s3_key,
                        's3_url': f"s3://{s3_client.bucket}/{s3_key}",
                        'asset_id': asset_id
                    })
            
            reference_urls = {
                'uploaded_assets': uploaded_assets_list,
                'style_guide_url': None,
                'product_reference_url': None
            }
            
            # Update progress to show we're using uploaded assets
            update_progress(
                video_id,
                "using_uploaded_assets",
                30,
                current_phase="phase3_references",
                total_cost=total_cost
            )
            print(f"✅ Using {len(uploaded_assets_list)} uploaded image(s) as reference assets")
            
        else:
            # No uploaded assets - generate reference images in Phase 3
            update_progress(video_id, "generating_references", 30, current_phase="phase3_references")
            
            # Run Phase 3 task synchronously (using apply instead of delay().get())
            # Pass user_id for new S3 path structure
            result3_obj = generate_references.apply(args=[video_id, spec, user_id])
            result3 = result3_obj.result  # Get actual result from EagerResult
            
            # Check Phase 3 success
            if result3['status'] != "success":
                raise Exception(f"Phase 3 failed: {result3.get('error_message', 'Unknown error')}")
            
            # Update cost tracking
            total_cost += result3['cost_usd']
            update_cost(video_id, "phase3", result3['cost_usd'])
            print(f"💰 Phase 3 Cost: ${result3['cost_usd']:.4f} | Total: ${total_cost:.4f}")
            
            # Extract reference URLs from Phase 3
            reference_urls = result3['output_data']
        
        # Store Phase 3 output in database (or uploaded assets info)
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                
                if has_uploaded_assets:
                    # Store uploaded assets info instead of Phase 3 output
                    video.phase_outputs['phase3_references'] = {
                        'status': 'skipped',
                        'reason': 'user_uploaded_assets',
                        'uploaded_assets_count': len(uploaded_assets_list)
                    }
                else:
                    # Store Phase 3 output
                    video.phase_outputs['phase3_references'] = result3
                
                video.reference_assets = reference_urls
                # Mark JSON column as modified so SQLAlchemy detects the change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Update progress
        phase3_status = "using_uploaded_assets" if has_uploaded_assets else "generating_references"
        update_progress(
            video_id,
            phase3_status,
            40,
            current_phase="phase3_references",
            total_cost=total_cost
        )
        
        # ============ PHASE 4: GENERATE VIDEO CHUNKS ============
        # Progress: Phase 1 ends at 20%, Phase 3 ends at 40%, Phase 4 starts at 50% (skipping Phase 2)
        update_progress(video_id, "generating_chunks", 50, current_phase="phase4_chunks")
        
        # Run Phase 4 task synchronously
        # Phase 2 is skipped (empty animatic_urls), but Phase 3 reference_urls are passed
        # Pass user_id for new S3 path structure
        result4_obj = generate_chunks.apply(args=[video_id, spec, animatic_urls, reference_urls, user_id])
        result4 = result4_obj.result
        
        # Check Phase 4 success
        if result4['status'] != "success":
            raise Exception(f"Phase 4 failed: {result4.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result4['cost_usd']
        update_cost(video_id, "phase4", result4['cost_usd'])
        print(f"💰 Phase 4 Cost: ${result4['cost_usd']:.4f} | Total: ${total_cost:.4f}")
        
        # Extract stitched video URL from Phase 4
        stitched_video_url = result4['output_data'].get('stitched_video_url')
        chunk_urls = result4['output_data'].get('chunk_urls', [])
        
        # Store Phase 4 output in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                video.phase_outputs['phase4_chunks'] = result4
                video.stitched_url = stitched_video_url
                video.chunk_urls = chunk_urls
                # Phase 4 updates final_video_url (will be overwritten by Phase 5 if it runs)
                video.final_video_url = stitched_video_url
                # Mark JSON column as modified so SQLAlchemy detects the change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Update progress - Phase 4 completes at 90%
        update_progress(
            video_id,
            "generating_chunks",
            90,
            current_phase="phase4_chunks",
            total_cost=total_cost
        )
        
        # ============ PHASE 5: REFINE & ENHANCE ============
        if stitched_video_url:
            # Phase 5 starts at 90%, will complete at 100%
            update_progress(video_id, "refining", 90, current_phase="phase5_refine")
            
            # Run Phase 5 task synchronously
            # Pass user_id for new S3 path structure
            result5_obj = refine_video.apply(args=[video_id, stitched_video_url, spec, user_id])
            result5 = result5_obj.result
            
            # Extract music_url from Phase 5 output (even if combining failed)
            music_url = result5.get('output_data', {}).get('music_url')
            
            # Check Phase 5 success
            if result5['status'] != "success":
                print(f"⚠️  Phase 5 failed: {result5.get('error_message', 'Unknown error')}")
                # Continue anyway - use stitched video as fallback
                refined_video_url = stitched_video_url
            else:
                # Update cost tracking
                total_cost += result5['cost_usd']
                update_cost(video_id, "phase5", result5['cost_usd'])
                print(f"💰 Phase 5 Cost: ${result5['cost_usd']:.4f} | Total: ${total_cost:.4f}")
                
                # Extract refined video URL from Phase 5
                refined_video_url = result5['output_data'].get('refined_video_url', stitched_video_url)
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Store Phase 5 output in database (including music_url even if combining failed)
            db = SessionLocal()
            try:
                video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                if video:
                    if video.phase_outputs is None:
                        video.phase_outputs = {}
                    video.phase_outputs['phase5_refine'] = result5
                    video.refined_url = refined_video_url
                    # Update final_video_url to the new URL (with music if combining succeeded)
                    video.final_video_url = refined_video_url
                    # Save music_url even if combining failed (for retry later)
                    if music_url:
                        video.final_music_url = music_url
                    # Update Phase 5 progress, status, and final metadata
                    video.progress = 100.0
                    video.current_phase = "phase5_refine"
                    video.status = VideoStatus.COMPLETE
                    video.cost_usd = total_cost
                    video.generation_time_seconds = generation_time
                    if video.completed_at is None:
                        from datetime import datetime
                        video.completed_at = datetime.utcnow()
                    flag_modified(video, 'phase_outputs')
                    db.commit()
            finally:
                db.close()
        else:
            refined_video_url = stitched_video_url
            # Phase 5 was skipped - update final status
            generation_time = time.time() - start_time
            db = SessionLocal()
            try:
                video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                if video:
                    video.status = VideoStatus.COMPLETE
                    video.progress = 100.0
                    video.current_phase = "phase4_chunks"
                    video.cost_usd = total_cost
                    video.generation_time_seconds = generation_time
                    video.final_video_url = refined_video_url
                    if video.completed_at is None:
                        from datetime import datetime
                        video.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        
        # Print final cost summary
        print("="*70)
        print(f"✅ VIDEO GENERATION COMPLETE: {video_id}")
        print("="*70)
        print(f"💰 TOTAL COST: ${total_cost:.4f} USD")
        print(f"   - Phase 1 (Validate): ${result1['cost_usd']:.4f}")
        print(f"   - Phase 3 (References): ${result3['cost_usd']:.4f}")
        print(f"   - Phase 4 (Chunks): ${result4['cost_usd']:.4f}")
        if 'cost_usd' in result5 and result5.get('status') == 'success':
            print(f"   - Phase 5 (Refine): ${result5['cost_usd']:.4f}")
        print(f"⏱️  Generation Time: {generation_time:.1f} seconds ({generation_time/60:.1f} minutes)")
        print(f"📹 Video URL: {stitched_video_url}")
        print("="*70)
        
        return {
            "video_id": video_id,
            "status": "success",
            "spec": spec,
            "stitched_video_url": stitched_video_url,
            "cost_usd": total_cost,
            "generation_time_seconds": generation_time
        }
        
    except Exception as e:
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            total_cost=total_cost
        )
        print("="*70)
        print(f"❌ VIDEO GENERATION FAILED: {video_id}")
        print("="*70)
        print(f"💰 Total Cost Before Failure: ${total_cost:.4f} USD")
        print(f"❌ Error: {str(e)}")
        print("="*70)
        raise
