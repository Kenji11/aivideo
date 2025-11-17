# Phase 4 Storyboard: Chunk Generation with Storyboard Images (TDD v2.0)
import os
import tempfile
import subprocess
import requests
import time
import math
from datetime import datetime
from typing import Optional, List, Dict, Tuple

from app.orchestrator.celery_app import celery_app
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.phases.phase4_chunks_storyboard.schemas import ChunkSpec
from app.phases.phase4_chunks_storyboard.model_config import get_default_model, get_model_config
from app.common.constants import get_video_s3_key
from app.common.exceptions import PhaseException


def extract_last_frame(video_path: str, output_path: Optional[str] = None) -> str:
    """
    Extract the last frame from a video using FFmpeg.
    
    Args:
        video_path: Path to input video file
        output_path: Optional output path (if None, creates temp file)
        
    Returns:
        Path to extracted frame image (PNG)
        
    Raises:
        PhaseException: If FFmpeg extraction fails
    """
    if output_path is None:
        output_path = tempfile.mktemp(suffix='.png')
    
    try:
        # Get total frame count dynamically
        probe_cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-count_packets', '-show_entries', 'stream=nb_read_packets',
            '-of', 'csv=p=0', video_path
        ]
        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True, timeout=10)
            frame_count = int(result.stdout.strip())
            last_frame_num = max(0, frame_count - 1)
        except (subprocess.CalledProcessError, ValueError, subprocess.TimeoutExpired):
            # Fallback: use seek to end and extract last frame
            last_frame_num = None
        
        # Use FFmpeg to extract last frame
        if last_frame_num is not None:
            # Extract specific frame number
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vf', f'select=eq(n\\,{last_frame_num})',
                '-vframes', '1',
                '-y',  # Overwrite output file
                output_path
            ]
        else:
            # Fallback: use -sseof to seek from end and extract last frame
            cmd = [
                'ffmpeg',
                '-sseof', '-0.1',  # Seek to 0.1 seconds before end
                '-i', video_path,
                '-vframes', '1',
                '-y',
                output_path
            ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not os.path.exists(output_path):
            raise PhaseException(f"FFmpeg completed but output file not found: {output_path}")
        
        return output_path
        
    except subprocess.CalledProcessError as e:
        raise PhaseException(f"FFmpeg failed to extract last frame: {e.stderr}")
    except Exception as e:
        raise PhaseException(f"Failed to extract last frame: {str(e)}")


def calculate_beat_to_chunk_mapping(
    beats: List[Dict],
    actual_chunk_duration: float
) -> Dict[int, int]:
    """
    Calculate which chunks start at beat boundaries.
    
    Maps chunk indices to beat indices for chunks that start a new beat.
    Uses actual beat['start'] values from Phase 1 to ensure accuracy.
    
    Example: 3 beats (10s + 5s + 5s) with 5s chunks = 4 chunks
    - Beat 0 starts at 0s → Chunk 0
    - Beat 1 starts at 10s → Chunk 2 (10s / 5s per chunk)
    - Beat 2 starts at 15s → Chunk 3 (15s / 5s per chunk)
    
    Args:
        beats: List of beat dictionaries with 'start' and 'duration' keys
        actual_chunk_duration: Duration of each chunk in seconds
        
    Returns:
        Dictionary mapping chunk_idx -> beat_idx for chunks that start a beat
    """
    beat_to_chunk = {}
    
    for beat_idx, beat in enumerate(beats):
        # Use actual beat start time from Phase 1 (more reliable than recalculating)
        beat_start = beat.get('start', 0.0)
        
        # Calculate which chunk this beat starts at
        # Account for chunk overlap (25% overlap means chunks are spaced at 75% of duration)
        chunk_spacing = actual_chunk_duration * 0.75  # 25% overlap
        chunk_idx = int(beat_start // chunk_spacing) if chunk_spacing > 0 else 0
        
        # Only map if this chunk actually starts at or very close to the beat start
        # (within 0.5 seconds tolerance to handle floating point precision)
        chunk_start_time = chunk_idx * chunk_spacing
        if abs(chunk_start_time - beat_start) < 0.5:
            beat_to_chunk[chunk_idx] = beat_idx
    
    return beat_to_chunk


def build_chunk_specs_with_storyboard(
    video_id: str,
    spec: Dict,
    reference_urls: Dict,
    user_id: str = None
) -> Tuple[List[ChunkSpec], Dict[int, int]]:
    """
    Build chunk specifications using storyboard images from Phase 2 (NEW LOGIC).
    
    This function uses storyboard images at beat boundaries and last-frame continuation
    within beats, following TDD v2.0 architecture.
    
    Args:
        video_id: Unique video generation ID
        spec: Video specification from Phase 1 (contains beats with image_url from Phase 2)
        reference_urls: Dictionary with style_guide_url and product_reference_url from Phase 3
        user_id: User ID for organizing outputs in S3 (required for new structure)
        
    Returns:
        Tuple of (List of ChunkSpec objects, beat_to_chunk_map dictionary)
        
    Raises:
        PhaseException: If storyboard images are missing or invalid
    """
    duration = spec.get('duration', 30)
    beats = spec.get('beats', [])
    
    # Validate that we have storyboard images in beats
    storyboard_images_count = sum(1 for beat in beats if beat.get('image_url'))
    if storyboard_images_count == 0:
        raise PhaseException("No storyboard images found in spec['beats'] - cannot use storyboard logic")
    
    if storyboard_images_count < len(beats):
        print(f"   ⚠️  Warning: Only {storyboard_images_count}/{len(beats)} beats have storyboard images")
    
    # Get model from spec (or use default)
    selected_model = spec.get('model', 'hailuo')
    try:
        model_config = get_model_config(selected_model)
    except Exception as e:
        print(f"   ⚠️  Invalid model '{selected_model}', falling back to default: {str(e)}")
        model_config = get_default_model()
        selected_model = model_config.get('name', 'hailuo')
    
    # Get model's actual chunk duration
    actual_chunk_duration = model_config.get('actual_chunk_duration', 5.0)
    model_name = model_config.get('name', 'unknown')
    
    # Calculate chunk count
    chunk_count = math.ceil(duration / actual_chunk_duration)
    chunk_duration = actual_chunk_duration
    
    # Overlap is 25% of actual chunk duration
    chunk_overlap = actual_chunk_duration * 0.25
    
    print(f"   📊 Chunk calculation (Storyboard Mode):")
    print(f"      - Video duration: {duration}s")
    print(f"      - Model: {model_name}")
    print(f"      - Model outputs: {actual_chunk_duration}s chunks")
    print(f"      - Chunk count: ceil({duration}s / {actual_chunk_duration}s) = {chunk_count} chunks")
    print(f"      - Overlap: {chunk_overlap:.2f}s (25% of chunk duration)")
    print(f"      - Storyboard images: {storyboard_images_count}/{len(beats)} beats")
    
    # Calculate beat-to-chunk mapping
    beat_to_chunk_map = calculate_beat_to_chunk_mapping(beats, actual_chunk_duration)
    
    print(f"   🗺️  Beat-to-Chunk Mapping:")
    for chunk_idx, beat_idx in sorted(beat_to_chunk_map.items()):
        beat = beats[beat_idx] if beat_idx < len(beats) else None
        beat_id = beat.get('beat_id', f'beat_{beat_idx}') if beat else 'unknown'
        print(f"      - Chunk {chunk_idx} starts Beat {beat_idx} ({beat_id})")
    
    chunk_specs = []
    product_reference_url = reference_urls.get('product_reference_url') if reference_urls else None
    
    for chunk_num in range(chunk_count):
        # Calculate chunk timing
        start_time = chunk_num * (chunk_duration - chunk_overlap)
        duration_actual = chunk_duration
        
        # Map chunk to corresponding beat
        beat_index = 0
        for i, beat in enumerate(beats):
            beat_start = beat.get('start', 0)
            beat_duration = beat.get('duration', 5)
            if start_time >= beat_start and start_time < beat_start + beat_duration:
                beat_index = i
                break
        
        # Use last beat if we've gone past all beats
        if beat_index >= len(beats):
            beat_index = len(beats) - 1
        
        beat = beats[beat_index]
        
        # Determine if this chunk starts a new beat (use storyboard image)
        storyboard_image_url = None
        uses_storyboard = False
        
        if chunk_num in beat_to_chunk_map:
            # This chunk starts a new beat - try to use storyboard image
            beat_idx_for_storyboard = beat_to_chunk_map[chunk_num]
            if beat_idx_for_storyboard < len(beats):
                storyboard_beat = beats[beat_idx_for_storyboard]
                storyboard_image_url = storyboard_beat.get('image_url')
                if storyboard_image_url:
                    uses_storyboard = True
                    print(f"   🎨 Chunk {chunk_num}: Using storyboard image from Beat {beat_idx_for_storyboard}")
                else:
                    # Beat exists but has no image_url - will use last-frame continuation instead
                    print(f"   ⚠️  Chunk {chunk_num}: Beat {beat_idx_for_storyboard} has no image_url, will use last-frame continuation")
                    uses_storyboard = False
            else:
                # Beat index out of range - will use last-frame continuation
                print(f"   ⚠️  Chunk {chunk_num}: Beat index {beat_idx_for_storyboard} out of range ({len(beats)} beats), will use last-frame continuation")
                uses_storyboard = False
        else:
            # This chunk does NOT start a beat - will use last-frame continuation
            print(f"   🔄 Chunk {chunk_num}: Will use last-frame continuation (does not start a beat)")
        
        # Build prompt from beat
        prompt_template = beat.get('prompt_template', '')
        prompt = prompt_template.format(
            product_name=spec.get('product', {}).get('name', 'product'),
            style_aesthetic=spec.get('style', {}).get('aesthetic', 'cinematic')
        )
        
        # Truncate prompt if too long
        words = prompt.split()
        if len(words) > 100:
            prompt = ' '.join(words[:100])
        
        # Determine reference URL for chunk
        chunk_reference_url = storyboard_image_url if uses_storyboard else None
        
        chunk_spec = ChunkSpec(
            video_id=video_id,
            user_id=user_id,
            chunk_num=chunk_num,
            start_time=start_time,
            duration=duration_actual,
            beat=beat,
            animatic_frame_url=None,  # Not used in storyboard mode
            style_guide_url=chunk_reference_url,  # Storyboard image or None
            product_reference_url=product_reference_url,
            previous_chunk_last_frame=None,  # Will be set after previous chunk generates
            uploaded_asset_url=None,
            prompt=prompt,
            fps=spec.get('fps', 24),
            use_text_to_video=True,  # Always use image-to-video with storyboard
            model=selected_model
        )
        
        chunk_specs.append(chunk_spec)
    
    return chunk_specs, beat_to_chunk_map


def generate_single_chunk_continuous(chunk_spec_obj: ChunkSpec) -> dict:
    """
    Generate a chunk using last-frame continuation (within a beat).
    
    This function uses the previous chunk's last frame as the init_image
    to maintain temporal coherence within a beat.
    
    Args:
        chunk_spec_obj: ChunkSpec object with previous_chunk_last_frame set
        
    Returns:
        Dictionary with chunk_url, last_frame_url, and cost
        
    Raises:
        PhaseException: If generation fails or previous frame is missing
    """
    chunk_num = chunk_spec_obj.chunk_num
    video_id = chunk_spec_obj.video_id
    user_id = chunk_spec_obj.user_id
    
    if not chunk_spec_obj.previous_chunk_last_frame:
        raise PhaseException(f"Chunk {chunk_num} requires previous_chunk_last_frame for continuous generation")
    
    print(f"   🔄 Chunk {chunk_num}: Continuous generation using last frame from chunk {chunk_num - 1}")
    
    # Get model configuration
    selected_model = chunk_spec_obj.model or 'hailuo'
    try:
        model_config = get_model_config(selected_model)
    except Exception as e:
        model_config = get_default_model()
        selected_model = model_config.get('name', 'hailuo')
    
    model_name = model_config['replicate_model']
    cost_per_second = model_config['cost_per_generation']
    param_names = model_config.get('param_names', {})
    image_param_name = param_names.get('image', 'image')
    prompt_param_name = param_names.get('prompt', 'prompt')
    
    chunk_start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"🎬 [{timestamp}] Chunk {chunk_num} - Continuous Generation")
    print(f"   Using last frame from previous chunk")
    print(f"   Prompt: {chunk_spec_obj.prompt[:80]}...")
    
    temp_files = []
    
    try:
        # Download previous chunk's last frame from S3
        prev_frame_url = chunk_spec_obj.previous_chunk_last_frame
        if prev_frame_url.startswith('s3://'):
            prev_frame_key = prev_frame_url.replace(f's3://{s3_client.bucket}/', '')
        elif prev_frame_url.startswith('http'):
            prev_frame_key = prev_frame_url.split(f'{s3_client.bucket}/', 1)[-1].split('?')[0]
        else:
            prev_frame_key = prev_frame_url
        
        prev_frame_path = s3_client.download_temp(prev_frame_key)
        temp_files.append(prev_frame_path)
        
        # Generate video using previous frame as init_image
        with open(prev_frame_path, 'rb') as img_file:
            replicate_input = {
                image_param_name: img_file,
                prompt_param_name: chunk_spec_obj.prompt,
            }
            
            # Add duration/num_frames based on model
            if 'duration' in param_names:
                duration_param_name = param_names.get('duration', 'duration')
                replicate_input[duration_param_name] = int(chunk_spec_obj.duration)
            else:
                fps = chunk_spec_obj.fps
                chunk_duration = chunk_spec_obj.duration
                max_frames = model_config['params'].get('num_frames', 80)
                num_frames = min(int(chunk_duration * fps), max_frames)
                replicate_input["num_frames"] = num_frames
                replicate_input["fps"] = fps
            
            # Add width/height if model supports them
            if 'width' in param_names:
                replicate_input[param_names.get('width', 'width')] = model_config['params'].get('width')
            if 'height' in param_names:
                replicate_input[param_names.get('height', 'height')] = model_config['params'].get('height')
            
            output = replicate_client.run(
                model_name,
                input=replicate_input,
                timeout=300
            )
        
        # Download generated video
        if isinstance(output, str):
            video_url = output
        elif hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
            video_list = list(output)
            video_url = video_list[0] if video_list else str(output)
        else:
            video_url = str(output)
        
        video_path = tempfile.mktemp(suffix='.mp4')
        temp_files.append(video_path)
        
        response = requests.get(video_url, stream=True, timeout=120)
        response.raise_for_status()
        with open(video_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # Upload chunk to S3
        chunk_key = get_video_s3_key(user_id, video_id, f"chunk_{chunk_num:02d}.mp4")
        chunk_s3_url = s3_client.upload_file(video_path, chunk_key)
        
        # Extract last frame for next chunk
        last_frame_path = extract_last_frame(video_path)
        temp_files.append(last_frame_path)
        
        # Upload last frame to S3
        last_frame_key = get_video_s3_key(user_id, video_id, f"chunk_{chunk_num:02d}_last_frame.png")
        last_frame_s3_url = s3_client.upload_file(last_frame_path, last_frame_key)
        
        # Cleanup
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
        
        # Calculate cost
        chunk_cost = chunk_spec_obj.duration * cost_per_second
        generation_time = time.time() - chunk_start_time
        
        print(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Chunk {chunk_num} Complete (Continuous)")
        print(f"   Cost: ${chunk_cost:.4f}")
        print(f"   Generation Time: {generation_time:.1f}s")
        
        return {
            'chunk_url': chunk_s3_url,
            'last_frame_url': last_frame_s3_url,
            'cost': chunk_cost
        }
        
    except Exception as e:
        # Cleanup on error
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
        raise PhaseException(f"Failed to generate continuous chunk {chunk_num}: {str(e)}")


@celery_app.task(bind=True, name="app.phases.phase4_chunks_storyboard.chunk_generator.generate_single_chunk_with_storyboard")
def generate_single_chunk_with_storyboard(
    self,
    chunk_spec: dict, 
    beat_to_chunk_map: dict = None
) -> dict:
    """
    Generate a single video chunk using storyboard images (NEW LOGIC).
    
    This function determines whether to use a storyboard image (at beat boundaries)
    or last-frame continuation (within beats).
    
    Args:
        self: Celery task instance
        chunk_spec: ChunkSpec dictionary
        beat_to_chunk_map: Optional dictionary mapping chunk_idx -> beat_idx for storyboard detection
        
    Returns:
        Dictionary with chunk_url, last_frame_url, cost, and init_image_source
    """
    chunk_spec_obj = ChunkSpec(**chunk_spec)
    chunk_num = chunk_spec_obj.chunk_num
    video_id = chunk_spec_obj.video_id
    user_id = chunk_spec_obj.user_id
    
    # Determine if this chunk starts a beat (uses storyboard) or continues (uses last frame)
    is_beat_start = beat_to_chunk_map and chunk_num in beat_to_chunk_map
    
    if is_beat_start:
        # This chunk starts a new beat - use storyboard image
        beat_idx = beat_to_chunk_map[chunk_num]
        print(f"   🎨 Chunk {chunk_num}: Beat boundary - using storyboard from beat {beat_idx}")
        
        # Generate using storyboard image
        if not chunk_spec_obj.style_guide_url:
            raise PhaseException(f"Chunk {chunk_num} marked as beat start but has no storyboard image URL")
        
        # Get model configuration
        selected_model = chunk_spec_obj.model or 'hailuo'
        try:
            model_config = get_model_config(selected_model)
        except Exception as e:
            model_config = get_default_model()
            selected_model = model_config.get('name', 'hailuo')
        
        model_name = model_config['replicate_model']
        cost_per_second = model_config['cost_per_generation']
        param_names = model_config.get('param_names', {})
        image_param_name = param_names.get('image', 'image')
        prompt_param_name = param_names.get('prompt', 'prompt')
        
        chunk_start_time = time.time()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(f"🎬 [{timestamp}] Chunk {chunk_num} - Beat Start (Storyboard)")
        print(f"   Beat Index: {beat_idx}")
        print(f"   Prompt: {chunk_spec_obj.prompt[:80]}...")
        
        temp_files = []
        
        try:
            # Download storyboard image from S3
            storyboard_url = chunk_spec_obj.style_guide_url
            if storyboard_url.startswith('s3://'):
                storyboard_key = storyboard_url.replace(f's3://{s3_client.bucket}/', '')
            elif storyboard_url.startswith('http'):
                storyboard_key = storyboard_url.split(f'{s3_client.bucket}/', 1)[-1].split('?')[0]
            else:
                storyboard_key = storyboard_url
            
            storyboard_path = s3_client.download_temp(storyboard_key)
            temp_files.append(storyboard_path)
            
            # Generate video using storyboard image
            with open(storyboard_path, 'rb') as img_file:
                replicate_input = {
                    image_param_name: img_file,
                    prompt_param_name: chunk_spec_obj.prompt,
                }
                
                # Add duration/num_frames based on model
                if 'duration' in param_names:
                    duration_param_name = param_names.get('duration', 'duration')
                    replicate_input[duration_param_name] = int(chunk_spec_obj.duration)
                else:
                    fps = chunk_spec_obj.fps
                    chunk_duration = chunk_spec_obj.duration
                    max_frames = model_config['params'].get('num_frames', 80)
                    num_frames = min(int(chunk_duration * fps), max_frames)
                    replicate_input["num_frames"] = num_frames
                    replicate_input["fps"] = fps
                
                # Add width/height if model supports them
                if 'width' in param_names:
                    replicate_input[param_names.get('width', 'width')] = model_config['params'].get('width')
                if 'height' in param_names:
                    replicate_input[param_names.get('height', 'height')] = model_config['params'].get('height')
                
                output = replicate_client.run(
                    model_name,
                    input=replicate_input,
                    timeout=300
                )
            
            # Download generated video
            if isinstance(output, str):
                video_url = output
            elif hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
                video_list = list(output)
                video_url = video_list[0] if video_list else str(output)
            else:
                video_url = str(output)
            
            video_path = tempfile.mktemp(suffix='.mp4')
            temp_files.append(video_path)
            
            response = requests.get(video_url, stream=True, timeout=120)
            response.raise_for_status()
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Upload chunk to S3
            chunk_key = get_video_s3_key(user_id, video_id, f"chunk_{chunk_num:02d}.mp4")
            chunk_s3_url = s3_client.upload_file(video_path, chunk_key)
            
            # Extract last frame for next chunk
            last_frame_path = extract_last_frame(video_path)
            temp_files.append(last_frame_path)
            
            # Upload last frame to S3
            last_frame_key = get_video_s3_key(user_id, video_id, f"chunk_{chunk_num:02d}_last_frame.png")
            last_frame_s3_url = s3_client.upload_file(last_frame_path, last_frame_key)
            
            # Cleanup
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
            
            # Calculate cost
            chunk_cost = chunk_spec_obj.duration * cost_per_second
            generation_time = time.time() - chunk_start_time
            
            print(f"✅ [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Chunk {chunk_num} Complete (Storyboard)")
            print(f"   Beat: {beat_idx}")
            print(f"   Cost: ${chunk_cost:.4f}")
            print(f"   Generation Time: {generation_time:.1f}s")
            
            return {
                'chunk_url': chunk_s3_url,
                'last_frame_url': last_frame_s3_url,
                'cost': chunk_cost,
                'init_image_source': f'storyboard_beat_{beat_idx}',
                'beat_idx': beat_idx
            }
            
        except Exception as e:
            # Cleanup on error
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
            raise PhaseException(f"Failed to generate storyboard chunk {chunk_num}: {str(e)}")
    
    else:
        # This chunk continues within a beat - use last-frame continuation
        result = generate_single_chunk_continuous(chunk_spec_obj)
        result['init_image_source'] = 'last_frame_continuation'
        return result