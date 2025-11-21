# Phase 3: Chunk Generation Task
import time
import os
import tempfile
import logging
from datetime import datetime
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase3_chunks.stitcher import VideoStitcher
from app.common.exceptions import PhaseException
from app.orchestrator.progress import update_progress, update_cost
from app.database import SessionLocal
from app.common.models import VideoGeneration
from sqlalchemy.orm.attributes import flag_modified
from app.phases.phase3_chunks.schemas import ChunkSpec
from app.phases.phase3_chunks.chunk_generator import (
    generate_single_chunk_with_storyboard,
    generate_single_chunk_continuous,
    build_chunk_specs_with_storyboard
)
from langchain_core.runnables import RunnableParallel
from app.services.thumbnail import thumbnail_service
from app.services.s3 import s3_client

logger = logging.getLogger(__name__)


def generate_chunk_reference_image(chunk_spec: ChunkSpec, beat_to_chunk_map: dict) -> dict:
    """
    Generate chunk using storyboard image from Phase 2 (Reference Image Chunk).
    
    This is a helper function (NOT a Celery task) that will be called by LangChain
    RunnableParallel for parallel execution. It wraps the existing storyboard
    generation logic.
    
    Args:
        chunk_spec: ChunkSpec object for the chunk to generate
        beat_to_chunk_map: Dictionary mapping chunk indices → beat indices
        
    Returns:
        Dictionary with chunk_url, last_frame_url, chunk_num, and cost
        
    Raises:
        PhaseException: If generation fails
    """
    chunk_num = chunk_spec.chunk_num
    video_id = chunk_spec.video_id
    
    try:
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds
        print(f"🚀 [{timestamp}] [PARALLEL Phase 1] Starting reference image chunk {chunk_num} (starts beat)")
        
        # Call existing function directly (not a Celery task)
        # Convert ChunkSpec to dict for the function
        chunk_spec_dict = chunk_spec.dict()
        
        # Call the function directly
        result = generate_single_chunk_with_storyboard(
            chunk_spec_dict, 
            beat_to_chunk_map
        )
        
        elapsed = time.time() - start_time
        timestamp_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"✅ [{timestamp_end}] [PARALLEL Phase 1] Completed reference image chunk {chunk_num} in {elapsed:.1f}s")
        
        # Extract and return structured result
        return {
            'chunk_url': result['chunk_url'],
            'last_frame_url': result['last_frame_url'],
            'chunk_num': chunk_num,
            'cost': result['cost']
        }
        
    except Exception as e:
        timestamp_error = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"❌ [{timestamp_error}] [PARALLEL Phase 1] Failed reference image chunk {chunk_num}: {str(e)}")
        raise PhaseException(f"Failed to generate reference image chunk {chunk_num}: {str(e)}")


def generate_chunk_continuous(chunk_spec: ChunkSpec, ref_result: dict) -> dict:
    """
    Generate chunk using last frame from reference chunk (Continuous Chunk).
    
    This is a helper function (NOT a Celery task) that will be called by LangChain
    RunnableParallel for parallel execution. It wraps the existing continuous
    generation logic.
    
    Args:
        chunk_spec: ChunkSpec object for the chunk to generate
        ref_result: Result dict from reference chunk containing last_frame_url
        
    Returns:
        Dictionary with chunk_url, chunk_num, and cost
        
    Raises:
        PhaseException: If generation fails or previous frame is missing
    """
    chunk_num = chunk_spec.chunk_num
    video_id = chunk_spec.video_id
    
    try:
        start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds
        ref_chunk_num = ref_result.get('chunk_num', 'unknown')
        print(f"🚀 [{timestamp}] [PARALLEL Phase 2] Starting continuous chunk {chunk_num} (uses last frame from chunk {ref_chunk_num})")
        
        # Extract last_frame_url from reference chunk result
        last_frame_url = ref_result.get('last_frame_url')
        if not last_frame_url:
            raise PhaseException(f"Reference chunk result missing last_frame_url for chunk {chunk_num}")
        
        # Update chunk_spec with last frame from reference chunk
        chunk_spec.previous_chunk_last_frame = last_frame_url
        
        # Call existing continuous generation function directly (not a Celery task)
        result = generate_single_chunk_continuous(chunk_spec)
        
        elapsed = time.time() - start_time
        timestamp_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"✅ [{timestamp_end}] [PARALLEL Phase 2] Completed continuous chunk {chunk_num} in {elapsed:.1f}s")
        
        # Return structured result (no last_frame_url needed for continuous chunks)
        return {
            'chunk_url': result['chunk_url'],
            'chunk_num': chunk_num,
            'cost': result['cost']
        }
        
    except Exception as e:
        timestamp_error = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"❌ [{timestamp_error}] [PARALLEL Phase 2] Failed continuous chunk {chunk_num}: {str(e)}")
        raise PhaseException(f"Failed to generate continuous chunk {chunk_num}: {str(e)}")


def generate_chunks_parallel(video_id: str, spec: dict, reference_urls: dict, user_id: str) -> dict:
    """
    Generate chunks in parallel using LangChain RunnableParallel (two-phase execution).
    
    Phase 1: All reference image chunks run in parallel
    Phase 2: All continuous chunks run in parallel (after Phase 1 completes)
    
    Args:
        video_id: Unique video generation ID
        spec: Video specification from Phase 1 (contains beats with image_url from Phase 2)
        reference_urls: Dictionary with style_guide_url and product_reference_url from Phase 3
        user_id: User ID for organizing outputs in S3
        
    Returns:
        Dictionary with chunk_urls (list) and total_cost (float)
        
    Raises:
        PhaseException: If generation fails or chunk separation fails
    """
    try:
        # Build chunk specs and beat_to_chunk_map
        chunk_specs, beat_to_chunk_map = build_chunk_specs_with_storyboard(
            video_id, spec, reference_urls, user_id
        )
        
        print(f"   📊 Parallel chunk generation: {len(chunk_specs)} chunks total")
        print(f"   🗺️  Beat-to-chunk mapping: {beat_to_chunk_map}")
        
        # Separate reference and continuous chunks
        ref_chunks = []  # List of (chunk_spec, chunk_num) tuples
        cont_chunks = []  # List of (chunk_spec, ref_chunk_num) tuples
        
        for i, chunk_spec in enumerate(chunk_specs):
            if i in beat_to_chunk_map:
                # Reference image chunk (starts a beat)
                ref_chunks.append((chunk_spec, i))
            else:
                # Continuous chunk - find its reference chunk (look backwards)
                # Edge case: Chunk 0 cannot be continuous (must start a beat)
                if i == 0:
                    raise PhaseException(f"Chunk 0 is orphaned (must start a beat, not be continuous)")
                
                ref_chunk_num = None
                for j in range(i - 1, -1, -1):
                    if j in beat_to_chunk_map:
                        ref_chunk_num = j
                        break
                
                if ref_chunk_num is None:
                    raise PhaseException(f"Chunk {i} is orphaned (no reference chunk found)")
                
                cont_chunks.append((chunk_spec, ref_chunk_num))
        
        print(f"   📋 Chunk separation: {len(ref_chunks)} reference chunks, {len(cont_chunks)} continuous chunks")
        
        # Phase 1: Generate all reference image chunks in parallel
        ref_results_by_num = {}
        if ref_chunks:
            phase1_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            ref_chunk_nums = [cn for _, cn in ref_chunks]
            print(f"   🚀 [{phase1_start}] Phase 1 START: Generating {len(ref_chunks)} reference image chunks in parallel")
            print(f"      Chunks starting together: {ref_chunk_nums}")
            
            # Build RunnableParallel dict with proper closure capture
            ref_parallel_dict = {}
            for chunk_spec, chunk_num in ref_chunks:
                # Create closure to capture chunk_spec and chunk_num properly
                def make_ref_generator(cs, cn, btm):
                    return lambda x: generate_chunk_reference_image(cs, btm)
                
                ref_parallel_dict[f'chunk_{chunk_num}'] = make_ref_generator(chunk_spec, chunk_num, beat_to_chunk_map)
            
            ref_parallel = RunnableParallel(ref_parallel_dict)
            
            # Invoke parallel execution (blocks until all complete)
            ref_results = ref_parallel.invoke({})
            
            # Convert results to dict keyed by chunk_num
            for key, result in ref_results.items():
                chunk_num = int(key.split('_')[1])
                ref_results_by_num[chunk_num] = result
            
            phase1_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"   ✅ [{phase1_end}] Phase 1 COMPLETE: {len(ref_results_by_num)} reference chunks generated")
            # Update progress: 60% after Phase 1 completes
            update_progress(video_id, "generating_chunks", 60, current_phase="phase3_chunks")
        else:
            print(f"   ⚠️  Phase 1 skipped: No reference chunks")
        
        # Phase 2: Generate all continuous chunks in parallel
        cont_results_by_num = {}
        if cont_chunks:
            phase2_start = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            cont_chunk_nums = [cs.chunk_num for cs, _ in cont_chunks]
            print(f"   🚀 [{phase2_start}] Phase 2 START: Generating {len(cont_chunks)} continuous chunks in parallel")
            print(f"      Chunks starting together: {cont_chunk_nums}")
            
            # Build RunnableParallel dict with proper closure capture
            cont_parallel_dict = {}
            for chunk_spec, ref_chunk_num in cont_chunks:
                # Create closure to capture chunk_spec and ref_chunk_num properly
                # Capture ref_results_by_num at the time of closure creation
                def make_cont_generator(cs, ref_num, ref_results):
                    return lambda x: generate_chunk_continuous(cs, ref_results[ref_num])
                
                cont_parallel_dict[f'chunk_{chunk_spec.chunk_num}'] = make_cont_generator(
                    chunk_spec, ref_chunk_num, ref_results_by_num
                )
            
            cont_parallel = RunnableParallel(cont_parallel_dict)
            
            # Invoke parallel execution (blocks until all complete)
            cont_results = cont_parallel.invoke({})
            
            # Convert results to dict keyed by chunk_num
            for key, result in cont_results.items():
                chunk_num = int(key.split('_')[1])
                cont_results_by_num[chunk_num] = result
            
            phase2_end = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"   ✅ [{phase2_end}] Phase 2 COMPLETE: {len(cont_results_by_num)} continuous chunks generated")
        else:
            print(f"   ⚠️  Phase 2 skipped: No continuous chunks")
        
        # Update progress: 70% after both phases complete
        update_progress(video_id, "generating_chunks", 70, current_phase="phase3_chunks")
        
        # Merge and sort all chunks by chunk_num
        all_chunks = []
        all_chunks.extend(ref_results_by_num.values())
        all_chunks.extend(cont_results_by_num.values())
        all_chunks.sort(key=lambda x: x['chunk_num'])
        
        # Validate chunk ordering (no gaps in chunk_num sequence)
        expected_chunk_nums = set(range(len(chunk_specs)))
        actual_chunk_nums = set(chunk['chunk_num'] for chunk in all_chunks)
        if expected_chunk_nums != actual_chunk_nums:
            missing = expected_chunk_nums - actual_chunk_nums
            extra = actual_chunk_nums - expected_chunk_nums
            error_msg = f"Chunk ordering validation failed: expected {len(chunk_specs)} chunks"
            if missing:
                error_msg += f", missing chunks: {sorted(missing)}"
            if extra:
                error_msg += f", extra chunks: {sorted(extra)}"
            raise PhaseException(error_msg)
        
        # Extract URLs and calculate total cost
        chunk_urls = [chunk['chunk_url'] for chunk in all_chunks]
        total_cost = sum(chunk['cost'] for chunk in all_chunks)
        
        print(f"   ✅ Parallel generation complete: {len(chunk_urls)} chunks, ${total_cost:.4f} total cost")
        
        return {
            'chunk_urls': chunk_urls,
            'total_cost': total_cost
        }
        
    except PhaseException:
        # Re-raise PhaseException as-is
        raise
    except Exception as e:
        raise PhaseException(f"Failed to generate chunks in parallel: {str(e)}")


@celery_app.task(bind=True, name="app.phases.phase3_chunks.task.generate_chunks")
def generate_chunks(
    self,
    phase2_output: dict,
    user_id: str = None,
    model: str = 'hailuo_fast'
) -> dict:
    """
    Phase 3: Generate video chunks in parallel and stitch them together.
    
    Args:
        self: Celery task instance
        phase2_output: PhaseOutput dict from Phase 2 (contains spec with storyboard images)
        user_id: User ID for organizing outputs in S3 (required for new structure)
        model: Video generation model to use (default: 'hailuo_fast')
        
    Returns:
        PhaseOutput dictionary with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    # Check if Phase 2 succeeded
    if phase2_output.get('status') != 'success':
        error_msg = phase2_output.get('error_message', 'Phase 2 failed')
        video_id = phase2_output.get('video_id', 'unknown')
        
        # Update progress
        update_progress(video_id, "failed", 0, error_message=f"Phase 2 failed: {error_msg}", current_phase="phase3_chunks")
        
        # Return failed PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=0.0,
            error_message=f"Phase 2 failed: {error_msg}"
        ).dict()
    
    # Extract data from Phase 2 output
    # Phase 2 returns spec with storyboard images
    video_id = phase2_output.get('video_id', 'unknown')
    phase2_data = phase2_output.get('output_data', {})
    spec = phase2_data.get('spec')
    reference_urls = {
        'style_guide_url': phase2_data.get('style_guide_url'),
        'product_reference_url': phase2_data.get('product_reference_url')
    }
    
    if not spec:
        raise PhaseException("Spec not found in Phase 3 output")
    
    # Add model to spec for chunk generation
    spec['model'] = model
    
    # Set empty animatic_urls (Phase 2 animatic is disabled)
    animatic_urls = []
    
    try:
        # Update progress at start
        update_progress(video_id, "generating_chunks", 50, current_phase="phase3_chunks")
        # Initialize stitcher
        stitcher = VideoStitcher()
        
        # Generate all chunks in parallel using LangChain RunnableParallel
        print(f"🚀 Phase 3 (Chunks - Storyboard Mode, Parallel) starting for video {video_id}")
        chunk_results = generate_chunks_parallel(
            video_id=video_id,
            spec=spec,
            reference_urls=reference_urls,
            user_id=user_id
        )
        
        chunk_urls = chunk_results['chunk_urls']
        total_cost = chunk_results['total_cost']
        
        # Progress already updated to 70% in generate_chunks_parallel()
        
        # Generate thumbnail from first chunk (non-blocking - don't fail Phase 3 if this fails)
        if chunk_urls and len(chunk_urls) > 0:
            try:
                first_chunk_url = chunk_urls[0]
                logger.info(f"Generating thumbnail from first chunk: {first_chunk_url}")
                
                # Download first chunk from S3
                first_chunk_path = None
                try:
                    # Extract S3 key from URL or download directly
                    if first_chunk_url.startswith('s3://'):
                        s3_key = first_chunk_url.replace(f's3://{s3_client.bucket}/', '')
                        # Download from S3
                        first_chunk_path = s3_client.download_temp(s3_key)
                    else:
                        # For presigned URLs, download directly
                        import requests
                        first_chunk_path = tempfile.mktemp(suffix='.mp4')
                        response = requests.get(first_chunk_url, stream=True, timeout=60)
                        response.raise_for_status()
                        with open(first_chunk_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                f.write(chunk)
                    
                    if first_chunk_path and os.path.exists(first_chunk_path):
                        # Generate thumbnail
                        thumbnail_url = thumbnail_service.generate_video_thumbnail(
                            video_path=first_chunk_path,
                            user_id=user_id,
                            video_id=video_id
                        )
                        
                        # Update database with thumbnail_url
                        db = SessionLocal()
                        try:
                            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                            if video:
                                video.thumbnail_url = thumbnail_url
                                flag_modified(video, 'thumbnail_url')
                                db.commit()
                                logger.info(f"Updated video {video_id} with thumbnail_url: {thumbnail_url}")
                        except Exception as db_error:
                            logger.warning(f"Failed to update database with thumbnail_url: {str(db_error)}")
                            db.rollback()
                        finally:
                            db.close()
                        
                        # Cleanup downloaded chunk
                        if os.path.exists(first_chunk_path):
                            try:
                                os.remove(first_chunk_path)
                            except Exception:
                                pass
                    else:
                        logger.warning(f"First chunk file not found at {first_chunk_path}")
                        
                except Exception as download_error:
                    logger.warning(f"Failed to download first chunk for thumbnail: {str(download_error)}")
                    
            except Exception as thumbnail_error:
                # Don't fail Phase 3 if thumbnail generation fails
                logger.warning(f"Thumbnail generation failed (non-blocking): {str(thumbnail_error)}", exc_info=True)
        
        # Now proceed to stitching
        
        # Stitch chunks together with transitions
        print(f"Stitching {len(chunk_urls)} chunks with transitions...")
        transitions = spec.get('transitions', [])
        stitched_video_url = stitcher.stitch_with_transitions(
            video_id=video_id,
            chunk_urls=chunk_urls,
            transitions=transitions,
            user_id=user_id
        )
        
        # Update progress after stitching
        update_progress(
            video_id,
            "generating_chunks",
            75,  # 75% = stitching complete
            current_phase="phase3_chunks"
        )
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create success output
        # Pass through spec for Phase 4 (needs it for music generation)
        output = PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="success",
            output_data={
                'stitched_video_url': stitched_video_url,
                'chunk_urls': chunk_urls,
                'total_cost': total_cost,
                'spec': spec  # Pass through spec for Phase 4
            },
            cost_usd=total_cost,
            duration_seconds=duration_seconds,
            error_message=None
        )
        
        # Update cost tracking
        update_cost(video_id, "phase3", total_cost)
        
        # Update progress
        update_progress(
            video_id,
            "generating_chunks",
            90,
            current_phase="phase3_chunks",
            total_cost=total_cost
        )
        
        # Store Phase 3 output in database
        db = SessionLocal()
        try:
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if video:
                if video.phase_outputs is None:
                    video.phase_outputs = {}
                video.phase_outputs['phase3_chunks'] = output.dict()
                video.stitched_url = stitched_video_url
                video.chunk_urls = chunk_urls
                video.final_video_url = stitched_video_url
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        print(f"✅ Phase 3 (Chunks) completed successfully for video {video_id}")
        print(f"   - Generated chunks: {len(chunk_urls)}")
        print(f"   - Stitched video: {stitched_video_url}")
        print(f"   - Total cost: ${total_cost:.4f}")
        print(f"   - Duration: {duration_seconds:.2f}s")
        
        return output.dict()
        
    except PhaseException as e:
        # Phase-specific exception
        duration_seconds = time.time() - start_time
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase3_chunks"
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
                    "phase": "phase3_chunks",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": str(e)
                }
                video.phase_outputs['phase3_chunks'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        print(f"❌ Phase 3 (Chunks) failed for video {video_id}: {str(e)}")
        return output.dict()
        
    except Exception as e:
        # Unexpected exception
        duration_seconds = time.time() - start_time
        
        # Update progress with failure
        update_progress(
            video_id,
            "failed",
            0,
            error_message=str(e),
            current_phase="phase3_chunks"
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
                    "phase": "phase3_chunks",
                    "status": "failed",
                    "output_data": {},
                    "cost_usd": 0.0,
                    "duration_seconds": duration_seconds,
                    "error_message": f"An unexpected error occurred: {str(e)}"
                }
                video.phase_outputs['phase3_chunks'] = output_dict
                flag_modified(video, 'phase_outputs')
                db.commit()
        finally:
            db.close()
        
        output = PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=f"An unexpected error occurred: {str(e)}"
        )
        
        print(f"❌ Phase 3 (Chunks) unexpected error for video {video_id}: {str(e)}")
        return output.dict()