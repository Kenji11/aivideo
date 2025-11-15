# Phase 4: Chunk Generation with Image Compositing
import os
import tempfile
import subprocess
import requests
import time
from datetime import datetime
from typing import Optional, List, Dict
from PIL import Image

from app.orchestrator.celery_app import celery_app
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.phases.phase4_chunks.schemas import ChunkSpec
from app.phases.phase4_chunks.model_config import get_default_model
from app.common.constants import S3_CHUNKS_PREFIX
from app.common.exceptions import PhaseException


def create_reference_composite(
    animatic_path: str,
    style_guide_path: Optional[str] = None,
    previous_frame_path: Optional[str] = None,
    animatic_weight: float = 0.7,
    style_weight: float = 0.3,
    temporal_weight: float = 0.7
) -> str:
    """
    Composite multiple reference images into single conditioning image.
    
    Strategy:
    - Chunk 0: animatic (70%) + style_guide (30%)
    - Chunks 1+: previous_frame (70%) + animatic (30%)
    
    Args:
        animatic_path: Path to animatic frame image
        style_guide_path: Optional path to style guide image (for chunk 0)
        previous_frame_path: Optional path to previous chunk's last frame (for chunks 1+)
        animatic_weight: Weight for animatic image (default 0.7)
        style_weight: Weight for style guide (default 0.3)
        temporal_weight: Weight for previous frame (default 0.7)
        
    Returns:
        Path to temporary composite image file
        
    Raises:
        PhaseException: If image loading or compositing fails
    """
    try:
        # Load animatic as base
        animatic_img = Image.open(animatic_path).convert('RGB')
        animatic_width, animatic_height = animatic_img.size
        
        # Resize all images to match animatic dimensions
        def resize_to_match(img: Image.Image) -> Image.Image:
            return img.resize((animatic_width, animatic_height), Image.Resampling.LANCZOS)
        
        # Start with animatic as base
        composite = animatic_img.copy()
        
        # Chunk 0: Blend with style guide
        if style_guide_path and previous_frame_path is None:
            style_img = Image.open(style_guide_path).convert('RGB')
            style_img = resize_to_match(style_img)
            
            # Blend: animatic_weight * animatic + style_weight * style_guide
            composite = Image.blend(composite, style_img, style_weight)
        
        # Chunks 1+: Blend with previous frame
        elif previous_frame_path:
            prev_img = Image.open(previous_frame_path).convert('RGB')
            prev_img = resize_to_match(prev_img)
            
            # Blend: temporal_weight * previous_frame + (1 - temporal_weight) * animatic
            composite = Image.blend(prev_img, composite, 1 - temporal_weight)
        
        # Save composite to temp file
        temp_composite = tempfile.mktemp(suffix='.png')
        composite.save(temp_composite, 'PNG')
        
        return temp_composite
        
    except Exception as e:
        raise PhaseException(f"Failed to create reference composite: {str(e)}")


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


def build_chunk_specs(
    video_id: str,
    spec: Dict,
    animatic_urls: List[str],
    reference_urls: Dict
) -> List[ChunkSpec]:
    """
    Build chunk specifications from video spec, animatic URLs, and reference URLs.
    
    Uses chunk_count from spec (calculated in Phase 1 based on model's actual output duration).
    
    Args:
        video_id: Unique video generation ID
        spec: Video specification from Phase 1 (contains chunk_count, chunk_duration, beats, etc.)
        animatic_urls: List of animatic frame S3 URLs from Phase 2
        reference_urls: Dictionary with style_guide_url and product_reference_url from Phase 3
        
    Returns:
        List of ChunkSpec objects, one per chunk
    """
    duration = spec.get('duration', 30)  # Default 30 seconds
    beats = spec.get('beats', [])
    
    # Get chunk parameters from spec (calculated in Phase 1 based on model's actual output)
    chunk_count = spec.get('chunk_count')
    actual_chunk_duration = spec.get('chunk_duration')
    
    # Fallback if not provided (for backwards compatibility)
    if chunk_count is None or actual_chunk_duration is None:
        from app.phases.phase4_chunks.model_config import get_default_model
        import math
        model_config = get_default_model()
        actual_chunk_duration = model_config['actual_chunk_duration']
        chunk_count = math.ceil(duration / actual_chunk_duration)
        print(f"⚠️  chunk_count not in spec, calculated: {chunk_count} chunks @ {actual_chunk_duration}s each")
    
    # Calculate overlap based on actual chunk duration (25% overlap for smooth transitions)
    chunk_overlap = actual_chunk_duration * 0.25
    
    # Log chunk calculation
    print(f"📊 Chunk Calculation:")
    print(f"   Video Duration: {duration}s")
    print(f"   Model Chunk Duration: {actual_chunk_duration}s (actual model output)")
    print(f"   Chunk Count: {chunk_count} chunks")
    print(f"   Chunk Overlap: {chunk_overlap}s ({chunk_overlap/actual_chunk_duration*100:.0f}%)")
    
    # Determine if we should use text-to-video or image-to-video mode
    # Priority: 1) product_reference from Phase 3, 2) animatic from Phase 2, 3) text-to-video fallback
    product_reference_url = reference_urls.get('product_reference_url') if reference_urls else None
    has_reference_image = product_reference_url is not None
    has_animatic = len(animatic_urls) > 0
    
    # Use image-to-video if we have either product reference or animatic
    use_text_to_video = not (has_reference_image or has_animatic)
    
    # Log mode selection
    if has_reference_image:
        print(f"✅ Using image-to-video mode with product reference from Phase 3")
        print(f"   Reference URL: {product_reference_url[:80]}...")
    elif has_animatic:
        print(f"✅ Using image-to-video mode with animatic frames from Phase 2")
    else:
        print(f"⚠️  No reference images available - using text-to-video fallback")
    
    # Only validate animatic frames if we're using them (Phase 2 enabled)
    if has_animatic and not has_reference_image:
        # Ensure we have enough animatic frames (only check if animatic_urls is provided)
        if len(animatic_urls) < len(beats):
            raise PhaseException(f"Not enough animatic frames: {len(animatic_urls)} < {len(beats)}")
    
    chunk_specs = []
    style_guide_url = reference_urls.get('style_guide_url') if reference_urls else None
    
    for chunk_num in range(chunk_count):
        # Calculate chunk timing based on actual model output duration
        start_time = chunk_num * (actual_chunk_duration - chunk_overlap)
        duration_actual = actual_chunk_duration  # Use actual model output duration
        
        # Map chunk to corresponding beat
        # Find beat that covers this chunk's start time
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
        
        # Determine reference image to use for this chunk
        # PR #8 Strategy: Chunk 0 uses product_reference, chunks 1+ use previous_chunk_last_frame
        # animatic_frame_url is now a fallback only
        animatic_frame_url = None
        if has_reference_image:
            # Chunk 0: Use product reference as init image
            # Chunks 1+: Will use previous_chunk_last_frame (set by service layer)
            # Keep product_reference as fallback in case previous frame is missing
            if chunk_num == 0:
                animatic_frame_url = product_reference_url
            else:
                # For chunks 1+, keep as fallback but expect previous_chunk_last_frame to be used
                animatic_frame_url = product_reference_url  # Fallback only
        elif has_animatic:
            # Use animatic frames (different frame per beat) - Phase 2 mode
            animatic_frame_url = animatic_urls[beat_index] if beat_index < len(animatic_urls) else animatic_urls[-1]
        
        # Build prompt from beat (keep concise, ~50-100 words)
        prompt_template = beat.get('prompt_template', '')
        # Format template if it has placeholders (already formatted in Phase 1, but be safe)
        prompt = prompt_template.format(
            product_name=spec.get('product', {}).get('name', 'product'),
            style_aesthetic=spec.get('style', {}).get('aesthetic', 'cinematic')
        )
        
        # Truncate prompt if too long (keep under 100 words)
        words = prompt.split()
        if len(words) > 100:
            prompt = ' '.join(words[:100])
        
        # Create chunk spec
        chunk_spec = ChunkSpec(
            video_id=video_id,
            chunk_num=chunk_num,
            start_time=start_time,
            duration=duration_actual,
            beat=beat,
            animatic_frame_url=animatic_frame_url,  # product_reference, animatic, or None
            style_guide_url=style_guide_url if chunk_num == 0 else None,  # Style guide disabled for MVP
            product_reference_url=product_reference_url,
            previous_chunk_last_frame=None,  # Will be set after previous chunk generates
            prompt=prompt,
            fps=spec.get('fps', 24),
            use_text_to_video=use_text_to_video  # False if we have any reference image
        )
        
        chunk_specs.append(chunk_spec)
    
    return chunk_specs


@celery_app.task(bind=True, name="app.phases.phase4_chunks.chunk_generator.generate_single_chunk")
def generate_single_chunk(self, chunk_spec: dict) -> dict:
    """
    Generate a single video chunk using Zeroscope.
    
    Args:
        self: Celery task instance
        chunk_spec: ChunkSpec dictionary
        
    Returns:
        Dictionary with chunk_url, last_frame_url, and cost
    """
    chunk_spec_obj = ChunkSpec(**chunk_spec)
    video_id = chunk_spec_obj.video_id
    chunk_num = chunk_spec_obj.chunk_num
    use_text_to_video = chunk_spec_obj.use_text_to_video
    
    # ============ INPUT LOGGING ============
    chunk_start_time = time.time()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get model configuration (default model)
    model_config = get_default_model()
    model_name = model_config['replicate_model']
    model_params = model_config['params']
    cost_per_second = model_config['cost_per_generation']
    
    # Build prompt (already formatted in build_chunk_specs from beat prompt_template)
    prompt = chunk_spec_obj.prompt
    prompt_preview = prompt[:100] + "..." if len(prompt) > 100 else prompt
    
    print(f"🎬 [{timestamp}] Chunk {chunk_num} Input")
    print(f"   Start Time: {chunk_spec_obj.start_time:.2f}s")
    print(f"   Duration: {chunk_spec_obj.duration:.2f}s")
    print(f"   Prompt: {prompt_preview}")
    print(f"   Text-to-Video Mode: {'✅' if use_text_to_video else '❌'}")
    print(f"   Model: {model_config['name']} ({model_name})")
    
    temp_files = []  # Track temp files for cleanup
    
    try:
        
        # Calculate frames based on chunk duration and fps from chunk spec
        fps = chunk_spec_obj.fps
        chunk_duration = chunk_spec_obj.duration
        # Use model's max frames limit
        max_frames = model_params.get('num_frames', 80)
        num_frames = min(int(chunk_duration * fps), max_frames)
        
        output = None
        last_error = None
        image_to_video_failed = False
        
        # Try image-to-video first if images are available, otherwise use text-to-video
        if not use_text_to_video and chunk_spec_obj.animatic_frame_url:
            # ============ IMAGE-TO-VIDEO MODE ============
            try:
                print(f"Generating chunk {chunk_num} with image-to-video...")
                
                # ============ LAST-FRAME CONTINUATION STRATEGY (PR #8) ============
                # Chunk 0: Use Phase 3 reference image as init_image
                # Chunks 1+: Use last frame from previous chunk as init_image
                # This provides temporal coherence and motion continuity
                
                init_image_path = None
                
                if chunk_num == 0:
                    # ============ CHUNK 0: Use Phase 3 Reference Image ============
                    if chunk_spec_obj.product_reference_url:
                        # MVP Mode: Use product reference from Phase 3
                        reference_key = chunk_spec_obj.product_reference_url.replace(f's3://{s3_client.bucket}/', '')
                        init_image_path = s3_client.download_temp(reference_key)
                        temp_files.append(init_image_path)
                        print(f"   🎬 Chunk 0: Using reference image from Phase 3")
                        print(f"   Reference URL: {chunk_spec_obj.product_reference_url[:80]}...")
                    elif chunk_spec_obj.animatic_frame_url:
                        # Fallback: Use animatic frame if no product reference
                        reference_key = chunk_spec_obj.animatic_frame_url.replace(f's3://{s3_client.bucket}/', '')
                        init_image_path = s3_client.download_temp(reference_key)
                        temp_files.append(init_image_path)
                        print(f"   🎬 Chunk 0: Using animatic frame (no product reference available)")
                else:
                    # ============ CHUNKS 1+: Use Last Frame from Previous Chunk ============
                    if chunk_spec_obj.previous_chunk_last_frame:
                        # Use last frame from previous chunk for temporal continuity
                        prev_frame_key = chunk_spec_obj.previous_chunk_last_frame.replace(f's3://{s3_client.bucket}/', '')
                        init_image_path = s3_client.download_temp(prev_frame_key)
                        temp_files.append(init_image_path)
                        print(f"   🔗 Chunk {chunk_num}: Using last frame from chunk {chunk_num-1} for continuity")
                        print(f"   Previous frame URL: {chunk_spec_obj.previous_chunk_last_frame[:80]}...")
                    elif chunk_spec_obj.animatic_frame_url:
                        # Fallback: Use animatic/reference if previous frame not available
                        reference_key = chunk_spec_obj.animatic_frame_url.replace(f's3://{s3_client.bucket}/', '')
                        init_image_path = s3_client.download_temp(reference_key)
                        temp_files.append(init_image_path)
                        print(f"   ⚠️  Chunk {chunk_num}: Previous frame not available, using reference image")
                
                if not init_image_path:
                    raise PhaseException(f"No init image available for chunk {chunk_num}")
                
                # Use init_image directly (no compositing for MVP)
                composite_path = init_image_path
                
                # Image-to-video using model config
                # Replicate accepts file paths or file objects
                # Open file in binary mode for Replicate
                with open(composite_path, 'rb') as img_file:
                    try:
                        print(f"   Trying model: {model_name} (image-to-video)...")
                        
                        # Get model-specific parameter names (some models use different names)
                        param_names = model_config.get('param_names', {
                            'image': 'image',  # Default parameter names
                            'prompt': 'prompt',
                            'num_frames': 'num_frames',
                            'fps': 'fps',
                        })
                        
                        # Build input dict with model-specific parameter names
                        input_params = {
                            param_names['image']: img_file,
                            param_names['prompt']: prompt,
                            param_names['num_frames']: num_frames,
                            param_names['fps']: fps,
                        }
                        
                        # Use model config parameters
                        # Timeout: 5 minutes per chunk (should be enough for video generation)
                        output = replicate_client.run(
                            model_name,
                            input=input_params,
                            timeout=300  # 5 minutes timeout
                        )
                        
                        print(f"   ✅ Success with {model_name}")
                    except Exception as e:
                        last_error = e
                        error_msg = str(e).lower()
                        error_type = type(e).__name__
                        # Image-to-video failed, fallback to text-to-video
                        print(f"   ⚠️  Image-to-video failed ({error_type}): {str(e)[:80]}...), falling back to text-to-video...")
                        image_to_video_failed = True
                
                if output is None and not image_to_video_failed:
                    image_to_video_failed = True
                    print(f"   ⚠️  Image-to-video failed, falling back to text-to-video...")
                    
            except Exception as e:
                # Image-to-video processing failed, fallback to text-to-video
                image_to_video_failed = True
                last_error = e
                print(f"   ⚠️  Image-to-video processing failed: {str(e)[:80]}..., falling back to text-to-video...")
        
        # ============ TEXT-TO-VIDEO MODE (Fallback or Primary) ============
        if use_text_to_video or image_to_video_failed:
            print(f"Generating chunk {chunk_num} with text-to-video (no image input)...")
            
            # Check if model supports text-to-video
            if not model_config.get('supports_text_to_video', False):
                raise PhaseException(f"Model {model_config['name']} does not support text-to-video generation")
            
            try:
                print(f"   Trying text-to-video model: {model_name}...")
                
                # Text-to-video: prompt only, no image input
                # Use model config parameters
                output = replicate_client.run(
                    model_name,
                    input={
                        "prompt": prompt,
                        "num_frames": num_frames,
                        "fps": fps,
                        # No "image" parameter for text-to-video
                    },
                    timeout=300  # 5 minutes timeout
                )
                
                print(f"   ✅ Success with text-to-video ({model_name})")
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                print(f"   ❌ Text-to-video failed ({error_type}): {str(e)}")
                raise PhaseException(f"Text-to-video generation failed: {str(e)}")
            
            if output is None:
                raise PhaseException(f"Text-to-video generation failed. Last error: {str(last_error)}")
        
        # Download generated video
        # Replicate returns either a string URL or a list/iterator
        if isinstance(output, str):
            video_url = output
        elif hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
            # If it's an iterator/list, get first item
            video_list = list(output) if hasattr(output, '__iter__') else [output]
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
        chunk_key = f"{S3_CHUNKS_PREFIX}/{video_id}/chunk_{chunk_num:02d}.mp4"
        chunk_s3_url = s3_client.upload_file(video_path, chunk_key)
        
        # Extract last frame for next chunk's temporal consistency
        last_frame_path = extract_last_frame(video_path)
        temp_files.append(last_frame_path)
        
        # Upload last frame to S3
        last_frame_key = f"{S3_CHUNKS_PREFIX}/{video_id}/frames/chunk_{chunk_num}_last_frame.png"
        last_frame_s3_url = s3_client.upload_file(last_frame_path, last_frame_key)
        
        # Cleanup temp files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass  # Ignore cleanup errors
        
        # Calculate actual cost using model config
        chunk_duration = chunk_spec_obj.duration
        chunk_cost = chunk_duration * cost_per_second
        generation_time = time.time() - chunk_start_time
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ============ SUCCESS LOGGING ============
        print(f"✅ [{timestamp}] Chunk {chunk_num} Complete")
        print(f"   Chunk URL: {chunk_s3_url[:80]}...")
        print(f"   Last Frame URL: {last_frame_s3_url[:80] if last_frame_s3_url else 'N/A'}...")
        print(f"   Cost: ${chunk_cost:.4f}")
        print(f"   Generation Time: {generation_time:.1f}s")
        
        return {
            'chunk_url': chunk_s3_url,
            'last_frame_url': last_frame_s3_url,
            'cost': chunk_cost
        }
        
    except Exception as e:
        # Cleanup temp files on error
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
        
        raise PhaseException(f"Failed to generate chunk {chunk_num}: {str(e)}")
