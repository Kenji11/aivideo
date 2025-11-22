"""
Background Removal Service using Replicate's recraft-remove-background model

Removes backgrounds from product images automatically during asset upload.
"""
import logging
import tempfile
import os
import requests
from typing import Optional
from PIL import Image
import replicate
from app.config import get_settings
from app.services.s3 import s3_client
from app.common.constants import COST_RECRAFT_REMOVE_BG

logger = logging.getLogger(__name__)

settings = get_settings()

# Replicate model identifier - UPDATE THIS with the correct model identifier from Replicate
# Located on line 25 - change RECRAFT_REMOVE_BG_MODEL value
RECRAFT_REMOVE_BG_MODEL = "recraft-ai/recraft-remove-background"


class BackgroundRemovalService:
    """Service for removing backgrounds from product images"""
    
    def __init__(self):
        self.model = RECRAFT_REMOVE_BG_MODEL
        self.timeout = 120  # 2 minutes timeout for background removal
        self.max_retries = 2
    
    def remove_background(
        self,
        image_url: str,
        s3_key: str
    ) -> Optional[str]:
        """
        Remove background from an image using Replicate's recraft-remove-background model.
        
        Downloads the image, processes it through Replicate, then uploads the result
        back to S3 at the same key (overwriting the original).
        
        Args:
            image_url: Presigned S3 URL or direct URL to the image
            s3_key: S3 key where the processed image should be uploaded (overwrites original)
            
        Returns:
            S3 URL of the processed image, or None if processing failed
            
        Raises:
            Exception: If background removal fails after retries
        """
        temp_input_path = None
        temp_output_path = None
        
        try:
            logger.info(f"Starting background removal for image: {s3_key}")
            
            # Step 1: Download image from S3 to temporary file
            temp_input_path = s3_client.download_file(s3_key)
            logger.debug(f"Downloaded image to: {temp_input_path}")
            
            # Step 2: Call Replicate API to remove background
            logger.info(f"Calling Replicate model {self.model} for background removal...")
            
            # Open image file for Replicate API (keep open during call)
            image_file = open(temp_input_path, 'rb')
            try:
                output = replicate.run(
                    self.model,
                    input={
                        "image": image_file
                    }
                )
                
                # Handle output format (can be string URL, iterator, or list)
                if isinstance(output, str):
                    output_url = output
                elif hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
                    # Convert iterator/list to list and get first item
                    output_list = list(output)
                    output_url = output_list[0] if output_list else None
                elif isinstance(output, dict):
                    # Try common keys for output
                    output_url = output.get('output') or output.get('url') or output.get('image')
                else:
                    output_url = str(output) if output else None
            finally:
                image_file.close()
            
            if not output_url:
                raise Exception("Replicate API returned no output URL")
            
            logger.info(f"Background removal complete. Output URL: {output_url}")
            
            # Step 3: Download processed image from Replicate
            temp_output_path = tempfile.mktemp(suffix='.png')
            response = requests.get(output_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(temp_output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.debug(f"Downloaded processed image to: {temp_output_path}")
            
            # Step 4: Verify the processed image is valid
            try:
                with Image.open(temp_output_path) as img:
                    # Ensure it's RGBA (has transparency)
                    if img.mode != 'RGBA':
                        # Convert to RGBA if needed
                        if img.mode == 'RGB':
                            # Add alpha channel
                            img = img.convert('RGBA')
                        else:
                            img = img.convert('RGBA')
                        
                        # Save converted image
                        img.save(temp_output_path, 'PNG')
                    
                    logger.debug(f"Processed image: {img.size[0]}x{img.size[1]}, mode: {img.mode}")
            except Exception as e:
                logger.error(f"Failed to validate processed image: {str(e)}")
                raise
            
            # Step 5: Upload processed image back to S3 (overwrite original)
            s3_url = s3_client.upload_file(temp_output_path, s3_key)
            logger.info(f"✓ Background removal complete. Uploaded to S3: {s3_key}")
            logger.info(f"  Cost: ${COST_RECRAFT_REMOVE_BG:.4f}")
            
            return s3_url
            
        except TimeoutError as e:
            logger.error(f"Background removal timed out for {s3_key}: {str(e)}")
            raise Exception(f"Background removal timed out: {str(e)}")
        except Exception as e:
            logger.error(f"Background removal failed for {s3_key}: {str(e)}", exc_info=True)
            raise Exception(f"Background removal failed: {str(e)}")
        finally:
            # Clean up temporary files
            for temp_path in [temp_input_path, temp_output_path]:
                if temp_path and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {temp_path}: {str(e)}")


# Singleton instance
background_removal_service = BackgroundRemovalService()

