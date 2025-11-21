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
        conditioning_scale: float = 0.75,
        aspect_ratio: str = "16:9"
    ) -> str:
        """
        Generate image using flux-dev-controlnet with control image.
        
        Args:
            prompt: Text prompt for generation
            control_image_path: Path to control image (preprocessed edge map)
            conditioning_scale: Control strength (0.5-1.0, default 0.75)
            aspect_ratio: Aspect ratio (default "16:9" for 1280x720)
            
        Returns:
            URL of generated image
        """
        from app.services.replicate import replicate_client
        
        try:
            # Open control image as file handle for Replicate
            with open(control_image_path, 'rb') as control_file:
                logger.info(f"Generating image with flux-dev-controlnet: {prompt[:80]}...")
                
                output = replicate_client.run(
                    "xlabs-ai/flux-dev-controlnet",
                    input={
                        "prompt": prompt,
                        "image": control_file,
                        "conditioning_scale": conditioning_scale,
                        "aspect_ratio": aspect_ratio,
                        "output_format": "png",
                        "output_quality": 90,
                        "num_inference_steps": 30,
                        "controlnet_type": "canny"
                    },
                    timeout=120  # ControlNet takes longer
                )
                
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

