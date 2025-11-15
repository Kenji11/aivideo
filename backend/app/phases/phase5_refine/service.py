# Phase 5: Refinement Service
import os
import tempfile
import requests
from typing import Dict, Tuple, Optional
from app.services.s3 import s3_client
from app.services.ffmpeg import ffmpeg_service
from app.services.replicate import replicate_client
from app.common.exceptions import PhaseException
from app.common.constants import COST_MUSICGEN


class RefinementService:
    """Service for refining and polishing video"""
    
    def __init__(self):
        self.total_cost = 0.0
    
    def refine_all(self, video_id: str, stitched_url: str, spec: dict) -> Tuple[str, Optional[str]]:
        """
        Refine video: upscale, color grade, add music, mix audio.
        
        Args:
            video_id: Unique video generation ID
            stitched_url: S3 URL of stitched video
            spec: Video specification
            
        Returns:
            Tuple of (refined_video_url, music_url)
        """
        temp_files = []
        
        try:
            # Step 1: Download stitched video
            print("   Downloading stitched video...")
            stitched_path = s3_client.download_temp(stitched_url)
            temp_files.append(stitched_path)
            
            # Step 2: Upscale to 1080p
            print("   Upscaling to 1080p...")
            upscaled_path = self._upscale_video(stitched_path)
            temp_files.append(upscaled_path)
            
            # Step 3: Generate background music
            print("   Generating background music...")
            music_path = None
            music_url = None
            try:
                music_path = self._generate_music(video_id, spec)
                if music_path:
                    temp_files.append(music_path)
                    # Upload music to S3
                    music_key = f"videos/{video_id}/music/background.mp3"
                    music_url = s3_client.upload_file(music_path, music_key)
                    self.total_cost += COST_MUSICGEN
            except Exception as e:
                print(f"   ⚠️  Music generation failed: {str(e)}, continuing without music")
            
            # Step 4: Mix audio (if music available)
            if music_path and os.path.exists(music_path):
                print("   Mixing audio...")
                final_path = self._mix_audio(upscaled_path, music_path)
                temp_files.append(final_path)
            else:
                final_path = upscaled_path
            
            # Step 5: Upload refined video
            print("   Uploading refined video...")
            refined_key = f"videos/{video_id}/refined/final_1080p.mp4"
            refined_url = s3_client.upload_file(final_path, refined_key)
            
            return refined_url, music_url
            
        except Exception as e:
            raise PhaseException(f"Refinement failed: {str(e)}")
        finally:
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass
    
    def _upscale_video(self, input_path: str) -> str:
        """Upscale video to 1080p using FFmpeg"""
        output_path = tempfile.mktemp(suffix='.mp4')
        
        # FFmpeg command to upscale to 1920x1080
        # Using lanczos scaling algorithm for quality
        command = [
            'ffmpeg',
            '-i', input_path,
            '-vf', 'scale=1920:1080:flags=lanczos',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',  # Copy audio as-is
            '-y',  # Overwrite output
            output_path
        ]
        
        try:
            ffmpeg_service.run_command(command)
            return output_path
        except Exception as e:
            raise PhaseException(f"Upscaling failed: {str(e)}")
    
    def _generate_music(self, video_id: str, spec: dict) -> Optional[str]:
        """Generate background music using MusicGen"""
        try:
            # Extract music style from spec
            audio_spec = spec.get('audio', {})
            music_style = audio_spec.get('music_style', 'orchestral')
            tempo = audio_spec.get('tempo', 'moderate')
            mood = audio_spec.get('mood', 'sophisticated')
            
            # Create prompt for music generation
            prompt = f"{music_style} music, {tempo} tempo, {mood} mood, background music for advertisement"
            
            print(f"   Generating music with prompt: {prompt}")
            
            # Use MusicGen via Replicate
            output = replicate_client.run(
                "meta/musicgen:671ac645ce5e552cc63a54c2e00c19a55811a06",
                input={
                    "model_version": "large",
                    "prompt": prompt,
                    "duration": 30,  # 30 seconds
                },
                timeout=180  # 3 minutes for music generation
            )
            
            # Download music file
            music_url = output if isinstance(output, str) else output[0]
            music_path = tempfile.mktemp(suffix='.mp3')
            
            response = requests.get(music_url, stream=True, timeout=60)
            response.raise_for_status()
            with open(music_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return music_path
            
        except Exception as e:
            print(f"   ⚠️  Music generation error: {str(e)}")
            return None
    
    def _mix_audio(self, video_path: str, music_path: str) -> str:
        """Mix background music with video at 30% volume"""
        output_path = tempfile.mktemp(suffix='.mp4')
        
        # FFmpeg command to mix audio
        # Music at 30% volume, video audio at 100%
        command = [
            'ffmpeg',
            '-i', video_path,
            '-i', music_path,
            '-filter_complex', '[1:a]volume=0.3[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2',
            '-c:v', 'copy',  # Copy video as-is
            '-c:a', 'aac',
            '-b:a', '192k',
            '-shortest',  # Match shortest input
            '-y',
            output_path
        ]
        
        try:
            ffmpeg_service.run_command(command)
            return output_path
        except Exception as e:
            # If mixing fails, return video without music
            print(f"   ⚠️  Audio mixing failed: {str(e)}, using video without music")
            return video_path
