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
    
    Args:
        video_id: Unique video generation ID
        spec: Video specification from Phase 1 (contains beats, duration, etc.)
        animatic_urls: List of animatic frame S3 URLs from Phase 2
        reference_urls: Dictionary with style_guide_url and product_reference_url from Phase 3
        
    Returns:
        List of ChunkSpec objects, one per chunk
    """
    duration = spec.get('duration', 30)  # Default 30 seconds
    beats = spec.get('beats', [])
    
    # Calculate chunk parameters
    # Adaptive chunk duration based on total video length
    # Target: 5-6 chunks for 30-second videos
    if duration <= 10:
        chunk_duration = 1.5  # 1.5 seconds per chunk for short ads
        chunk_overlap = 0.3  # 0.3 seconds overlap
    elif duration <= 20:
        chunk_duration = 1.8  # 1.8 seconds per chunk for medium videos
        chunk_overlap = 0.4  # 0.4 seconds overlap
    elif duration <= 30:
        # For 30-second videos: use ~5.5-second chunks to get exactly 6 chunks
        # Formula: chunk_duration = (duration + overlap * (1 + target_chunks)) / target_chunks
        target_chunks = 6
        chunk_overlap = 0.5
        chunk_duration = (duration + chunk_overlap * (1 + target_chunks)) / target_chunks  # ~5.42s
    else:
        # For longer videos (>30s): scale proportionally
        # Target ~6 chunks, so chunk_duration = duration / 6
        chunk_duration = duration / 6.0
        chunk_overlap = 0.5  # 0.5 seconds overlap
    
    chunk_count = int((duration + chunk_overlap) / (chunk_duration - chunk_overlap))
    
    # Check if we have animatic URLs - if not, use text-to-video fallback
    use_text_to_video = len(animatic_urls) == 0
    
    # Only validate animatic frames if we're using image-to-video mode
    if not use_text_to_video:
        # Ensure we have enough animatic frames (only check if animatic_urls is provided)
        if len(animatic_urls) < len(beats):
            raise PhaseException(f"Not enough animatic frames: {len(animatic_urls)} < {len(beats)}")
    
    chunk_specs = []
    style_guide_url = reference_urls.get('style_guide_url') if reference_urls else None
    product_reference_url = reference_urls.get('product_reference_url') if reference_urls else None
    
    # Prioritize uploaded assets (user-provided images like Kobe photos) over generated references
    uploaded_assets = reference_urls.get('uploaded_assets', []) if reference_urls else []
    has_uploaded_assets = len(uploaded_assets) > 0
    
    if has_uploaded_assets:
        print(f"   📸 Found {len(uploaded_assets)} uploaded reference image(s)")
        # Will distribute images across chunks (see chunk creation below)
    elif style_guide_url:
        print(f"   Using generated style guide as reference")
    elif product_reference_url:
        print(f"   Using product reference as reference")
    
    for chunk_num in range(chunk_count):
        # Calculate chunk timing
        start_time = chunk_num * (chunk_duration - chunk_overlap)
        duration_actual = chunk_duration
        
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
        
        # Get animatic frame for this chunk (map to beat) - only if available
        animatic_frame_url = None
        if not use_text_to_video and animatic_urls:
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
        # Distribute uploaded assets across chunks for variety
        # Strategy: If we have multiple uploaded images, cycle through them
        # If we have fewer images than chunks, reuse them in a pattern
        chunk_reference_url = None
        
        if has_uploaded_assets:
            # Distribute uploaded images across chunks
            # For chunk 0: use first image
            # For other chunks: cycle through available images
            asset_index = chunk_num % len(uploaded_assets)
            selected_asset = uploaded_assets[asset_index]
            chunk_reference_url = selected_asset.get('s3_url') or selected_asset.get('s3_key')
            uploaded_asset_url = chunk_reference_url  # Store for this specific chunk
            print(f"   📸 Chunk {chunk_num}: Using uploaded image {asset_index + 1}/{len(uploaded_assets)}")
        else:
            uploaded_asset_url = None
            if chunk_num == 0:
                # Chunk 0: Use style guide or product reference
                chunk_reference_url = style_guide_url or product_reference_url
            else:
                # Other chunks: Use product reference if available
                chunk_reference_url = product_reference_url
        
        chunk_spec = ChunkSpec(
            video_id=video_id,
            chunk_num=chunk_num,
            start_time=start_time,
            duration=duration_actual,
            beat=beat,
            animatic_frame_url=animatic_frame_url,  # None if using text-to-video
            style_guide_url=chunk_reference_url,  # Use uploaded asset or generated reference
            product_reference_url=product_reference_url,
            previous_chunk_last_frame=None,  # Will be set after previous chunk generates
            uploaded_asset_url=uploaded_asset_url if has_uploaded_assets else None,  # Specific uploaded image for this chunk
            prompt=prompt,
            fps=spec.get('fps', 24),
            use_text_to_video=use_text_to_video  # Set based on whether animatic_urls is empty
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
            # ============ IMAGE-TO-VIDEO MODE (Existing Code) ============
            try:
                print(f"Generating chunk {chunk_num} with image-to-video...")
                
                # Download animatic frame from S3
                animatic_key = chunk_spec_obj.animatic_frame_url.replace(f's3://{s3_client.bucket}/', '')
                animatic_path = s3_client.download_temp(animatic_key)
                temp_files.append(animatic_path)
                
                # Download style guide if chunk 0
                style_guide_path = None
                if chunk_num == 0 and chunk_spec_obj.style_guide_url:
                    style_guide_key = chunk_spec_obj.style_guide_url.replace(f's3://{s3_client.bucket}/', '')
                    style_guide_path = s3_client.download_temp(style_guide_key)
                    temp_files.append(style_guide_path)
                
                # Download previous chunk's last frame if chunk > 0
                previous_frame_path = None
                if chunk_num > 0 and chunk_spec_obj.previous_chunk_last_frame:
                    prev_frame_key = chunk_spec_obj.previous_chunk_last_frame.replace(f's3://{s3_client.bucket}/', '')
                    previous_frame_path = s3_client.download_temp(prev_frame_key)
                    temp_files.append(previous_frame_path)
                
                # Create composite image
                composite_path = create_reference_composite(
                    animatic_path=animatic_path,
                    style_guide_path=style_guide_path,
                    previous_frame_path=previous_frame_path,
                    animatic_weight=0.7 if chunk_num == 0 else 0.3,
                    style_weight=0.3 if chunk_num == 0 else 0.0,
                    temporal_weight=0.7 if chunk_num > 0 else 0.0
                )
                temp_files.append(composite_path)
                
                # Image-to-video using model config
                # Replicate accepts file paths or file objects
                # Open file in binary mode for Replicate
                with open(composite_path, 'rb') as img_file:
                    try:
                        print(f"   Trying model: {model_name} (image-to-video)...")
                        
                        # Get model-specific parameter names (e.g., hailuo uses 'first_frame_image' instead of 'image')
                        param_names = model_config.get('param_names', {})
                        image_param_name = param_names.get('image', 'image')  # Default to 'image' if not specified
                        
                        # Use model config parameters
                        # Timeout: 5 minutes per chunk (should be enough for video generation)
                        input_params = {
                            image_param_name: img_file,  # Use model-specific parameter name
                            "prompt": prompt,
                            "num_frames": num_frames,
                            "fps": fps,
                        }
                        
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
        # Since wan-2.1-i2v-480p requires an image, we use reference assets from Phase 3
        if use_text_to_video or image_to_video_failed:
            print(f"Generating chunk {chunk_num} with image-to-video using reference assets...")
            
            # Since we're skipping Phase 2 (animatic), use Phase 3 reference assets as input
            # For chunk 0: use style_guide_url or product_reference_url
            # For chunk 1+: use previous chunk's last frame (already handled above)
            
            input_image_path = None
            
            if chunk_num == 0:
                # Chunk 0: Prioritize uploaded assets (user images like Kobe photos), then style guide, then product reference
                if chunk_spec_obj.style_guide_url:
                    # Extract S3 key (handle both s3:// URLs and direct keys)
                    ref_url = chunk_spec_obj.style_guide_url
                    if ref_url.startswith('s3://'):
                        ref_key = ref_url.replace(f's3://{s3_client.bucket}/', '')
                    elif ref_url.startswith('http'):
                        # If it's a presigned URL, extract the key from the path
                        # Presigned URLs have the key in the path: /bucket/key
                        ref_key = ref_url.split(f'{s3_client.bucket}/', 1)[-1].split('?')[0]
                    else:
                        ref_key = ref_url
                    
                    input_image_path = s3_client.download_temp(ref_key)
                    temp_files.append(input_image_path)
                    
                    # Determine source type for logging
                    if 'uploaded_assets' in ref_key:
                        print(f"   📸 Using uploaded reference image (e.g., Kobe photo) as input")
                    elif 'style_guide' in ref_key:
                        print(f"   Using style guide from Phase 3 as input image")
                    else:
                        print(f"   Using reference image from Phase 3 as input")
                elif chunk_spec_obj.product_reference_url:
                    product_ref_url = chunk_spec_obj.product_reference_url
                    if product_ref_url.startswith('s3://'):
                        product_ref_key = product_ref_url.replace(f's3://{s3_client.bucket}/', '')
                    elif product_ref_url.startswith('http'):
                        product_ref_key = product_ref_url.split(f'{s3_client.bucket}/', 1)[-1].split('?')[0]
                    else:
                        product_ref_key = product_ref_url
                    
                    input_image_path = s3_client.download_temp(product_ref_key)
                    temp_files.append(input_image_path)
                    print(f"   Using product reference from Phase 3 as input image")
                else:
                    raise PhaseException(
                        "No animatic frames (Phase 2 skipped) and no reference assets (Phase 3) available. "
                        "Cannot generate video without an input image."
                    )
            elif chunk_spec_obj.previous_chunk_last_frame:
                # Chunk 1+: Use previous chunk's last frame OR uploaded asset (if provided)
                # If we have an uploaded asset for this chunk, use it; otherwise use previous frame
                if chunk_spec_obj.uploaded_asset_url:
                    # Use the specific uploaded image assigned to this chunk
                    uploaded_url = chunk_spec_obj.uploaded_asset_url
                    if uploaded_url.startswith('s3://'):
                        uploaded_key = uploaded_url.replace(f's3://{s3_client.bucket}/', '')
                    elif uploaded_url.startswith('http'):
                        uploaded_key = uploaded_url.split(f'{s3_client.bucket}/', 1)[-1].split('?')[0]
                    else:
                        uploaded_key = uploaded_url
                    
                    input_image_path = s3_client.download_temp(uploaded_key)
                    temp_files.append(input_image_path)
                    print(f"   📸 Using uploaded image for chunk {chunk_num} (from multiple images)")
                else:
                    # Fallback to previous chunk's last frame for temporal consistency
                    prev_frame_key = chunk_spec_obj.previous_chunk_last_frame.replace(f's3://{s3_client.bucket}/', '')
                    input_image_path = s3_client.download_temp(prev_frame_key)
                    temp_files.append(input_image_path)
                    print(f"   Using previous chunk's last frame as input image")
            else:
                raise PhaseException(
                    f"Chunk {chunk_num} requires previous chunk's last frame or uploaded asset, but neither is available"
                )
            
            # Generate video using the input image
            try:
                print(f"   Trying image-to-video model: {model_name}...")
                
                # Get model-specific parameter names (e.g., hailuo uses 'first_frame_image' instead of 'image')
                param_names = model_config.get('param_names', {})
                image_param_name = param_names.get('image', 'image')  # Default to 'image' if not specified
                
                # Open image file for Replicate
                with open(input_image_path, 'rb') as img_file:
                    input_params = {
                        image_param_name: img_file,  # Use model-specific parameter name
                        "prompt": prompt,
                        "num_frames": num_frames,
                        "fps": fps,
                    }
                    
                    output = replicate_client.run(
                        model_name,
                        input=input_params,
                        timeout=300  # 5 minutes timeout
                    )
                
                print(f"   ✅ Success with image-to-video using reference assets ({model_name})")
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                print(f"   ❌ Image-to-video failed ({error_type}): {str(e)}")
                raise PhaseException(f"Image-to-video generation failed: {str(e)}")
            
            if output is None:
                raise PhaseException(f"Image-to-video generation failed. Last error: {str(last_error)}")
        
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
