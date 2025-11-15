# Phase 5: Refinement Service
import os
import tempfile
import requests
import subprocess
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
            print(f"   Downloading stitched video from: {stitched_url}")
            try:
                stitched_path = s3_client.download_temp(stitched_url)
                temp_files.append(stitched_path)
                print(f"   ✅ Stitched video downloaded to: {stitched_path}")
            except Exception as e:
                raise PhaseException(f"Failed to download stitched video from {stitched_url}: {str(e)}")
            
            # Step 2: Upscale to 1080p
            print("   Upscaling to 1080p...")
            upscaled_path = self._upscale_video(stitched_path)
            temp_files.append(upscaled_path)
            
            # Step 3: Generate background music
            print("   Generating background music...")
            music_path = None
            music_url = None
            try:
                # Get video duration for music length matching
                duration = spec.get('duration', 30)
                music_path = self._generate_music(video_id, spec, duration)
                if music_path and os.path.exists(music_path):
                    temp_files.append(music_path)
                    # Upload music to S3
                    music_key = f"videos/{video_id}/music/background.mp3"
                    music_url = s3_client.upload_file(music_path, music_key)
                    self.total_cost += COST_MUSICGEN
                    print(f"   ✅ Music generated successfully: {music_key}")
                else:
                    print(f"   ⚠️  Music generation returned no file")
            except Exception as e:
                print(f"   ⚠️  Music generation failed: {str(e)}, continuing without music")
                import traceback
                traceback.print_exc()
            
            # Step 4: Mix audio (if music available)
            if music_path and os.path.exists(music_path):
                print("   Mixing audio with video...")
                try:
                    final_path = self._mix_audio(upscaled_path, music_path)
                    temp_files.append(final_path)
                    print(f"   ✅ Audio mixed successfully")
                except Exception as e:
                    print(f"   ⚠️  Audio mixing failed: {str(e)}, using video without music")
                    final_path = upscaled_path
            else:
                # No music - ensure video has at least silent audio track
                print("   No music available, ensuring video has audio track...")
                final_path = self._ensure_audio_track(upscaled_path)
                if final_path != upscaled_path:
                    temp_files.append(final_path)
            
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
    
    def _generate_music(self, video_id: str, spec: dict, duration: int = 30) -> Optional[str]:
        """Generate background music using MusicGen"""
        try:
            # Extract music style from spec
            audio_spec = spec.get('audio', {})
            music_style = audio_spec.get('music_style', 'orchestral')
            tempo = audio_spec.get('tempo', 'moderate')
            mood = audio_spec.get('mood', 'sophisticated')
            
            # Create prompt for music generation
            prompt = f"{music_style} music, {tempo} tempo, {mood} mood, background music for advertisement"
            
            print(f"   Generating music with prompt: '{prompt}'")
            print(f"   Duration: {duration} seconds")
            
            # Use MusicGen via Replicate
            output = replicate_client.run(
                "meta/musicgen:671ac645ce5e552cc63a54c2e00c19a55811a06",
                input={
                    "model_version": "large",
                    "prompt": prompt,
                    "duration": min(duration, 30),  # MusicGen max is 30 seconds, but we'll loop if needed
                },
                timeout=180  # 3 minutes for music generation
            )
            
            # Download music file
            music_url = output if isinstance(output, str) else output[0]
            if not music_url:
                print(f"   ⚠️  MusicGen returned no URL")
                return None
            
            music_path = tempfile.mktemp(suffix='.mp3')
            
            print(f"   Downloading music from: {music_url[:80]}...")
            response = requests.get(music_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(music_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # If music is shorter than video, loop it to match duration
            if duration > 30:
                print(f"   Looping music to match {duration}s video duration...")
                looped_path = self._loop_audio(music_path, duration)
                os.remove(music_path)  # Remove original
                music_path = looped_path
            
            print(f"   ✅ Music generated: {music_path}")
            return music_path
            
        except Exception as e:
            print(f"   ⚠️  Music generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _loop_audio(self, audio_path: str, target_duration: int) -> str:
        """Loop audio to match target duration"""
        output_path = tempfile.mktemp(suffix='.mp3')
        
        # Calculate number of loops needed
        # Get original duration first
        probe_command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        result = subprocess.run(probe_command, capture_output=True, text=True, timeout=10)
        original_duration = float(result.stdout.strip()) if result.stdout.strip() else 30.0
        
        loops_needed = int(target_duration / original_duration) + 1
        
        # Loop audio using FFmpeg
        command = [
            'ffmpeg',
            '-stream_loop', str(loops_needed),
            '-i', audio_path,
            '-t', str(target_duration),
            '-c:a', 'libmp3lame',
            '-y',
            output_path
        ]
        
        ffmpeg_service.run_command(command)
        return output_path
    
    def _ensure_audio_track(self, video_path: str) -> str:
        """Ensure video has an audio track (add silent audio if missing)"""
        try:
            # Check if video has audio
            probe_command = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'csv=p=0',
                video_path
            ]
            result = subprocess.run(probe_command, capture_output=True, text=True, timeout=10)
            has_audio = 'audio' in result.stdout.lower()
            
            if has_audio:
                return video_path  # Already has audio, return as-is
            
            # Add silent audio track
            print("   Adding silent audio track to video...")
            output_path = tempfile.mktemp(suffix='.mp4')
            command = [
                'ffmpeg',
                '-i', video_path,
                '-f', 'lavfi',
                '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-shortest',
                '-y',
                output_path
            ]
            ffmpeg_service.run_command(command)
            return output_path
            
        except Exception as e:
            print(f"   ⚠️  Failed to ensure audio track: {str(e)}, using original video")
            return video_path
    
    def _mix_audio(self, video_path: str, music_path: str) -> str:
        """Mix background music with video at 30% volume"""
        output_path = tempfile.mktemp(suffix='.mp4')
        
        # Check if video has audio track
        # If not, we'll add silent audio first, then mix with music
        try:
            # Probe video to check for audio stream
            probe_command = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'a:0',
                '-show_entries', 'stream=codec_type',
                '-of', 'csv=p=0',
                video_path
            ]
            result = subprocess.run(probe_command, capture_output=True, text=True, timeout=10)
            has_audio = 'audio' in result.stdout.lower()
        except Exception:
            # If probe fails, assume no audio
            has_audio = False
        
        if not has_audio:
            # Video has no audio - add silent audio track first
            print("   Video has no audio track, adding silent audio...")
            silent_video_path = tempfile.mktemp(suffix='.mp4')
            add_silent_command = [
                'ffmpeg',
                '-i', video_path,
                '-f', 'lavfi',
                '-i', f'anullsrc=channel_layout=stereo:sample_rate=44100',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-shortest',
                '-y',
                silent_video_path
            ]
            try:
                ffmpeg_service.run_command(add_silent_command)
                video_path = silent_video_path  # Use video with silent audio
            except Exception as e:
                print(f"   ⚠️  Failed to add silent audio: {str(e)}, proceeding without video audio")
        
        # FFmpeg command to mix audio
        # Music at 30% volume, video audio at 100% (or silent if no original audio)
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
            # If mixing fails, try simpler approach: just add music without mixing
            print(f"   ⚠️  Audio mixing failed: {str(e)}, trying simple music overlay...")
            try:
                simple_command = [
                    'ffmpeg',
                    '-i', video_path,
                    '-i', music_path,
                    '-filter_complex', '[1:a]volume=0.4[music]',
                    '-map', '0:v',  # Video from first input
                    '-map', '[music]',  # Music from filter
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-shortest',
                    '-y',
                    output_path
                ]
                ffmpeg_service.run_command(simple_command)
                return output_path
            except Exception as e2:
                print(f"   ⚠️  Simple audio overlay also failed: {str(e2)}, using video without music")
                return video_path
