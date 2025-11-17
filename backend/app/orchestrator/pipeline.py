# Main orchestration task
import time
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_storyboard.task import generate_storyboard
# from app.phases.phase3_references.task import generate_references  # COMMENTED OUT - Phase 3 disabled
from app.phases.phase4_chunks.task import generate_chunks as generate_chunks_old
from app.phases.phase4_chunks_storyboard.task import generate_chunks as generate_chunks_storyboard
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
        
        # ============ PHASE 2: GENERATE STORYBOARD ============
        # Generate one storyboard image per beat - these will be used as input for Phase 4 chunks
        update_progress(video_id, "generating_storyboard", 25, current_phase="phase2_storyboard")
        
        # Run Phase 2 task synchronously (using apply instead of delay().get())
        # Pass user_id for new S3 path structure
        result2_obj = generate_storyboard.apply(args=[video_id, spec, user_id])
        result2 = result2_obj.result  # Get actual result from EagerResult
        
        # Check if result2 is an exception/error
        if isinstance(result2, Exception):
            raise result2
        
        # Check Phase 2 success
        if result2.get('status') != "success":
            raise Exception(f"Phase 2 failed: {result2.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result2['cost_usd']
        update_cost(video_id, "phase2", result2['cost_usd'])
        print(f"💰 Phase 2 Cost: ${result2['cost_usd']:.4f} | Total: ${total_cost:.4f}")
        
        # Extract updated spec from Phase 2 (beats now have image_url)
        spec = result2['output_data']['spec']
        
        # CRITICAL: Preserve model selection (Phase 2 might not include it)
        if 'model' not in spec:
            spec['model'] = model
        elif spec.get('model') != model:
            # If model was set but doesn't match, use the one from pipeline parameter
            print(f"⚠️  Model mismatch: spec had '{spec.get('model')}', using '{model}' from pipeline")
            spec['model'] = model
        
        # Extract storyboard image URLs from beats (one per beat)
        # Storyboard images are stored in beat['image_url'] after Phase 2
        storyboard_urls = []
        beats = spec.get('beats', [])
        for beat in beats:
            image_url = beat.get('image_url')
            if image_url:
                storyboard_urls.append(image_url)
        
        print(f"📸 Generated {len(storyboard_urls)} storyboard images (one per beat)")
        
        # Store Phase 2 output in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                video.phase_outputs['phase2_storyboard'] = result2
                # Mark JSON column as modified so SQLAlchemy detects the change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Use storyboard URLs for Phase 4 (replaces old animatic_urls)
        animatic_urls = storyboard_urls  # Phase 4 will use these as input images
        
        # ============ PHASE 3: COMMENTED OUT ============
        # Phase 3 is completely disabled - Phase 2 storyboard images are used directly for Phase 4
        # No reference image generation needed when using storyboard images
        print(f"⏭️  Phase 3 disabled - going directly from Phase 2 to Phase 4")
        
        # Create empty reference_urls - Phase 4 will use storyboard images from Phase 2
        reference_urls = {
            'uploaded_assets': [],
            'style_guide_url': None,
            'product_reference_url': None
        }
        
        # # ============ PHASE 3: GENERATE REFERENCE ASSETS (COMMENTED OUT) ============
        # # Phase 3 is completely skipped - Phase 2 storyboard images are used directly for Phase 4
        # update_progress(video_id, "generating_references", 30, current_phase="phase3_references")
        # 
        # # Run Phase 3 task synchronously (using apply instead of delay().get())
        # # Pass user_id for new S3 path structure
        # result3_obj = generate_references.apply(args=[video_id, spec, user_id])
        # result3 = result3_obj.result  # Get actual result from EagerResult
        # 
        # # Check Phase 3 success
        # if result3['status'] != "success":
        #     raise Exception(f"Phase 3 failed: {result3.get('error_message', 'Unknown error')}")
        # 
        # # Update cost tracking
        # total_cost += result3['cost_usd']
        # update_cost(video_id, "phase3", result3['cost_usd'])
        # print(f"💰 Phase 3 Cost: ${result3['cost_usd']:.4f} | Total: ${total_cost:.4f}")
        # 
        # # Extract reference URLs from Phase 3
        # reference_urls = result3['output_data']
        # 
        # # Store Phase 3 output in database
        # db = SessionLocal()
        # try:
        #     video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        #     if video:
        #         if video.phase_outputs is None:
        #             video.phase_outputs = {}
        #         video.phase_outputs['phase3_references'] = result3
        #         video.reference_assets = reference_urls
        #         # Mark JSON column as modified so SQLAlchemy detects the change
        #         from sqlalchemy.orm.attributes import flag_modified
        #         flag_modified(video, 'phase_outputs')
        #         db.commit()
        # finally:
        #     db.close()
        
        # Update progress - Phase 3 skipped, move directly to Phase 4
        update_progress(
            video_id,
            "generating_chunks",
            40,
            current_phase="phase4_chunks",
            total_cost=total_cost
        )
        
        # ============ PHASE 4: GENERATE VIDEO CHUNKS ============
        # Progress: Phase 1 ends at 20%, Phase 2 ends at 25%, Phase 3 disabled, Phase 4 starts at 40%
        update_progress(video_id, "generating_chunks", 50, current_phase="phase4_chunks")
        
        # Use storyboard-aware logic dynamically based on Phase 2 output
        # Phase 2 always runs and creates one storyboard image per beat
        beats = spec.get('beats', [])
        storyboard_images_count = sum(1 for beat in beats if beat.get('image_url'))
        
        print(f"📊 Phase 4: Using storyboard logic with {storyboard_images_count} storyboard images from {len(beats)} beats")
        
        # Always use storyboard logic - it dynamically handles any number of images
        # The storyboard logic will:
        # - Use storyboard images at beat boundaries (mapped dynamically based on actual count)
        # - Use last-frame continuation within beats
        # - Handle edge cases (missing images, partial images, etc.)
        result4_obj = generate_chunks_storyboard.apply(args=[video_id, spec, animatic_urls, reference_urls, user_id])
        result4 = result4_obj.result
        
        # Check if result4 is an exception/error
        if isinstance(result4, Exception):
            # If storyboard logic failed due to missing images, fall back to old logic
            error_msg = str(result4)
            if "No storyboard images found" in error_msg or "storyboard" in error_msg.lower():
                print(f"⚠️  Storyboard logic failed: {error_msg}")
                print(f"📊 Phase 4: Falling back to old logic")
                result4_obj = generate_chunks_old.apply(args=[video_id, spec, animatic_urls, reference_urls, user_id])
                result4 = result4_obj.result
            else:
                # Re-raise if it's a different error
                raise result4
        
        # Check if Phase 4 failed with error message about storyboard
        if result4.get('status') != "success":
            error_msg = result4.get('error_message', '')
            if "No storyboard images found" in error_msg or ("storyboard" in error_msg.lower() and storyboard_images_count == 0):
                print(f"⚠️  Storyboard logic failed: {error_msg}")
                print(f"📊 Phase 4: Falling back to old logic")
                result4_obj = generate_chunks_old.apply(args=[video_id, spec, animatic_urls, reference_urls, user_id])
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
        # Skip Phase 5 for Veo models (they generate native audio)
        video_model = spec.get('model')
        if not video_model:
            raise Exception("Model not specified in spec! Cannot determine if Phase 5 should be skipped.")
        model_has_native_audio = video_model in ['veo_fast', 'veo']
        
        if stitched_video_url and not model_has_native_audio:
            # Phase 5 starts at 90%, will complete at 100%
            update_progress(video_id, "refining", 90, current_phase="phase5_refine")
            
            # Run Phase 5 task synchronously
            # Pass user_id for new S3 path structure
            result5_obj = refine_video.apply(args=[video_id, stitched_video_url, spec, user_id])
            result5 = result5_obj.result
            
            # Extract music_url from Phase 5 output (even if combining failed)
            music_url = result5.get('output_data', {}).get('music_url')
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Check Phase 5 success
            if result5['status'] != "success":
                print(f"⚠️  Phase 5 failed: {result5.get('error_message', 'Unknown error')}")
                # Continue anyway - use stitched video as fallback
                refined_video_url = stitched_video_url
                
                # Update final status - Phase 5 failed, use stitched video
                db = SessionLocal()
                try:
                    video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                    if video:
                        video.status = VideoStatus.COMPLETE
                        video.progress = 100.0
                        video.current_phase = "phase4_chunks"  # Phase 4 was the last successful phase
                        video.cost_usd = total_cost
                        video.generation_time_seconds = generation_time
                        video.final_video_url = refined_video_url
                        if video.completed_at is None:
                            from datetime import datetime
                            video.completed_at = datetime.utcnow()
                        db.commit()
                finally:
                    db.close()
            else:
                # Update cost tracking
                total_cost += result5['cost_usd']
                update_cost(video_id, "phase5", result5['cost_usd'])
                print(f"💰 Phase 5 Cost: ${result5['cost_usd']:.4f} | Total: ${total_cost:.4f}")
                
                # Extract refined video URL from Phase 5
                refined_video_url = result5['output_data'].get('refined_video_url', stitched_video_url)
                
                # Store Phase 5 output in database and update final status
                db = SessionLocal()
                try:
                    video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                    if video:
                        if video.phase_outputs is None:
                            video.phase_outputs = {}
                        video.phase_outputs['phase5_refine'] = result5
                        video.refined_url = refined_video_url
                        video.final_video_url = refined_video_url  # Phase 5 output is the final video
                        video.progress = 100.0
                        video.current_phase = "phase5_refine"
                        video.status = VideoStatus.COMPLETE
                        video.cost_usd = total_cost
                        video.generation_time_seconds = generation_time
                        if video.completed_at is None:
                            from datetime import datetime
                            video.completed_at = datetime.utcnow()
                        # Mark JSON column as modified so SQLAlchemy detects the change
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(video, 'phase_outputs')
                        db.commit()
                finally:
                    db.close()
        elif model_has_native_audio:
            # Veo models have native audio - skip Phase 5 entirely
            print(f"🎵 Model '{video_model}' generates native audio - skipping Phase 5")
            refined_video_url = stitched_video_url
            music_url = None
            
            # Calculate generation time
            generation_time = time.time() - start_time
            
            # Update final status - Phase 5 was skipped, stitched video is final
            db = SessionLocal()
            try:
                video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                if video:
                    if video.phase_outputs is None:
                        video.phase_outputs = {}
                    # Don't store Phase 5 output since it was skipped
                    # The stitched video from Phase 4 is the final video (with native audio)
                    video.refined_url = refined_video_url
                    video.final_video_url = refined_video_url  # Stitched video IS the final video for Veo
                    # Update status and final metadata
                    video.progress = 100.0
                    video.current_phase = "phase4_chunks"  # Phase 4 was the last phase
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
        print(f"   - Phase 2 (Storyboard): ${result2['cost_usd']:.4f}")
        print(f"   - Phase 3 (References): DISABLED (using Phase 2 storyboard images)")
        print(f"   - Phase 4 (Chunks): ${result4['cost_usd']:.4f}")
        if 'result5' in locals() and result5.get('status') == 'success':
            print(f"   - Phase 5 (Refine): ${result5.get('cost_usd', 0):.4f}")
        elif model_has_native_audio:
            print(f"   - Phase 5 (Refine): Skipped (model '{video_model}' has native audio)")
        else:
            print(f"   - Phase 5 (Refine): Skipped (no stitched video)")
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
