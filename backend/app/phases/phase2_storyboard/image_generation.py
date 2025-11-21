"""
Image generation helper for Phase 2 storyboard generation.

Generates one image per beat using FLUX Dev model (same as Phase 3).
"""

import os
import tempfile
import requests
import logging
from typing import Dict
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.common.constants import get_video_s3_key
from app.common.exceptions import PhaseException

logger = logging.getLogger(__name__)


def generate_beat_image(
    video_id: str,
    beat_index: int,
    beat: Dict,
    style: Dict,
    product: Dict,
    user_id: str,
    version: int = 1
) -> Dict:
    """
    Generate a storyboard image for a single beat.

    Uses FLUX Dev model (same as Phase 3) to generate high-quality storyboard images.
    Image is uploaded to S3 and URL is returned.

    Args:
        video_id: Unique video generation ID
        beat_index: Index of beat in sequence (0-based)
        beat: Beat dictionary with beat_id, duration, prompt_template, shot_type, etc.
        style: Style specification with color_palette, lighting, aesthetic, etc.
        product: Product specification with name, category, etc.
        user_id: User ID for organizing outputs in S3
        version: Version number for artifact versioning (default: 1)

    Returns:
        Dictionary with:
            - beat_id: Beat identifier
            - beat_index: Index in sequence
            - start: Start time in seconds
            - duration: Duration in seconds
            - image_url: S3 URL of generated image
            - s3_key: S3 key for the uploaded image
            - shot_type: Shot type from beat
            - prompt_used: Full prompt that was used for generation
    """
    
    # Extract base prompt from beat template
    base_prompt = beat.get('prompt_template', '')
    
    # Extract style information
    color_palette = style.get('color_palette', [])
    colors_str = ', '.join(color_palette) if color_palette else 'neutral tones'
    lighting = style.get('lighting', 'soft')
    aesthetic = style.get('aesthetic', 'cinematic')
    shot_type = beat.get('shot_type', 'medium')
    
    # Compose full prompt
    full_prompt = (
        f"{base_prompt}, "
        f"{colors_str} color palette, "
        f"{lighting} lighting, "
        f"{aesthetic} aesthetic, "
        f"cinematic composition, "
        f"high quality professional photography, "
        f"1280x720 aspect ratio, "
        f"{shot_type} shot framing"
    )
    
    # Create negative prompt
    negative_prompt = (
        "blurry, low quality, distorted, deformed, ugly, amateur, "
        "watermark, text, signature, letters, words, "
        "multiple subjects, cluttered, busy, messy, chaotic"
    )
    
    logger.info(
        f"Generating storyboard image for beat {beat_index} ({beat.get('beat_id', 'unknown')}): "
        f"{full_prompt[:100]}..."
    )
    
    try:
        # Call Replicate FLUX Dev model (same as Phase 3)
        # Cost: $0.025/image (better quality than SDXL)
        logger.info(f"   Using Replicate FLUX Dev model...")
        output = replicate_client.run(
            "black-forest-labs/flux-dev",
            input={
                "prompt": full_prompt,
                "aspect_ratio": "16:9",  # 1280x720 aspect ratio
                "output_format": "png",
                "output_quality": 90,  # High quality for storyboards
            },
            timeout=60
        )
        
        # Extract image URL from output
        # FLUX Dev returns a URL or list of URLs
        if isinstance(output, str):
            image_url = output
        elif isinstance(output, list) and len(output) > 0:
            image_url = output[0]
        else:
            # Handle iterator/other formats
            image_url = list(output)[0] if hasattr(output, '__iter__') else str(output)
        
        # Download image
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        
        # Save to temp file
        temp_path = tempfile.mktemp(suffix='.png')
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        # Upload to S3 using user-scoped structure with versioning
        if not user_id:
            raise PhaseException("user_id is required for S3 uploads")

        # Include version in S3 key: beat_00_v1.png, beat_00_v2.png, etc.
        s3_key = get_video_s3_key(user_id, video_id, f"beat_{beat_index:02d}_v{version}.png")
        s3_url = s3_client.upload_file(temp_path, s3_key)

        logger.info(f"✅ Uploaded storyboard image to S3: {s3_url[:80]}...")

        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)

        # Return beat image info
        return {
            "beat_id": beat.get('beat_id'),
            "beat_index": beat_index,
            "start": beat.get('start', 0),
            "duration": beat.get('duration', 5),
            "image_url": s3_url,
            "s3_key": s3_key,  # Include S3 key for checkpoint artifact tracking
            "shot_type": shot_type,
            "prompt_used": full_prompt
        }
        
    except Exception as e:
        # Cleanup temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        raise PhaseException(f"Failed to generate storyboard image for beat {beat_index}: {str(e)}")

