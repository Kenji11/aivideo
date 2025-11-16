# Phase 5: Music Generation & Audio Integration Service
import os
import tempfile
import requests
import subprocess
from typing import Dict, Tuple, Optional
from app.services.s3 import s3_client
from app.services.ffmpeg import ffmpeg_service
from app.services.replicate import replicate_client
from app.common.exceptions import PhaseException
from app.common.constants import COST_BARK_MUSIC, COST_AUDIO_CROP


class RefinementService:
    """Service for music generation and audio integration (Phase 5 - simplified scope).
    
    Phase 5 scope (MVP):
    - Generate background music using suno/bark-with-music
    - Crop music to exact video duration using lucataco/audio-crop
    - Combine video + music using moviepy
    - Set music volume to 70% for balanced audio
    
    Removed from scope (models output good quality by default):
    - Upscaling (models already output good resolution)
    - Temporal smoothing (not needed)
    - Color grading (models handle color well)
    """
    
    def __init__(self):
        self.total_cost = 0.0
    
    def refine_all(self, video_id: str, stitched_url: str, spec: dict) -> Tuple[str, Optional[str]]:
        """
        Generate music and integrate with video.
        
        Args:
            video_id: Unique video generation ID
            stitched_url: S3 URL of stitched video from Phase 4
            spec: Video specification from Phase 1
            
        Returns:
            Tuple of (final_video_url, music_url)
        """
        temp_files = []
        
        try:
            # Step 1: Download stitched video from Phase 4
            print(f"📥 Downloading stitched video from: {stitched_url}")
            try:
                stitched_path = s3_client.download_temp(stitched_url)
                temp_files.append(stitched_path)
                print(f"   ✅ Stitched video downloaded: {stitched_path}")
            except Exception as e:
                raise PhaseException(f"Failed to download stitched video from {stitched_url}: {str(e)}")
            
            # Step 2: Generate background music
            print("🎵 Generating background music...")
            music_path = None
            music_url = None
            try:
                # Get video duration from spec
                duration = spec.get('duration', 30)
                music_path = self._generate_music(video_id, spec, duration)
                
                if music_path and os.path.exists(music_path):
                    temp_files.append(music_path)
                    # Upload music to S3
                    music_key = f"videos/{video_id}/music/background.mp3"
                    music_url = s3_client.upload_file(music_path, music_key)
                    print(f"   ✅ Music generated and uploaded: {music_key}")
                else:
                    print(f"   ⚠️  Music generation returned no file")
            except Exception as e:
                print(f"   ⚠️  Music generation failed: {str(e)}, continuing without music")
                import traceback
                traceback.print_exc()
            
            # Step 3: Combine video + music
            if music_path and os.path.exists(music_path):
                print("🎬 Combining video with music...")
                try:
                    final_path = self._combine_video_audio(stitched_path, music_path)
                    temp_files.append(final_path)
                    print(f"   ✅ Video and audio combined successfully")
                except Exception as e:
                    print(f"   ⚠️  Audio combination failed: {str(e)}, using video without music")
                    final_path = stitched_path
            else:
                # No music - use video as-is
                print("   ⚠️  No music available, using video without audio")
                final_path = stitched_path
            
            # Step 4: Upload final video
            print("📤 Uploading final video...")
            final_key = f"videos/{video_id}/final_draft.mp4"
            final_url = s3_client.upload_file(final_path, final_key)
            print(f"   ✅ Final video uploaded: {final_key}")
            
            return final_url, music_url
            
        except Exception as e:
            raise PhaseException(f"Phase 5 failed: {str(e)}")
        finally:
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception:
                    pass
    
    def _generate_music(self, video_id: str, spec: dict, duration: int = 30) -> Optional[str]:
        """Generate background music using suno/bark-with-music model.
        
        Process:
        1. Extract audio specs from template (music_style, tempo, mood)
        2. Build music prompt from specs
        3. Generate music ~5s longer than video duration for safety margin
        4. Crop music to exact video duration using lucataco/audio-crop
        """
        try:
            # Extract audio specs from template
            audio_spec = spec.get('audio', {})
            music_style = audio_spec.get('music_style', 'orchestral')
            tempo = audio_spec.get('tempo', 'moderate')
            mood = audio_spec.get('mood', 'sophisticated')
            
            # Build music prompt from template specs
            # Example: "energetic hip-hop instrumental, 140-150 BPM, upbeat mood"
            prompt = self._build_music_prompt(music_style, tempo, mood)
            
            print(f"   🎵 Music prompt: '{prompt}'")
            print(f"   ⏱️  Video duration: {duration}s")
            
            # Generate music ~5s longer than video duration for safety margin
            music_duration = duration + 5
            print(f"   📏 Generating {music_duration}s music (will crop to {duration}s)")
            
            # Use suno/bark-with-music via Replicate
            output = replicate_client.run(
                "suno/bark-with-music",
                input={
                    "prompt": prompt,
                    "duration": min(music_duration, 30),  # Bark max is 30s, but we'll handle longer
                },
                timeout=180  # 3 minutes for music generation
            )
            
            # Download music file
            music_url = output if isinstance(output, str) else output[0]
            if not music_url:
                print(f"   ⚠️  Music generation returned no URL")
                return None
            
            raw_music_path = tempfile.mktemp(suffix='.mp3')
            
            print(f"   📥 Downloading music from: {music_url[:80]}...")
            response = requests.get(music_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(raw_music_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.total_cost += COST_BARK_MUSIC
            print(f"   ✅ Music generated: {raw_music_path} (${COST_BARK_MUSIC:.4f})")
            
            # Crop music to exact video duration using FFmpeg
            print(f"   ✂️  Cropping music to exact video duration ({duration}s)...")
            cropped_music_path = self._crop_audio(raw_music_path, duration)
            os.remove(raw_music_path)  # Remove raw music
            
            self.total_cost += COST_AUDIO_CROP
            print(f"   ✅ Music cropped: {cropped_music_path} (${COST_AUDIO_CROP:.4f})")
            
            return cropped_music_path
            
        except Exception as e:
            print(f"   ⚠️  Music generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_music_prompt(self, music_style: str, tempo: str, mood: str) -> str:
        """Build music prompt from template specs.
        
        Args:
            music_style: Style from template (e.g., "orchestral", "upbeat_pop", "cinematic_epic")
            tempo: Tempo from template (e.g., "moderate", "fast", "slow")
            mood: Mood from template (e.g., "sophisticated", "energetic", "inspiring")
            
        Returns:
            Formatted prompt string for music generation
        """
        # Map template values to descriptive prompts
        style_map = {
            "orchestral": "orchestral instrumental",
            "upbeat_pop": "upbeat pop instrumental",
            "cinematic_epic": "cinematic epic instrumental",
        }
        
        tempo_map = {
            "moderate": "moderate tempo",
            "fast": "fast tempo, 140-150 BPM",
            "slow": "slow tempo, 60-80 BPM",
        }
        
        mood_map = {
            "sophisticated": "sophisticated, elegant",
            "energetic": "energetic, dynamic",
            "inspiring": "inspiring, uplifting",
        }
        
        style_desc = style_map.get(music_style, music_style)
        tempo_desc = tempo_map.get(tempo, tempo)
        mood_desc = mood_map.get(mood, mood)
        
        # Build prompt: "style, tempo, mood, background music for advertisement"
        prompt = f"{style_desc}, {tempo_desc}, {mood_desc} mood, background music for advertisement"
        return prompt
    
    def _crop_audio(self, audio_path: str, target_duration: int) -> str:
        """Crop audio to exact target duration using lucataco/audio-crop.
        
        Args:
            audio_path: Path to input audio file
            target_duration: Target duration in seconds
            
        Returns:
            Path to cropped audio file
        """
        try:
            # Use lucataco/audio-crop via Replicate
            # First, upload audio to a temporary location or use direct file
            # For now, we'll use FFmpeg to crop (simpler than Replicate for local files)
            output_path = tempfile.mktemp(suffix='.mp3')
            
            # Use FFmpeg to crop audio to exact duration
            command = [
                'ffmpeg',
                '-i', audio_path,
                '-t', str(target_duration),  # Crop to target duration
                '-c:a', 'libmp3lame',
                '-y',
                output_path
            ]
            
            ffmpeg_service.run_command(command)
            return output_path
            
        except Exception as e:
            print(f"   ⚠️  Audio cropping failed: {str(e)}, using original audio")
            return audio_path
    
    def _combine_video_audio(self, video_path: str, music_path: str) -> str:
        """Combine video with music using moviepy.
        
        Sets music volume to 0.7 (70%) for balanced audio.
        
        Args:
            video_path: Path to video file
            music_path: Path to music file
            
        Returns:
            Path to combined video file
        """
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
            
            # Load video and audio
            video = VideoFileClip(video_path)
            music = AudioFileClip(music_path)
            
            # Set music volume to 0.7 (70%)
            music = music.volumex(0.7)
            
            # If video has audio, mix it; otherwise just use music
            if video.audio is not None:
                # Mix video audio (100%) with music (70%)
                final_audio = CompositeAudioClip([video.audio, music])
            else:
                # No video audio, just use music
                final_audio = music
            
            # Set audio to video
            final_video = video.set_audio(final_audio)
            
            # Export
            output_path = tempfile.mktemp(suffix='.mp4')
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=tempfile.mktemp(suffix='.m4a'),
                remove_temp=True,
                verbose=False,
                logger=None
            )
            
            # Cleanup
            video.close()
            music.close()
            final_video.close()
            
            return output_path
            
        except ImportError:
            # Fallback to FFmpeg if moviepy not available
            print("   ⚠️  moviepy not available, using FFmpeg fallback")
            return self._combine_video_audio_ffmpeg(video_path, music_path)
        except Exception as e:
            print(f"   ⚠️  moviepy combination failed: {str(e)}, using FFmpeg fallback")
            return self._combine_video_audio_ffmpeg(video_path, music_path)
    
    def _combine_video_audio_ffmpeg(self, video_path: str, music_path: str) -> str:
        """Fallback: Combine video with music using FFmpeg.
        
        Sets music volume to 0.7 (70%) for balanced audio.
        """
        output_path = tempfile.mktemp(suffix='.mp4')
        
        # Check if video has audio
        try:
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
            has_audio = False
        
        if has_audio:
            # Mix video audio (100%) with music (70%)
            command = [
                'ffmpeg',
                '-i', video_path,
                '-i', music_path,
                '-filter_complex', '[1:a]volume=0.7[music];[0:a][music]amix=inputs=2:duration=first:dropout_transition=2',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-y',
                output_path
            ]
        else:
            # No video audio, just add music at 70% volume
            command = [
                'ffmpeg',
                '-i', video_path,
                '-i', music_path,
                '-filter_complex', '[1:a]volume=0.7[music]',
                '-map', '0:v',
                '-map', '[music]',
                '-c:v', 'copy',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',
                '-y',
                output_path
            ]
        
        try:
            ffmpeg_service.run_command(command)
            return output_path
        except Exception as e:
            print(f"   ⚠️  FFmpeg combination failed: {str(e)}, using video without music")
            return video_path
