# Phase 4: Chunk Generation with Image Compositing
import os
import tempfile
import subprocess
import requests
from typing import Optional, List, Dict
from PIL import Image

from app.orchestrator.celery_app import celery_app
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.phases.phase4_chunks.schemas import ChunkSpec
from app.common.constants import COST_WAN_480P_VIDEO, S3_CHUNKS_PREFIX
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
    # For short videos (5-10s ads), use shorter chunks (1-1.5s) for faster generation
    # For longer videos, use standard 2s chunks
    if duration <= 10:
        chunk_duration = 1.5  # 1.5 seconds per chunk for short ads
        chunk_overlap = 0.3  # 0.3 seconds overlap
    elif duration <= 20:
        chunk_duration = 1.8  # 1.8 seconds per chunk for medium videos
        chunk_overlap = 0.4  # 0.4 seconds overlap
    else:
        chunk_duration = 2.0  # 2 seconds per chunk for longer videos
        chunk_overlap = 0.5  # 0.5 seconds overlap
    
    chunk_count = int((duration + chunk_overlap) / (chunk_duration - chunk_overlap))
    
    # Ensure we have enough animatic frames
    if len(animatic_urls) < len(beats):
        raise PhaseException(f"Not enough animatic frames: {len(animatic_urls)} < {len(beats)}")
    
    chunk_specs = []
    style_guide_url = reference_urls.get('style_guide_url')
    product_reference_url = reference_urls.get('product_reference_url')
    
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
        
        # Get animatic frame for this chunk (map to beat)
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
            animatic_frame_url=animatic_frame_url,
            style_guide_url=style_guide_url if chunk_num == 0 else None,
            product_reference_url=product_reference_url,
            previous_chunk_last_frame=None,  # Will be set after previous chunk generates
            prompt=prompt,
            fps=spec.get('fps', 24)
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
    
    temp_files = []  # Track temp files for cleanup
    
    try:
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
        
        # Build prompt (already formatted in build_chunk_specs)
        prompt = chunk_spec_obj.prompt
        
        # Call Replicate Zeroscope model
        print(f"Generating chunk {chunk_num} with Zeroscope...")
        
        # Replicate accepts file paths or file objects
        # Open file in binary mode for Replicate
        with open(composite_path, 'rb') as img_file:
              # Calculate frames based on chunk duration and fps from chunk spec
              fps = chunk_spec_obj.fps
              chunk_duration = chunk_spec_obj.duration
              num_frames = int(chunk_duration * fps)
              
              # Image-to-video models for ad generation
              # PRD recommends: Zeroscope (dev) or AnimateDiff (final)
              # Try models in order of preference (cost, quality, availability)
              # Note: stability-ai/stable-video-diffusion returns 404, using wan-2.1 as primary
              model_variants = [
                  "wavespeedai/wan-2.1-i2v-480p",  # Primary: Wan 2.1 (verified working, open source)
              ]
              
              output = None
              last_error = None
              
              for model_name in model_variants:
                  try:
                      print(f"   Trying model: {model_name}...")
                      
                      # Wan 2.1 Image-to-Video parameters (only working model)
                      # Timeout: 5 minutes per chunk (should be enough for video generation)
                      output = replicate_client.run(
                          model_name,
                          input={
                              "image": img_file,
                              "prompt": prompt,
                              "num_frames": min(num_frames, 80),  # Wan supports up to 80 frames
                              "fps": fps,
                          },
                          timeout=300  # 5 minutes timeout
                      )
                      
                      print(f"   ✅ Success with {model_name}")
                      break
                  except Exception as e:
                      last_error = e
                      error_msg = str(e).lower()
                      error_type = type(e).__name__
                      # Check for 404, not found, or any HTTP/API error - catch all and try next
                      if any(keyword in error_msg for keyword in ["404", "not found", "422", "requested resource", "does not exist", "permission"]):
                          print(f"   ⚠️  {model_name} failed ({error_type}: {str(e)[:80]}...), trying next model...")
                          continue
                      # For any other error on first model, try next; on last model, raise
                      elif model_name == model_variants[-1]:
                          # Last model failed, raise the error
                          print(f"   ❌ All models failed. Last error ({error_type}): {str(e)}")
                          raise
                      else:
                          # Not last model, try next
                          print(f"   ⚠️  {model_name} error ({error_type}): {str(e)[:80]}..., trying next...")
                          continue
              
              if output is None:
                  raise PhaseException(f"All video generation models failed. Last error: {str(last_error)}")
        
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
        
        # Calculate actual cost: wan-2.1-480p is $0.09 per second of video
        chunk_duration = chunk_spec_obj.duration
        chunk_cost = chunk_duration * COST_WAN_480P_VIDEO
        
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
