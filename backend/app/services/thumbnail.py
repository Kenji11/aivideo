"""
Thumbnail Service for Video Generation

Extracts first frame from videos and generates thumbnails for the My Projects page.
"""

import os
import tempfile
import subprocess
import logging
from PIL import Image
from app.services.s3 import s3_client
from app.common.constants import get_video_s3_key
from app.common.exceptions import PhaseException

logger = logging.getLogger(__name__)


class ThumbnailService:
    """Service for generating video thumbnails"""
    
    def extract_first_frame(self, video_path: str) -> str:
        """
        Extract the first frame from a video using FFmpeg.
        
        Args:
            video_path: Path to input video file
            
        Returns:
            Path to extracted frame image (PNG)
            
        Raises:
            PhaseException: If FFmpeg extraction fails
        """
        output_path = tempfile.mktemp(suffix='.png')
        
        try:
            # Use FFmpeg to extract first frame
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vframes', '1',  # Extract only first frame
                '-q:v', '2',  # High quality
                '-y',  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise PhaseException(f"FFmpeg failed to extract first frame: {result.stderr}")
            
            if not os.path.exists(output_path):
                raise PhaseException("FFmpeg did not create output file")
            
            logger.info(f"Extracted first frame from {video_path} -> {output_path}")
            return output_path
            
        except subprocess.TimeoutExpired:
            raise PhaseException("FFmpeg timeout while extracting first frame")
        except Exception as e:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            raise PhaseException(f"Failed to extract first frame: {str(e)}")
    
    def resize_to_thumbnail(self, image_path: str, width: int = 640, height: int = 360) -> str:
        """
        Resize image to thumbnail size (16:9 aspect ratio).
        
        Args:
            image_path: Path to input image
            width: Target width (default 640)
            height: Target height (default 360)
            
        Returns:
            Path to resized thumbnail image (JPEG)
        """
        output_path = tempfile.mktemp(suffix='.jpg')
        
        try:
            # Open image
            img = Image.open(image_path)
            
            # Resize maintaining aspect ratio, then crop to exact size if needed
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            # Create new image with exact dimensions (16:9)
            thumbnail = Image.new('RGB', (width, height), (0, 0, 0))  # Black background
            
            # Center the resized image
            if img.size[0] < width or img.size[1] < height:
                # Image is smaller, center it
                x_offset = (width - img.size[0]) // 2
                y_offset = (height - img.size[1]) // 2
                thumbnail.paste(img, (x_offset, y_offset))
            else:
                # Image is larger, crop to center
                x_offset = (img.size[0] - width) // 2
                y_offset = (img.size[1] - height) // 2
                thumbnail = img.crop((x_offset, y_offset, x_offset + width, y_offset + height))
            
            # Save as JPEG with quality 85
            thumbnail.save(output_path, 'JPEG', quality=85, optimize=True)
            
            logger.info(f"Resized thumbnail: {image_path} -> {output_path} ({width}x{height})")
            return output_path
            
        except Exception as e:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except:
                    pass
            raise PhaseException(f"Failed to resize thumbnail: {str(e)}")
    
    def generate_video_thumbnail(self, video_path: str, user_id: str, video_id: str) -> str:
        """
        Generate thumbnail from video and upload to S3.
        
        Args:
            video_path: Path to video file (first chunk)
            user_id: User ID for S3 organization
            video_id: Video ID for S3 organization
            
        Returns:
            S3 URL of uploaded thumbnail
            
        Raises:
            PhaseException: If any step fails
        """
        frame_path = None
        thumbnail_path = None
        
        try:
            # Extract first frame
            frame_path = self.extract_first_frame(video_path)
            
            # Resize to thumbnail
            thumbnail_path = self.resize_to_thumbnail(frame_path, width=640, height=360)
            
            # Upload to S3
            thumbnail_key = get_video_s3_key(user_id, video_id, "thumbnail.jpg")
            thumbnail_s3_url = s3_client.upload_file(thumbnail_path, thumbnail_key)
            
            logger.info(f"Generated and uploaded thumbnail: {thumbnail_s3_url}")
            return thumbnail_s3_url
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnail: {str(e)}", exc_info=True)
            raise PhaseException(f"Failed to generate video thumbnail: {str(e)}")
            
        finally:
            # Cleanup temp files
            for temp_file in [frame_path, thumbnail_path]:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass


# Singleton instance
thumbnail_service = ThumbnailService()

