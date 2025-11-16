# Phase 5: Music Generation & Audio Integration Service
import os
import tempfile
import requests
import base64
import json
from typing import Dict, Tuple, Optional, List
from app.services.s3 import s3_client
from app.services.replicate import replicate_client
from app.services.openai import openai_client
from app.common.exceptions import PhaseException
from app.common.constants import COST_AUDIO_CROP
from app.phases.phase5_refine.model_config import get_default_music_model, get_music_model_config
from moviepy import VideoFileClip


class RefinementService:
    """Service for music generation and audio integration (Phase 5 - simplified scope).
    
    Phase 5 scope (MVP):
    - Generate background music using configured model (default: meta/musicgen)
    - Supports multiple models via model_config.py (musicgen, stable_audio)
    - Crop music to exact video duration using moviepy (Python-native)
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
            
            # Step 2: Analyze video content for better audio matching
            print("🔍 Analyzing video content for audio matching...")
            video_analysis = None
            try:
                video_analysis = self._analyze_video_content(stitched_path, spec)
                if video_analysis:
                    print(f"   ✅ Video analyzed: {video_analysis.get('summary', 'N/A')[:100]}...")
                else:
                    print(f"   ⚠️  Video analysis failed, using spec-based audio prompt")
            except Exception as e:
                print(f"   ⚠️  Video analysis error: {str(e)}, using spec-based audio prompt")
                import traceback
                traceback.print_exc()
            
            # Step 3: Generate background music (using video analysis if available)
            print("🎵 Generating background music...")
            music_path = None
            music_url = None
            try:
                # Get video duration from spec
                duration = spec.get('duration', 30)
                music_path = self._generate_music(video_id, spec, duration, video_analysis=video_analysis)
                
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
            
            # Step 4: Combine video + music
            final_path = stitched_path  # Default to stitched video
            if music_path and os.path.exists(music_path):
                print("🎬 Combining video with music...")
                try:
                    combined_path = self._combine_video_audio(stitched_path, music_path)
                    if combined_path and os.path.exists(combined_path):
                        temp_files.append(combined_path)
                        final_path = combined_path
                        print(f"   ✅ Video and audio combined successfully")
                    else:
                        print(f"   ⚠️  Audio combination returned no file, using video without music")
                        final_path = stitched_path  # Use original video
                except Exception as e:
                    error_msg = str(e)
                    print(f"   ❌ Audio combination failed: {error_msg}")
                    print(f"   ⚠️  Using video without music (original stitched video)")
                    final_path = stitched_path  # Use original video
            else:
                # No music - use video as-is
                print("   ⚠️  No music available, using video without audio")
            
            # Step 5: Upload final video (only if we have a valid final_path)
            print("📤 Uploading final video...")
            final_key = f"videos/{video_id}/final_draft.mp4"
            try:
                final_url = s3_client.upload_file(final_path, final_key)
                print(f"   ✅ Final video uploaded: {final_key}")
            except Exception as e:
                raise PhaseException(f"Failed to upload final video: {str(e)}")
            
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
    
    def _generate_music(self, video_id: str, spec: dict, duration: int = 30, video_analysis: Optional[Dict] = None) -> Optional[str]:
        """Generate background music using configured music model.
        
        Process:
        1. Get music model config (default: musicgen)
        2. Extract audio specs from template (music_style, tempo, mood)
        3. Build music prompt from specs OR video analysis (if available)
        4. Generate music matching video duration (respects model max_duration)
        5. Crop/extend music to exact video duration using FFmpeg if needed
        
        Args:
            video_id: Video generation ID
            spec: Video specification from Phase 1
            duration: Video duration in seconds
            video_analysis: Optional video analysis dict from GPT-4V (preferred over spec)
        """
        try:
            # Get music model configuration (default: musicgen)
            model_config = get_default_music_model()
            model_name = model_config['name']
            replicate_model = model_config['replicate_model']
            max_duration = model_config['max_duration']
            cost = model_config['cost_per_generation']
            input_params = model_config['input_params'].copy()
            
            print(f"   🎼 Using music model: {model_name} ({model_config.get('description', '')})")
            
            # Build music prompt: prefer video analysis over spec
            if video_analysis and video_analysis.get('audio_prompt'):
                # Use video analysis-based prompt (more accurate)
                prompt = video_analysis['audio_prompt']
                print(f"   🎵 Using video analysis-based audio prompt")
            else:
                # Fallback to spec-based prompt
                audio_spec = spec.get('audio', {})
                if not audio_spec:
                    print(f"   ⚠️  WARNING: No audio spec found in video spec! Using defaults.")
                    print(f"   📋 Spec keys: {list(spec.keys())}")
                    audio_spec = {}
                
                music_style = audio_spec.get('music_style', 'orchestral')
                tempo = audio_spec.get('tempo', 'moderate')
                mood = audio_spec.get('mood', 'sophisticated')
                
                print(f"   🎵 Audio spec: style={music_style}, tempo={tempo}, mood={mood}")
                
                # Build music prompt from template specs
                prompt = self._build_music_prompt(music_style, tempo, mood)
            
            print(f"   🎵 Music prompt: '{prompt}'")
            print(f"   ⏱️  Video duration: {duration}s")
            
            # Respect model's max duration
            music_duration = min(duration, max_duration)
            print(f"   📏 Generating {music_duration}s music (model max: {max_duration}s)")
            
            # Build input parameters based on model
            if model_name == 'musicgen':
                # MusicGen uses 'duration' parameter (in seconds, should be integer)
                input_params['prompt'] = prompt
                input_params['duration'] = int(music_duration)  # Ensure integer
            elif model_name == 'stable_audio':
                # Stable Audio uses 'seconds_total' parameter
                input_params['prompt'] = prompt
                input_params['seconds_total'] = music_duration
            
            # Use configured model via Replicate
            print(f"   🔧 Model: {replicate_model}")
            print(f"   🔧 Input params: {list(input_params.keys())}")
            print(f"   🔧 Prompt length: {len(input_params.get('prompt', ''))}")
            
            # Use replicate_client.run() which handles both model names and version hashes
            # The run() method automatically handles the correct API call format
            try:
                print(f"   🔧 Calling Replicate API...")
                output = replicate_client.run(
                    replicate_model,  # Can be model name or version hash
                    input=input_params,
                    timeout=180  # 3 minutes for music generation
                )
                print(f"   ✅ Music generation completed")
            except Exception as e:
                print(f"   ❌ Error during music generation: {str(e)}")
                raise
            
            # Download music file (output is URL from Replicate)
            # Replicate returns a URL string to the generated audio file
            if isinstance(output, str):
                music_url = output
            elif hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
                # If it's an iterator/list, get first item
                music_list = list(output) if hasattr(output, '__iter__') else [output]
                music_url = music_list[0] if music_list else None
            elif isinstance(output, dict):
                # Try common keys for audio output
                music_url = output.get('audio') or output.get('output') or output.get('url')
            else:
                music_url = str(output) if output else None
            
            if not music_url:
                print(f"   ⚠️  Music generation returned no URL (output type: {type(output)}, value: {output})")
                return None
            
            # Ensure we have a valid URL string
            if not isinstance(music_url, str):
                print(f"   ⚠️  Music URL is not a string (type: {type(music_url)})")
                return None
            
            # Download music file from URL
            raw_music_path = tempfile.mktemp(suffix='.mp3')
            
            try:
                print(f"   📥 Downloading music from: {music_url[:80]}...")
                response = requests.get(music_url, timeout=60)
                response.raise_for_status()
                
                print(f"   💾 Writing music to: {raw_music_path}")
                with open(raw_music_path, 'wb') as f:
                    f.write(response.content)
                
                # Verify file size
                file_size = os.path.getsize(raw_music_path)
                print(f"   ✅ Downloaded {file_size} bytes")
                
                if file_size < 1000:  # Less than 1KB is suspicious
                    print(f"   ⚠️  WARNING: Music file is very small ({file_size} bytes), may be invalid")
                    return None
                    
            except Exception as e:
                print(f"   ⚠️  Failed to download music file from {music_url}: {str(e)}")
                import traceback
                traceback.print_exc()
                return None
            
            self.total_cost += cost
            print(f"   ✅ Music generated: {raw_music_path} (${cost:.4f})")
            
            # If video is longer than generated music, crop it to exact duration
            if duration != music_duration:
                print(f"   ✂️  Adjusting music to exact video duration ({duration}s)...")
                cropped_music_path = self._crop_audio(raw_music_path, duration)
                os.remove(raw_music_path)  # Remove raw music
                self.total_cost += COST_AUDIO_CROP
                print(f"   ✅ Music adjusted: {cropped_music_path} (${COST_AUDIO_CROP:.4f})")
                return cropped_music_path
            
            return raw_music_path
            
        except Exception as e:
            print(f"   ⚠️  Music generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_music_prompt(self, music_style: str, tempo: str, mood: str) -> str:
        """Build music prompt from template specs.
        
        Format for MusicGen: Clear, descriptive style description
        "upbeat electronic pop music with energetic synthesizers and driving drums"
        
        Args:
            music_style: Style from template (e.g., "orchestral", "upbeat_pop", "cinematic_epic")
            tempo: Tempo from template (e.g., "moderate", "fast", "slow")
            mood: Mood from template (e.g., "sophisticated", "energetic", "inspiring")
            
        Returns:
            Formatted prompt string for music generation
        """
        # Map template values to MusicGen-friendly prompts
        style_map = {
            "orchestral": "orchestral music with strings and brass",
            "upbeat_pop": "upbeat electronic pop music with energetic synthesizers and driving drums",
            "cinematic_epic": "cinematic epic orchestral music with powerful brass and dramatic percussion",
        }
        
        tempo_map = {
            "moderate": "moderate tempo",
            "fast": "fast tempo with high energy",
            "slow": "slow tempo, calm and steady",
        }
        
        mood_map = {
            "sophisticated": "elegant and sophisticated mood",
            "energetic": "energetic and dynamic, uplifting mood",
            "inspiring": "inspiring and uplifting, powerful mood",
        }
        
        style_desc = style_map.get(music_style, f"{music_style} instrumental music")
        tempo_desc = tempo_map.get(tempo, f"{tempo} tempo")
        mood_desc = mood_map.get(mood, f"{mood} mood")
        
        # Build prompt for MusicGen
        # Example: "upbeat electronic pop music with energetic synthesizers and driving drums, fast tempo with high energy, energetic and dynamic uplifting mood"
        prompt = f"{style_desc}, {tempo_desc}, {mood_desc}"
        return prompt
    
    def _analyze_video_content(self, video_path: str, spec: dict) -> Optional[Dict]:
        """Analyze video content using GPT-4V to generate better audio prompts.
        
        Process:
        1. Extract key frames from video (start, middle, end)
        2. Analyze frames with GPT-4V to understand video content
        3. Generate audio prompt based on actual video content
        
        Args:
            video_path: Path to video file
            spec: Video specification from Phase 1 (for context)
            
        Returns:
            Dict with 'summary', 'audio_prompt', 'mood', 'tempo', 'style' or None if analysis fails
        """
        try:
            # Extract frames from video
            frames = self._extract_video_frames(video_path, num_frames=3)
            if not frames:
                print(f"   ⚠️  Failed to extract frames from video")
                return None
            
            print(f"   📸 Extracted {len(frames)} frames for analysis")
            
            # Analyze frames with GPT-4V
            analysis = self._analyze_frames_with_gpt4v(frames, spec)
            if not analysis:
                print(f"   ⚠️  GPT-4V analysis failed")
                # Cleanup frames
                for frame_path in frames:
                    try:
                        os.remove(frame_path)
                    except Exception:
                        pass
                return None
            
            # Build audio prompt from analysis
            audio_prompt = self._build_audio_prompt_from_analysis(analysis)
            if not audio_prompt:
                print(f"   ⚠️  Failed to build audio prompt from analysis")
                # Cleanup frames
                for frame_path in frames:
                    try:
                        os.remove(frame_path)
                    except Exception:
                        pass
                return None
            
            # Cleanup frames after successful analysis
            for frame_path in frames:
                try:
                    os.remove(frame_path)
                except Exception:
                    pass
            
            return {
                'summary': analysis.get('summary', ''),
                'audio_prompt': audio_prompt,
                'mood': analysis.get('mood', 'sophisticated'),
                'tempo': analysis.get('tempo', 'moderate'),
                'style': analysis.get('style', 'orchestral'),
                'content_type': analysis.get('content_type', 'general')
            }
            
        except Exception as e:
            print(f"   ⚠️  Video analysis error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_video_frames(self, video_path: str, num_frames: int = 3) -> List[str]:
        """Extract key frames from video using MoviePy.
        
        Args:
            video_path: Path to video file
            num_frames: Number of frames to extract (default: 3 for start, middle, end)
            
        Returns:
            List of paths to extracted frame images (PNG files)
        """
        frame_paths = []
        try:
            video = VideoFileClip(video_path)
            duration = video.duration
            
            # Extract frames at key points: start, middle, end
            frame_times = []
            if num_frames == 1:
                frame_times = [duration / 2]  # Middle
            elif num_frames == 2:
                frame_times = [duration * 0.25, duration * 0.75]  # 25% and 75%
            else:
                # Default: start, middle, end
                frame_times = [0, duration / 2, duration - 0.1]  # -0.1 to avoid last frame issues
            
            for i, time in enumerate(frame_times):
                # Clamp time to valid range
                time = max(0, min(time, duration - 0.1))
                
                # Extract frame
                frame_path = tempfile.mktemp(suffix=f'_frame_{i}.png')
                video.save_frame(frame_path, t=time)
                frame_paths.append(frame_path)
                print(f"   📸 Extracted frame {i+1}/{num_frames} at {time:.2f}s")
            
            video.close()
            return frame_paths
            
        except Exception as e:
            print(f"   ⚠️  Frame extraction error: {str(e)}")
            # Cleanup on error
            for frame_path in frame_paths:
                try:
                    os.remove(frame_path)
                except Exception:
                    pass
            return []
    
    def _analyze_frames_with_gpt4v(self, frame_paths: List[str], spec: dict) -> Optional[Dict]:
        """Analyze video frames using GPT-4V to understand video content.
        
        Args:
            frame_paths: List of paths to frame images
            spec: Video specification for context
            
        Returns:
            Dict with analysis results: summary, mood, tempo, style, content_type
        """
        try:
            # Read frames as base64
            frame_images = []
            for frame_path in frame_paths:
                with open(frame_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                    frame_images.append({
                        'type': 'image_url',
                        'image_url': {
                            'url': f'data:image/png;base64,{image_data}'
                        }
                    })
            
            # Build context from spec
            product_name = spec.get('product', {}).get('name', 'product')
            template = spec.get('template', 'general')
            original_audio = spec.get('audio', {})
            
            # Create analysis prompt
            system_prompt = """You are an expert at analyzing video content to determine the perfect background music.

Analyze the provided video frames and determine:
1. What is happening in the video (actions, objects, scenes)
2. The mood and atmosphere (elegant, energetic, calm, dramatic, etc.)
3. The appropriate tempo (slow, moderate, fast)
4. The music style/genre that would best match (orchestral, electronic, cinematic, upbeat pop, etc.)
5. The overall content type (product showcase, lifestyle ad, announcement, etc.)

Return your analysis as JSON with these fields:
{
    "summary": "Brief description of what's in the video (1-2 sentences)",
    "mood": "mood description (e.g., 'elegant', 'energetic', 'sophisticated', 'dramatic')",
    "tempo": "slow|moderate|fast",
    "style": "music style/genre (e.g., 'orchestral', 'electronic', 'cinematic_epic', 'upbeat_pop')",
    "content_type": "type of content (e.g., 'product_showcase', 'lifestyle_ad', 'announcement')",
    "audio_description": "Detailed description of what kind of music would fit perfectly (2-3 sentences)"
}"""

            user_prompt = f"""Analyze these frames from a video about {product_name} (template: {template}).

Original audio spec: {original_audio}

Provide a detailed analysis of what music would best match this video content."""

            # Call GPT-4V
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt}
                    ] + frame_images
                }
            ]
            
            print(f"   🤖 Calling GPT-4V for video analysis...")
            response = openai_client.chat.completions.create(
                model="gpt-4o",  # GPT-4o supports vision
                messages=messages,
                max_tokens=500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            # Parse JSON response
            # Extract JSON from response (handle markdown code blocks)
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0].strip()
            elif '```' in content:
                content = content.split('```')[1].split('```')[0].strip()
            
            analysis = json.loads(content)
            print(f"   ✅ GPT-4V analysis complete")
            return analysis
            
        except Exception as e:
            print(f"   ⚠️  GPT-4V analysis error: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _build_audio_prompt_from_analysis(self, analysis: Dict) -> Optional[str]:
        """Build music generation prompt from video analysis.
        
        Args:
            analysis: Dict from GPT-4V analysis with mood, tempo, style, audio_description
            
        Returns:
            Formatted prompt string for music generation (MusicGen/Stable Audio format)
        """
        try:
            # Use audio_description if available (most detailed)
            if analysis.get('audio_description'):
                # Extract key terms from audio_description and format for music model
                audio_desc = analysis['audio_description']
                style = analysis.get('style', 'orchestral')
                tempo = analysis.get('tempo', 'moderate')
                mood = analysis.get('mood', 'sophisticated')
                
                # Build prompt combining description with structured elements
                # Format: "detailed description, tempo, mood"
                tempo_map = {
                    "slow": "slow tempo, calm and steady",
                    "moderate": "moderate tempo",
                    "fast": "fast tempo with high energy"
                }
                tempo_desc = tempo_map.get(tempo, f"{tempo} tempo")
                
                # Create prompt: use audio_description as base, add tempo
                prompt = f"{audio_desc}, {tempo_desc}"
                return prompt
            else:
                # Fallback: build from structured fields
                style = analysis.get('style', 'orchestral')
                tempo = analysis.get('tempo', 'moderate')
                mood = analysis.get('mood', 'sophisticated')
                return self._build_music_prompt(style, tempo, mood)
                
        except Exception as e:
            print(f"   ⚠️  Audio prompt building error: {str(e)}")
            return None
    
    def _crop_audio(self, audio_path: str, target_duration: int) -> str:
        """Crop audio to exact target duration using moviepy (Python-native).
        
        Args:
            audio_path: Path to input audio file
            target_duration: Target duration in seconds
            
        Returns:
            Path to cropped audio file
        """
        try:
            # MoviePy 2.x uses direct imports (no .editor module)
            from moviepy import AudioFileClip
            
            # Load audio and crop to target duration
            audio = AudioFileClip(audio_path)
            cropped_audio = audio.subclip(0, target_duration)
            
            # Export cropped audio
            output_path = tempfile.mktemp(suffix='.mp3')
            cropped_audio.write_audiofile(
                output_path,
                codec='libmp3lame',
                verbose=False,
                logger=None
            )
            
            # Cleanup
            audio.close()
            cropped_audio.close()
            
            return output_path
            
        except ImportError:
            raise ImportError(
                "moviepy is not installed. Install it with: pip install moviepy\n"
                "It should be in requirements.txt for deployment."
            )
        except Exception as e:
            print(f"   ⚠️  Audio cropping failed: {str(e)}, using original audio")
            return audio_path
    
    def _combine_video_audio(self, video_path: str, music_path: str) -> str:
        """Combine video with music using moviepy (Python-native).
        
        Sets music volume to 0.7 (70%) for balanced audio.
        
        Args:
            video_path: Path to video file
            music_path: Path to music file
            
        Returns:
            Path to combined video file
            
        Raises:
            ImportError: If moviepy is not installed (should be in requirements.txt)
            Exception: If video/audio combination fails
        """
        try:
            # MoviePy 2.x uses direct imports (no .editor module)
            from moviepy import VideoFileClip, AudioFileClip, CompositeAudioClip
        except ImportError:
            raise ImportError(
                "moviepy is not installed. Install it with: pip install moviepy\n"
                "It should be in requirements.txt for deployment."
            )
        
        try:
            # Load video and audio
            video = VideoFileClip(video_path)
            music = AudioFileClip(music_path)
            
            # Set music volume to 0.7 (70%) - MoviePy 2.x uses with_volume_scaled
            music = music.with_volume_scaled(0.7)
            
            # If video has audio, mix it; otherwise just use music
            if video.audio is not None:
                # Mix video audio (100%) with music (70%)
                final_audio = CompositeAudioClip([video.audio, music])
            else:
                # No video audio, just use music
                final_audio = music
            
            # Set audio to video - MoviePy 2.x uses with_audio instead of set_audio
            final_video = video.with_audio(final_audio)
            
            # Export - MoviePy 2.x API changes
            output_path = tempfile.mktemp(suffix='.mp4')
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=tempfile.mktemp(suffix='.m4a'),
                remove_temp=True
            )
            
            # Cleanup
            video.close()
            music.close()
            final_video.close()
            
            return output_path
            
        except Exception as e:
            raise Exception(f"moviepy video/audio combination failed: {str(e)}")
    
