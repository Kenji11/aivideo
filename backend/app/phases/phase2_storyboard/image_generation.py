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
from app.services.controlnet import controlnet_service
from app.common.constants import get_video_s3_key, COST_FLUX_DEV_IMAGE, COST_FLUX_DEV_CONTROLNET_IMAGE
from app.common.exceptions import PhaseException
from app.database import SessionLocal
from app.common.models import Asset

logger = logging.getLogger(__name__)

# Debug flag: Exit early after model decision (for debugging ControlNet selection)
DEBUG_EXIT_AFTER_MODEL_DECISION = False  # Set to True to enable debug mode


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
    
    # Debug logging
    logger.info(f"🔍 ControlNet Debug - Beat ID: {beat_id}")
    logger.info(f"🔍 ControlNet Debug - reference_mapping exists: {reference_mapping is not None}")
    if reference_mapping:
        logger.info(f"🔍 ControlNet Debug - reference_mapping keys: {list(reference_mapping.keys())}")
    logger.info(f"🔍 ControlNet Debug - user_assets exists: {user_assets is not None}")
    if user_assets:
        logger.info(f"🔍 ControlNet Debug - user_assets count: {len(user_assets)}")
    
    if reference_mapping and beat_id and beat_id in reference_mapping:
        reference_info = reference_mapping[beat_id]
        logger.info(f"✅ Beat {beat_id} has reference mapping: {reference_info}")
    else:
        logger.info(f"⚠️ Beat {beat_id} has NO reference mapping (reference_mapping={reference_mapping is not None}, beat_id={beat_id}, in_mapping={beat_id in reference_mapping if reference_mapping and beat_id else False})")
    
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
    
    # Determine if we should use ControlNet (if product reference exists)
    use_controlnet = False
    product_asset_id = None
    
    logger.info(f"🔍 ControlNet Decision - reference_info exists: {reference_info is not None}")
    logger.info(f"🔍 ControlNet Decision - user_assets exists: {user_assets is not None}")
    
    if reference_info and user_assets:
        asset_ids = reference_info.get('asset_ids', [])
        usage_type = reference_info.get('usage_type', '')
        
        logger.info(f"🔍 ControlNet Decision - asset_ids: {asset_ids}, usage_type: {usage_type}")
        
        # Use ControlNet if we have a product reference
        if usage_type == 'product' and asset_ids:
            product_asset_id = asset_ids[0]  # Use first product asset
            use_controlnet = True
            logger.info(f"   ✅ Using ControlNet with product asset: {product_asset_id}")
        else:
            logger.info(f"   ⚠️ Not using ControlNet - usage_type='{usage_type}' (needs 'product'), asset_ids={asset_ids}")
    else:
        logger.info(f"   ⚠️ Not using ControlNet - reference_info={reference_info is not None}, user_assets={user_assets is not None}")
    
    # DEBUG: Exit early after model decision
    if DEBUG_EXIT_AFTER_MODEL_DECISION:
        logger.info("=" * 80)
        logger.info("🔴 DEBUG MODE: Exiting early after model decision")
        logger.info(f"   Model selected: {'flux-dev-controlnet' if use_controlnet else 'flux-dev'}")
        logger.info(f"   Product asset ID: {product_asset_id}")
        logger.info(f"   Beat ID: {beat_id}")
        logger.info("=" * 80)
        raise PhaseException(f"DEBUG: Early exit after model decision - would use {'ControlNet' if use_controlnet else 'regular flux-dev'}")
    
    try:
        temp_path = None
        if use_controlnet and product_asset_id:
            # ControlNet path: Download product image, preprocess, generate with ControlNet
            db = SessionLocal()
            try:
                asset = db.query(Asset).filter(Asset.id == product_asset_id).first()
                if not asset or not asset.s3_url:
                    logger.warning(f"Product asset {product_asset_id} not found or missing S3 URL, falling back to regular flux-dev")
                    use_controlnet = False
                else:
                    # Download product image from S3
                    try:
                        product_image_path = s3_client.download_temp(asset.s3_url)
                        if not product_image_path or not os.path.exists(product_image_path):
                            logger.warning(f"Failed to download product image from {asset.s3_url}, falling back to regular flux-dev")
                            use_controlnet = False
                        else:
                            control_image_path = None
                            try:
                                # Preprocess for ControlNet (extract edges)
                                control_image_path = controlnet_service.preprocess_for_controlnet(
                                    product_image_path,
                                    method="canny"
                                )
                                
                                # Generate with ControlNet
                                generated_image_url = controlnet_service.generate_with_controlnet(
                                    prompt=full_prompt,
                                    control_image_path=control_image_path,
                                    conditioning_scale=0.75,
                                    aspect_ratio="16:9"
                                )
                                
                                # Download generated image
                                response = requests.get(generated_image_url, timeout=60)
                                response.raise_for_status()
                                
                                # Save to temp file
                                temp_path = tempfile.mktemp(suffix='.png')
                                with open(temp_path, 'wb') as f:
                                    f.write(response.content)
                                
                                logger.info(f"   ✅ Generated with ControlNet (cost: ${COST_FLUX_DEV_CONTROLNET_IMAGE:.4f})")
                            finally:
                                # Cleanup preprocessing temp files
                                if product_image_path and os.path.exists(product_image_path):
                                    os.remove(product_image_path)
                                if control_image_path and os.path.exists(control_image_path):
                                    os.remove(control_image_path)
                    except Exception as e:
                        logger.warning(f"Error downloading/preprocessing product image: {str(e)}, falling back to regular flux-dev")
                        use_controlnet = False
            finally:
                db.close()
        
        if not use_controlnet or temp_path is None:
            # Regular flux-dev path (no ControlNet)
            logger.info(f"   Using Replicate FLUX Dev model (no ControlNet)...")
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
            if isinstance(output, str):
                generated_image_url = output
            elif isinstance(output, list) and len(output) > 0:
                generated_image_url = output[0]
            else:
                generated_image_url = list(output)[0] if hasattr(output, '__iter__') else str(output)
            
            # Download image
            response = requests.get(generated_image_url, timeout=60)
            response.raise_for_status()
            
            # Save to temp file
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"   ✅ Generated with flux-dev (cost: ${COST_FLUX_DEV_IMAGE:.4f})")
        
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
            "referenced_asset_ids": referenced_asset_ids,  # Track which assets were used
            "used_controlnet": use_controlnet  # Track which generation path was used
        }
        
    except Exception as e:
        # Cleanup temp file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        
        raise PhaseException(f"Failed to generate storyboard image for beat {beat_index}: {str(e)}")

