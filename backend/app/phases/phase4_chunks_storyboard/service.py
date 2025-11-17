# Phase 4: Parallel Chunk Generation Service
import time
import json
from datetime import datetime
from typing import List, Dict
from celery import group
from app.phases.phase4_chunks_storyboard.chunk_generator import (
    generate_single_chunk_with_storyboard,
    build_chunk_specs_with_storyboard
)
from app.common.exceptions import PhaseException


class ChunkGenerationService:
    """Service for generating video chunks in parallel"""
    
    def __init__(self):
        """Initialize the service with cost tracking"""
        self.total_cost = 0.0
        self.beat_to_chunk_map = None
        self.chunk_to_beat_map = None  # Reverse mapping: chunk_idx -> beat_idx for all chunks
    
    def _should_use_last_frame(self, chunk_idx: int, spec: Dict) -> bool:
        """
        Determine if a chunk should use last-frame continuation.
        
        Only use last-frame if:
        1. Chunk does NOT start a new beat (not in beat_to_chunk_map)
        2. Previous chunk is part of the same beat (beat spans multiple chunks)
        
        Args:
            chunk_idx: Current chunk index
            spec: Video specification with beats
            
        Returns:
            True if should use last-frame continuation, False otherwise
        """
        if chunk_idx == 0:
            # Chunk 0 never uses last-frame (it starts a beat or uses storyboard)
            return False
        
        # If this chunk starts a beat, it uses storyboard image (no last-frame)
        if chunk_idx in self.beat_to_chunk_map:
            return False
        
        # Find which beat this chunk belongs to
        beats = spec.get('beats', [])
        if not self.chunk_to_beat_map:
            # Build reverse mapping: chunk_idx -> beat_idx for all chunks
            from app.phases.phase4_chunks_storyboard.model_config import get_default_model, get_model_config
            selected_model = spec.get('model', 'hailuo')
            try:
                model_config = get_model_config(selected_model)
            except Exception:
                model_config = get_default_model()
            actual_chunk_duration = model_config.get('actual_chunk_duration', 5.0)
            
            # Calculate which beat each chunk belongs to
            self.chunk_to_beat_map = {}
            current_time = 0.0
            for beat_idx, beat in enumerate(beats):
                beat_duration = beat.get('duration', 5.0)
                beat_start_chunk = int(current_time // actual_chunk_duration)
                beat_end_chunk = int((current_time + beat_duration) // actual_chunk_duration)
                
                # All chunks from beat_start_chunk to beat_end_chunk belong to this beat
                for chunk_idx_in_beat in range(beat_start_chunk, beat_end_chunk + 1):
                    self.chunk_to_beat_map[chunk_idx_in_beat] = beat_idx
                
                current_time += beat_duration
        
        # Check if current chunk and previous chunk are in the same beat
        current_beat = self.chunk_to_beat_map.get(chunk_idx)
        previous_beat = self.chunk_to_beat_map.get(chunk_idx - 1)
        
        # Use last-frame only if both chunks are in the same beat (beat spans multiple chunks)
        return current_beat is not None and current_beat == previous_beat
    
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
            
            # Build chunk specifications using storyboard logic
            print(f"🔨 Building chunk specifications for {video_id} (Storyboard Mode)...")
            chunk_specs, beat_to_chunk_map = build_chunk_specs_with_storyboard(
                video_id=video_id,
                spec=spec,
                reference_urls=reference_urls,
                user_id=user_id
            )
            self.beat_to_chunk_map = beat_to_chunk_map  # Store for retry logic
            num_chunks = len(chunk_specs)
            
            print(f"Generating {num_chunks} chunks in parallel...")
            
            # Generate chunks sequentially
            # Only chunks within the same beat (beat spans multiple chunks) use last-frame continuation
            # Chunks that start new beats use storyboard images
            # Chunks that are the only chunk in a beat are independent
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
                    
                    # Update previous_chunk_last_frame only if this chunk is part of a beat that spans multiple chunks
                    if self._should_use_last_frame(i, spec):
                        if i - 1 < len(last_frame_urls) and last_frame_urls[i - 1]:
                            chunk_spec.previous_chunk_last_frame = last_frame_urls[i - 1]
                            print(f"   🔄 Chunk {i}: Using last-frame continuation (same beat as previous chunk)")
                        else:
                            print(f"   ⚠️  Warning: Chunk {i} should use last-frame but previous chunk's last frame not available")
                    else:
                        # Chunk is independent (starts new beat or beat only needs one chunk)
                        chunk_spec.previous_chunk_last_frame = None
                        if i in self.beat_to_chunk_map:
                            print(f"   🎨 Chunk {i}: Using storyboard image (starts new beat)")
                        else:
                            print(f"   📸 Chunk {i}: Independent chunk (beat only needs one chunk)")
                    
                    # Generate chunk synchronously (using apply to get result immediately)
                    # Use storyboard-aware function
                    result = generate_single_chunk_with_storyboard.apply(
                        args=[chunk_spec.dict(), self.beat_to_chunk_map]
                    )
                    
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
                        # Only store last_frame_url if it will be used by next chunk
                        # (i.e., if next chunk is part of same beat)
                        if i + 1 < num_chunks and self._should_use_last_frame(i + 1, spec):
                            last_frame_urls.append(chunk_result.get('last_frame_url'))
                        else:
                            # Next chunk is independent, don't need to store last frame
                            last_frame_urls.append(None)
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
                retry_results = self._retry_failed_chunks(failed_chunks, last_frame_urls, spec)
                
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
    
    def _retry_failed_chunks(self, failed_chunks: List[tuple], last_frame_urls: List[str], spec: Dict) -> List[tuple]:
        """
        Retry failed chunks individually (not in parallel).
        Maintains temporal consistency by setting previous_chunk_last_frame only when needed.
        
        Args:
            failed_chunks: List of (chunk_index, ChunkSpec) tuples for failed chunks (must be sorted by index)
            last_frame_urls: List of last_frame_urls from successfully generated chunks (for temporal consistency)
            spec: Video specification with beats (needed to determine if last-frame should be used)
            
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
                    # Update previous_chunk_last_frame only if this chunk is part of a beat that spans multiple chunks
                    if self._should_use_last_frame(chunk_index, spec):
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
                            print(f"   🔄 Using previous chunk's last frame (same beat): {prev_frame_url[:60]}...")
                        else:
                            print(f"   ⚠️  Warning: Chunk {chunk_index} requires previous chunk's last frame, but it's not available")
                    else:
                        # Chunk is independent, don't use last-frame
                        chunk_spec.previous_chunk_last_frame = None
                        if chunk_index in self.beat_to_chunk_map:
                            print(f"   🎨 Chunk {chunk_index}: Using storyboard image (starts new beat)")
                        else:
                            print(f"   📸 Chunk {chunk_index}: Independent chunk (beat only needs one chunk)")
                    
                    # Generate chunk synchronously (using apply to get result immediately)
                    # Use storyboard-aware function
                    result = generate_single_chunk_with_storyboard.apply(
                        args=[chunk_spec.dict(), self.beat_to_chunk_map]
                    )
                    
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
                        # Only store last_frame_url if it will be used by next chunk
                        # (i.e., if next chunk is part of same beat)
                        # We need to determine the total number of chunks to check if there's a next chunk
                        from app.phases.phase4_chunks_storyboard.model_config import get_default_model, get_model_config
                        import math
                        selected_model = spec.get('model', 'hailuo')
                        try:
                            model_config = get_model_config(selected_model)
                        except Exception:
                            model_config = get_default_model()
                        actual_chunk_duration = model_config.get('actual_chunk_duration', 5.0)
                        duration = spec.get('duration', 30)
                        num_chunks = math.ceil(duration / actual_chunk_duration)
                        
                        if chunk_index + 1 < num_chunks and self._should_use_last_frame(chunk_index + 1, spec):
                            # Next chunk will need this last frame
                            if chunk_index < len(last_frame_urls):
                                last_frame_urls[chunk_index] = chunk_result.get('last_frame_url')
                            else:
                                while len(last_frame_urls) <= chunk_index:
                                    last_frame_urls.append(None)
                                last_frame_urls[chunk_index] = chunk_result.get('last_frame_url')
                        else:
                            # Next chunk is independent, don't store last frame
                            if chunk_index < len(last_frame_urls):
                                last_frame_urls[chunk_index] = None
                            else:
                                while len(last_frame_urls) <= chunk_index:
                                    last_frame_urls.append(None)
                                last_frame_urls[chunk_index] = None
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