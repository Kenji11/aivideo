# Phase 4: Parallel Chunk Generation Service
import time
import json
from datetime import datetime
from typing import List, Dict
from celery import group
from app.phases.phase4_chunks.chunk_generator import generate_single_chunk, build_chunk_specs
from app.common.exceptions import PhaseException


class ChunkGenerationService:
    """Service for generating video chunks in parallel"""
    
    def __init__(self):
        """Initialize the service with cost tracking"""
        self.total_cost = 0.0
    
    def generate_all_chunks(
        self,
        video_id: str,
        spec: Dict,
        animatic_urls: List[str],
        reference_urls: Dict,
        user_id: str = None
    ) -> Dict:
        """
        Generate all video chunks in parallel using Celery group.
        
        Args:
            video_id: Unique video generation ID
            spec: Video specification from Phase 1
            animatic_urls: List of animatic frame S3 URLs from Phase 2
            reference_urls: Dictionary with style_guide_url and product_reference_url from Phase 3
            user_id: User ID for organizing outputs in S3 (required for new structure)
            
        Returns:
            Dictionary with:
                - chunk_urls: List of S3 URLs for generated chunks
                - last_frame_urls: List of S3 URLs for last frames (for temporal consistency)
                - total_cost: Total cost of chunk generation
                
        Raises:
            PhaseException: If chunk generation fails
        """
        try:
            # ============ INPUT LOGGING ============
            start_time = time.time()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Log summary
            num_beats = len(spec.get('beats', []))
            num_animatic_urls = len(animatic_urls) if animatic_urls else 0
            has_style_guide = bool(reference_urls and reference_urls.get('style_guide_url'))
            has_product_ref = bool(reference_urls and reference_urls.get('product_reference_url'))
            
            print("="*70)
            print(f"📋 [{timestamp}] Phase 4 Input Summary")
            print("="*70)
            print(f"   Video ID: {video_id}")
            print(f"   Duration: {spec.get('duration', 0)}s")
            print(f"   Beats: {num_beats}")
            print(f"   Animatic URLs: {num_animatic_urls}")
            print(f"   Style Guide: {'✅' if has_style_guide else '❌'}")
            print(f"   Product Reference: {'✅' if has_product_ref else '❌'}")
            print("="*70)
            
            # Log full details
            print(f"📄 [{timestamp}] Full Input Details")
            print(f"   Spec: {json.dumps(spec, indent=2, default=str)}")
            print(f"   Animatic URLs: {json.dumps(animatic_urls, indent=2) if animatic_urls else '[]'}")
            print(f"   Reference URLs: {json.dumps(reference_urls, indent=2) if reference_urls else '{}'}")
            print("="*70)
            
            # Build chunk specifications
            print(f"🔨 Building chunk specifications for {video_id}...")
            chunk_specs = build_chunk_specs(video_id, spec, animatic_urls, reference_urls, user_id)
            num_chunks = len(chunk_specs)
            
            print(f"Generating {num_chunks} chunks in parallel...")
            
            # Generate chunks sequentially for now to ensure temporal consistency
            # Chunk 0 can be generated immediately, but chunks 1+ need previous chunk's last frame
            # TODO: Optimize to generate in batches (chunk 0 first, then 1+ in parallel)
            chunk_urls = []
            last_frame_urls = []
            failed_chunks = []
            
            for i, chunk_spec in enumerate(chunk_specs):
                try:
                    print(f"Generating chunk {i+1}/{num_chunks}...")
                    
                    # Update progress: Phase 4 starts at 50%, ends at 70%
                    # Each chunk adds (20% / num_chunks) to progress
                    from app.orchestrator.progress import update_progress
                    chunk_progress = 50 + ((i + 1) / num_chunks) * 20
                    update_progress(
                        video_id,
                        "generating_chunks",
                        chunk_progress,
                        current_phase="phase4_chunks"
                    )
                    
                    # Update previous_chunk_last_frame if available
                    if i > 0 and i - 1 < len(last_frame_urls) and last_frame_urls[i - 1]:
                        chunk_spec.previous_chunk_last_frame = last_frame_urls[i - 1]
                    
                    # Generate chunk synchronously (using apply to get result immediately)
                    result = generate_single_chunk.apply(args=[chunk_spec.dict()])
                    
                    # Accessing result.result may raise an exception if the task failed
                    try:
                        chunk_result = result.result
                    except Exception as e:
                        # Task raised an exception - add to failed chunks
                        failed_chunks.append((i, chunk_spec))
                        error_type = type(e).__name__
                        print(f"   ❌ Chunk {i+1} task exception ({error_type}): {str(e)}")
                        continue  # Skip to next chunk
                    
                    if isinstance(chunk_result, dict) and 'chunk_url' in chunk_result:
                        chunk_urls.append(chunk_result['chunk_url'])
                        last_frame_urls.append(chunk_result.get('last_frame_url'))
                        # Use cost from result (calculated using model config in chunk_generator)
                        self.total_cost += chunk_result.get('cost', 0.0)
                        print(f"   ✅ Chunk {i+1}/{num_chunks} generated successfully ({len(chunk_urls)}/{num_chunks} complete)")
                    else:
                        failed_chunks.append((i, chunk_spec))
                        print(f"   ❌ Chunk {i+1} failed: {chunk_result}")
                except Exception as e:
                    # Catch any other exceptions (e.g., from apply() itself)
                    failed_chunks.append((i, chunk_spec))
                    error_type = type(e).__name__
                    print(f"   ❌ Chunk {i+1} exception ({error_type}): {str(e)}")
            
            # Retry failed chunks (must be in order to maintain last_frame dependencies)
            if failed_chunks:
                print(f"Retrying {len(failed_chunks)} failed chunks...")
                # Sort by chunk index to retry in order
                failed_chunks.sort(key=lambda x: x[0])
                retry_results = self._retry_failed_chunks(failed_chunks, last_frame_urls)
                
                # Add retry results (maintain order)
                for i, retry_result in retry_results:
                    if isinstance(retry_result, dict) and 'chunk_url' in retry_result:
                        # Insert at correct position (chunks are in order)
                        while len(chunk_urls) <= i:
                            chunk_urls.append(None)
                            last_frame_urls.append(None)
                        chunk_urls[i] = retry_result['chunk_url']
                        last_frame_urls[i] = retry_result.get('last_frame_url')
                        # Use cost from result (calculated using model config in chunk_generator)
                        self.total_cost += retry_result.get('cost', 0.0)
                    else:
                        raise PhaseException(f"Chunk {i} failed after retry: {retry_result}")
            
            # Ensure chunks are in correct order (they are already in order from sequential execution)
            total_time = time.time() - start_time
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # ============ SUCCESS LOGGING ============
            print("="*70)
            print(f"✅ [{timestamp}] Phase 4 Complete")
            print("="*70)
            print(f"   Total Chunks Generated: {len(chunk_urls)}/{num_chunks}")
            print(f"   Total Cost: ${self.total_cost:.4f}")
            print(f"   Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
            print(f"   Chunk URLs:")
            for i, url in enumerate(chunk_urls):
                print(f"      [{i+1}] {url[:80]}...")
            print("="*70)
            
            return {
                'chunk_urls': chunk_urls,
                'last_frame_urls': last_frame_urls,
                'total_cost': self.total_cost
            }
            
        except Exception as e:
            raise PhaseException(f"Failed to generate chunks: {str(e)}")
    
    def _retry_failed_chunks(self, failed_chunks: List[tuple], last_frame_urls: List[str]) -> List[tuple]:
        """
        Retry failed chunks individually (not in parallel).
        Maintains temporal consistency by setting previous_chunk_last_frame.
        
        Args:
            failed_chunks: List of (chunk_index, ChunkSpec) tuples for failed chunks (must be sorted by index)
            last_frame_urls: List of last_frame_urls from successfully generated chunks (for temporal consistency)
            
        Returns:
            List of (chunk_index, result) tuples
        """
        retry_results = []
        max_retries = 2
        
        for chunk_index, chunk_spec in failed_chunks:
            retry_count = 0
            success = False
            last_error = None
            
            while retry_count < max_retries and not success:
                retry_count += 1
                print(f"🔄 Retrying chunk {chunk_index} (attempt {retry_count}/{max_retries})...")
                
                try:
                    # Update previous_chunk_last_frame if this chunk needs it
                    if chunk_index > 0:
                        # Find previous chunk's last frame (from successful chunks or retried chunks)
                        prev_frame_url = None
                        if chunk_index - 1 < len(last_frame_urls):
                            prev_frame_url = last_frame_urls[chunk_index - 1]
                        else:
                            # Check if previous chunk was retried successfully
                            for retry_idx, retry_result in retry_results:
                                if retry_idx == chunk_index - 1 and isinstance(retry_result, dict):
                                    prev_frame_url = retry_result.get('last_frame_url')
                                    break
                        
                        if prev_frame_url:
                            chunk_spec.previous_chunk_last_frame = prev_frame_url
                            print(f"   Using previous chunk's last frame: {prev_frame_url[:60]}...")
                        else:
                            print(f"   ⚠️  Warning: Chunk {chunk_index} requires previous chunk's last frame, but it's not available")
                    
                    # Generate chunk synchronously (using apply to get result immediately)
                    result = generate_single_chunk.apply(args=[chunk_spec.dict()])
                    
                    # Accessing result.result may raise an exception if the task failed
                    try:
                        chunk_result = result.result
                    except Exception as e:
                        # Task raised an exception - capture it
                        error_msg = str(e)
                        error_type = type(e).__name__
                        print(f"Chunk {chunk_index} retry {retry_count} task exception ({error_type}): {error_msg}")
                        last_error = error_msg
                        continue  # Skip to next retry attempt
                    
                    if isinstance(chunk_result, dict) and 'chunk_url' in chunk_result:
                        retry_results.append((chunk_index, chunk_result))
                        success = True
                        print(f"   ✅ Chunk {chunk_index} retry {retry_count} succeeded!")
                        # Update last_frame_urls for future chunks
                        if chunk_index < len(last_frame_urls):
                            last_frame_urls[chunk_index] = chunk_result.get('last_frame_url')
                        else:
                            while len(last_frame_urls) <= chunk_index:
                                last_frame_urls.append(None)
                            last_frame_urls[chunk_index] = chunk_result.get('last_frame_url')
                    else:
                        # Task completed but returned invalid result
                        error_msg = chunk_result.get('error', str(chunk_result)) if isinstance(chunk_result, dict) else str(chunk_result)
                        print(f"   ❌ Chunk {chunk_index} retry {retry_count} failed: {error_msg}")
                        last_error = error_msg
                except Exception as e:
                    # Catch any other exceptions (e.g., from apply() itself)
                    import traceback
                    error_details = traceback.format_exc()
                    error_msg = str(e)
                    error_type = type(e).__name__
                    print(f"   ❌ Chunk {chunk_index} retry {retry_count} exception:")
                    print(f"      Error type: {error_type}")
                    print(f"      Error message: {error_msg}")
                    print(f"      Full traceback:")
                    for line in error_details.split('\n')[-10:]:  # Last 10 lines
                        if line.strip():
                            print(f"         {line}")
                    last_error = error_msg
                
                if not success and retry_count < max_retries:
                    print(f"   ⏳ Waiting 2 seconds before next retry...")
                    time.sleep(2)  # Brief delay before retry
            
            if not success:
                error_detail = last_error if last_error else 'Unknown error'
                print(f"   ❌ Chunk {chunk_index} failed after {max_retries} retries - giving up")
                retry_results.append((chunk_index, {'error': f'Failed after {max_retries} retries: {error_detail}'}))
        
        return retry_results