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


@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: list = None):
    """
    Main orchestration task - chains phases sequentially.
    Currently implements Phase 1 (Validate) -> Phase 4 (Chunks).
    Phase 2 (Animatic) and Phase 3 (References) are temporarily disabled for MVP.
    
    Args:
        video_id: Unique video generation ID
        prompt: User's video description
        assets: Optional list of uploaded assets
        
    Returns:
        Result dictionary with video_id, status, spec, and cost
        
    Raises:
        Exception: If any phase fails
    """
    if assets is None:
        assets = []
    
    start_time = time.time()
    total_cost = 0.0
    
    try:
        # ============ PHASE 1: VALIDATE & EXTRACT ============
        update_progress(video_id, "validating", 10, current_phase="phase1_validate")
        
        # Run Phase 1 task synchronously (using apply instead of delay().get())
        result1_obj = validate_prompt.apply(args=[video_id, prompt, assets])
        result1 = result1_obj.result  # Get actual result from EagerResult
        
        # Check Phase 1 success
        if result1['status'] != "success":
            raise Exception(f"Phase 1 failed: {result1.get('error_message', 'Unknown error')}")
        
        # Update cost tracking
        total_cost += result1['cost_usd']
        update_cost(video_id, "phase1", result1['cost_usd'])
        print(f"💰 Phase 1 Cost: ${result1['cost_usd']:.4f} | Total: ${total_cost:.4f}")
        
        # Extract spec from Phase 1
        spec = result1['output_data']['spec']
        
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
        # Phase 2 & 3 temporarily disabled for MVP
        # update_progress(video_id, "generating_references", 30, current_phase="phase3_references")
        # 
        # # Run Phase 3 task synchronously (using apply instead of delay().get())
        # result3_obj = generate_references.apply(args=[video_id, spec])
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
        #         # Mark JSON column as modified so SQLAlchemy detects the change
        #         from sqlalchemy.orm.attributes import flag_modified
        #         flag_modified(video, 'phase_outputs')
        #         db.commit()
        # finally:
        #     db.close()
        # 
        # # Update progress
        # update_progress(
        #     video_id,
        #     "generating_references",
        #     40,
        #     current_phase="phase3_references",
        #     total_cost=total_cost
        # )
        
        # Set empty reference_urls for Phase 4 (since Phase 3 is disabled)
        reference_urls = {}
        
        # ============ PHASE 4: GENERATE VIDEO CHUNKS ============
        # Progress adjusted: Phase 1 ends at 20%, Phase 4 starts at 30% (skipping Phase 2 & 3)
        update_progress(video_id, "generating_chunks", 30, current_phase="phase4_chunks")
        
        # Run Phase 4 task synchronously
        # Phase 2 & 3 temporarily disabled for MVP - passing empty lists
        result4_obj = generate_chunks.apply(args=[video_id, spec, [], {}])
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
                # Mark JSON column as modified so SQLAlchemy detects the change
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        # Update progress
        update_progress(
            video_id,
            "generating_chunks",
            70,
            current_phase="phase4_chunks",
            total_cost=total_cost
        )
        
        # ============ PHASE 5: REFINE & ENHANCE ============
        if stitched_video_url:
            update_progress(video_id, "refining", 80, current_phase="phase5_refine")
            
            # Run Phase 5 task synchronously
            result5_obj = refine_video.apply(args=[video_id, stitched_video_url, spec])
            result5 = result5_obj.result
            
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
                
                # Store Phase 5 output in database
                db = SessionLocal()
                try:
                    video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                    if video:
                        if video.phase_outputs is None:
                            video.phase_outputs = {}
                        video.phase_outputs['phase5_refine'] = result5
                        video.refined_url = refined_video_url
                        flag_modified(video, 'phase_outputs')
                        db.commit()
                finally:
                    db.close()
        else:
            refined_video_url = stitched_video_url
        
        # Calculate generation time
        generation_time = time.time() - start_time
        
        # Mark as complete
        # Update final status in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                video.status = VideoStatus.COMPLETE
                video.progress = 100.0
                video.current_phase = "phase5_refine" if stitched_video_url else "phase4_chunks"
                video.cost_usd = total_cost
                video.generation_time_seconds = generation_time
                video.final_video_url = refined_video_url  # Use refined video if available, else stitched
                if video.completed_at is None:
                    from datetime import datetime
                    video.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
        
        # Also call update_progress for consistency
        update_progress(
            video_id,
            "complete",
            100,
            current_phase="phase4_chunks",
            total_cost=total_cost,
            generation_time=generation_time
        )
        
        # Print final cost summary
        print("="*70)
        print(f"✅ VIDEO GENERATION COMPLETE: {video_id}")
        print("="*70)
        print(f"💰 TOTAL COST: ${total_cost:.4f} USD")
        print(f"   - Phase 1 (Validate): ${result1['cost_usd']:.4f}")
        # Phase 2 & 3 temporarily disabled for MVP
        print(f"   - Phase 4 (Chunks): ${result4['cost_usd']:.4f}")
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
