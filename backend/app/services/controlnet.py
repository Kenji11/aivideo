"""
ControlNet Service for Image Generation

Provides preprocessing (Canny edge detection) and generation using flux-dev-controlnet
for product consistency in storyboard images.
"""

import os
import cv2
import tempfile
import logging
from typing import Optional
from PIL import Image
import numpy as np
from app.services.s3 import s3_client
from app.common.exceptions import PhaseException

logger = logging.getLogger(__name__)


class ControlNetService:
    """Service for ControlNet preprocessing and image generation"""
    
    def preprocess_for_controlnet(self, image_path: str, method: str = "canny") -> str:
        """
        Preprocess image for ControlNet by extracting edges.
        
        Args:
            image_path: Path to input image file
            method: Preprocessing method (currently only "canny" supported)
            
        Returns:
            Path to preprocessed edge image
        """
        if method != "canny":
            raise PhaseException(f"Unsupported preprocessing method: {method}")
        
        try:
            # Load image with OpenCV
            img = cv2.imread(image_path)
            if img is None:
                raise PhaseException(f"Failed to load image: {image_path}")
            
            # Convert to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply Canny edge detection
            edges = cv2.Canny(gray, 100, 200)
            
            # Convert to 3-channel image (ControlNet requirement)
            edges_3channel = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
            
            # Save to temp file
            temp_path = tempfile.mktemp(suffix='.png')
            cv2.imwrite(temp_path, edges_3channel)
            
            logger.info(f"Preprocessed image for ControlNet: {image_path} -> {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error preprocessing image for ControlNet: {str(e)}", exc_info=True)
            raise PhaseException(f"Failed to preprocess image for ControlNet: {str(e)}")
    
    def generate_with_controlnet(
        self,
        prompt: str,
        control_image_path: str,
        control_strength: float = 0.5,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
        steps: int = 40,
        guidance_scale: float = 4.0,
        reference_image_path: Optional[str] = None,
        image_to_image_strength: Optional[float] = None
    ) -> str:
        """
        Generate image using flux-dev-controlnet with control image.
        
        Args:
            prompt: Text prompt for generation
            control_image_path: Path to control image (preprocessed edge map)
            control_strength: Control strength (0.5 recommended for Canny, default 0.5)
            aspect_ratio: Aspect ratio (default "16:9" for 1280x720)
            negative_prompt: Optional negative prompt to avoid unwanted elements
            steps: Number of inference steps (default 40, max 50 for better quality)
            guidance_scale: Guidance scale (default 4.0, max 5.0 for better quality)
            reference_image_path: Optional path to original reference image for image-to-image
            image_to_image_strength: Optional strength for image-to-image (0-1, recommended 0-0.25)
            
        Returns:
            URL of generated image
        """
        from app.services.replicate import replicate_client
        
        try:
            logger.info(f"Generating image with flux-dev-controlnet: {prompt[:80]}...")
            
            # Open control image and reference image (if provided) as file handles for Replicate
            # Both files need to stay open during the API call
            control_file = open(control_image_path, 'rb')
            ref_file = None
            
            try:
                if reference_image_path and image_to_image_strength is not None:
                    ref_file = open(reference_image_path, 'rb')
                    logger.info(f"Using image-to-image with strength: {image_to_image_strength}")
                
                # Build input parameters
                input_params = {
                    "prompt": prompt,
                    "control_image": control_file,
                    "control_type": "canny",
                    "control_strength": control_strength,
                    "aspect_ratio": aspect_ratio,
                    "output_format": "png",
                    "output_quality": 100,
                    "steps": steps,
                    "guidance_scale": guidance_scale
                }
                
                # Add reference image for image-to-image if provided
                if ref_file:
                    input_params["image"] = ref_file
                    input_params["image_to_image_strength"] = image_to_image_strength
                
                # Add negative prompt if provided
                if negative_prompt:
                    input_params["negative_prompt"] = negative_prompt
                
                output = replicate_client.run(
                    "xlabs-ai/flux-dev-controlnet",
                    input=input_params,
                    timeout=120  # ControlNet takes longer
                )
            finally:
                # Close files after API call
                control_file.close()
                if ref_file:
                    ref_file.close()
            
            # Extract image URL from output
            if isinstance(output, str):
                image_url = output
            elif isinstance(output, list) and len(output) > 0:
                image_url = output[0]
            else:
                image_url = list(output)[0] if hasattr(output, '__iter__') else str(output)
            
            logger.info(f"✅ Generated image with ControlNet: {image_url[:80]}...")
            return image_url
                
        except Exception as e:
            logger.error(f"Error generating image with ControlNet: {str(e)}", exc_info=True)
            raise PhaseException(f"Failed to generate image with ControlNet: {str(e)}")


# Singleton instance
controlnet_service = ControlNetService()

