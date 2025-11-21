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
    reference_mapping: Dict = None,
    user_assets: list = None
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
        reference_mapping: Optional dict mapping beat_id to reference assets (from Phase 1)
        user_assets: Optional list of user asset dicts (from Phase 0) for metadata lookup
        
    Returns:
        Dictionary with:
            - beat_id: Beat identifier
            - beat_index: Index in sequence
            - start: Start time in seconds
            - duration: Duration in seconds
            - image_url: S3 URL of generated image
            - shot_type: Shot type from beat
            - prompt_used: Full prompt that was used for generation
            - referenced_asset_ids: List of asset IDs used (for usage tracking)
    """
    
    # Extract base prompt from beat template
    base_prompt = beat.get('prompt_template', '')
    
    # Extract style information
    color_palette = style.get('color_palette', [])
    colors_str = ', '.join(color_palette) if color_palette else 'neutral tones'
    lighting = style.get('lighting', 'soft')
    aesthetic = style.get('aesthetic', 'cinematic')
    shot_type = beat.get('shot_type', 'medium')
    
    # Track which assets are referenced for this beat
    referenced_asset_ids = []
    
    # Check if this beat has reference assets in the mapping
    beat_id = beat.get('beat_id')
    reference_info = None
    if reference_mapping and beat_id and beat_id in reference_mapping:
        reference_info = reference_mapping[beat_id]
        logger.info(f"Beat {beat_id} has reference mapping: {reference_info}")
    
    # Enhance prompt with reference asset information
    reference_prompt_parts = []
    if reference_info and user_assets:
        asset_ids = reference_info.get('asset_ids', [])
        usage_type = reference_info.get('usage_type', 'product')
        
        # Look up asset details from user_assets list
        for asset_id in asset_ids:
            asset = next((a for a in user_assets if a.get('asset_id') == asset_id), None)
            if asset:
                referenced_asset_ids.append(asset_id)
                
                # Extract asset metadata
                primary_object = asset.get('primary_object', '')
                asset_name = asset.get('name', '')
                asset_colors = asset.get('colors', [])
                asset_style_tags = asset.get('style_tags', [])
                
                # Build reference description based on usage type
                if usage_type == 'product':
                    if primary_object:
                        reference_prompt_parts.append(f"featuring {primary_object}")
                    elif asset_name:
                        reference_prompt_parts.append(f"featuring {asset_name}")
                    
                    # Add style tags if available
                    if asset_style_tags:
                        style_str = ', '.join(asset_style_tags[:3])  # Limit to 3 tags
                        reference_prompt_parts.append(f"{style_str} style")
                    
                elif usage_type == 'logo':
                    if asset_name:
                        reference_prompt_parts.append(f"with {asset_name} logo visible")
                    else:
                        reference_prompt_parts.append("with brand logo prominent")
                    reference_prompt_parts.append("brand identity clear")
                
                # Merge asset colors into palette if available
                if asset_colors:
                    # Prepend asset colors to existing palette (give them priority)
                    color_palette = asset_colors[:2] + color_palette  # Take top 2 colors from asset
                    colors_str = ', '.join(color_palette[:5])  # Limit to 5 total colors
                    logger.info(f"Enhanced color palette with asset colors: {colors_str}")
                
                logger.info(
                    f"Enhanced prompt with {usage_type} reference: {asset_name or primary_object} "
                    f"(asset_id: {asset_id})"
                )
    
    # Compose full prompt with reference enhancements
    prompt_parts = [base_prompt]
    
    # Add reference descriptions
    if reference_prompt_parts:
        prompt_parts.extend(reference_prompt_parts)
    
    # Add style information
    prompt_parts.append(f"{colors_str} color palette")
    prompt_parts.append(f"{lighting} lighting")
    prompt_parts.append(f"{aesthetic} aesthetic")
    prompt_parts.append("cinematic composition")
    prompt_parts.append("high quality professional photography")
    prompt_parts.append("1280x720 aspect ratio")
    prompt_parts.append(f"{shot_type} shot framing")
    
    full_prompt = ', '.join(prompt_parts)
    
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
        
        # Upload to S3 using user-scoped structure
        if not user_id:
            raise PhaseException("user_id is required for S3 uploads")
        
        s3_key = get_video_s3_key(user_id, video_id, f"beat_{beat_index:02d}.png")
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
            "shot_type": shot_type,
            "prompt_used": full_prompt,
            "referenced_asset_ids": referenced_asset_ids  # Track which assets were used
        }
        
    except Exception as e:
        # Cleanup temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        raise PhaseException(f"Failed to generate storyboard image for beat {beat_index}: {str(e)}")

