from typing import List, Dict
import tempfile
import os
import requests
from app.services import replicate_client, s3_client
from app.phases.phase2_animatic.prompts import (
    generate_animatic_prompt,
    create_negative_prompt,
)
from app.common.constants import COST_SDXL_IMAGE, S3_ANIMATIC_PREFIX


class AnimaticGenerationService:
    """Service for generating animatic frames using SDXL"""
    
    def __init__(self):
        """Initialize the service with clients and cost tracking"""
        self.replicate = replicate_client
        self.s3 = s3_client
        self.total_cost = 0.0
    
    def generate_frames(self, video_id: str, spec: Dict) -> List[str]:
        """
        Generate animatic frames for all beats in the spec.
        
        Args:
            video_id: Unique identifier for the video
            spec: Dictionary containing 'beats' and 'style' keys
            
        Returns:
            List of S3 URLs for generated frames
        """
        beats = spec.get("beats", [])
        style = spec.get("style", {})
        
        frame_urls = []
        total_frames = len(beats)
        
        print(f"Starting animatic generation for {total_frames} frames...")
        
        for frame_num, beat in enumerate(beats):
            print(f"Generating frame {frame_num + 1}/{total_frames} for beat: {beat.get('name', 'unknown')}")
            
            # Generate prompt
            prompt = generate_animatic_prompt(beat, style)
            negative_prompt = create_negative_prompt()
            
            # Generate single frame
            s3_url = self._generate_single_frame(
                video_id=video_id,
                frame_num=frame_num,
                prompt=prompt,
                negative_prompt=negative_prompt
            )
            
            frame_urls.append(s3_url)
            self.total_cost += COST_SDXL_IMAGE
        
        print(f"Completed animatic generation: {total_frames} frames, Total cost: ${self.total_cost:.4f}")
        
        return frame_urls
    
    def _generate_single_frame(
        self,
        video_id: str,
        frame_num: int,
        prompt: str,
        negative_prompt: str
    ) -> str:
        """
        Generate a single animatic frame using SDXL and upload to S3.
        
        Args:
            video_id: Unique identifier for the video
            frame_num: Frame number (0-indexed)
            prompt: Positive prompt for image generation
            negative_prompt: Negative prompt to avoid unwanted details
            
        Returns:
            S3 URL of the uploaded frame
            
        Raises:
            Exception: If frame generation or upload fails
        """
        try:
            # Generate image using SDXL
            output = self.replicate.run(
                "stability-ai/sdxl:latest",
                input={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": 512,
                    "height": 512,
                    "num_inference_steps": 20,
                    "guidance_scale": 7.0,
                    "num_outputs": 1,
                }
            )
            
            # Extract image URL from output
            image_url = output[0]
            
            # Download image data
            response = requests.get(image_url)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(response.content)
                tmp_file_path = tmp_file.name
            
            # Construct S3 key
            s3_key = f"videos/{video_id}/{S3_ANIMATIC_PREFIX}/frame_{frame_num:02d}.png"
            
            # Upload to S3
            s3_url = self.s3.upload_file(tmp_file_path, s3_key)
            
            print(f"Frame {frame_num} uploaded successfully: {s3_url}")
            
            # Clean up temporary file
            os.unlink(tmp_file_path)
            
            return s3_url
            
        except Exception as e:
            raise Exception(f"Failed to generate frame {frame_num}: {str(e)}")
