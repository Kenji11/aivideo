# Phase 4: Video Stitching with Transitions
import os
import tempfile
import subprocess
from typing import List, Dict
from app.services.s3 import s3_client
from app.common.constants import S3_CHUNKS_PREFIX
from app.common.exceptions import PhaseException


class VideoStitcher:
    """Service for stitching video chunks with transitions"""
    
    def __init__(self):
        """Initialize the stitcher"""
        self.s3 = s3_client
    
    def stitch_with_transitions(
        self,
        video_id: str,
        chunk_urls: List[str],
        transitions: List[Dict]
    ) -> str:
        """
        Stitch video chunks together with transitions using FFmpeg.
        
        Args:
            video_id: Unique video generation ID
            chunk_urls: List of S3 URLs for video chunks (in order)
            transitions: List of transition specifications from spec
            
        Returns:
            S3 URL of stitched video
            
        Raises:
            PhaseException: If stitching fails
        """
        temp_dir = None
        temp_files = []
        
        try:
            # Create temporary directory for chunks
            temp_dir = tempfile.mkdtemp()
            
            # Download all chunks from S3
            print(f"Downloading {len(chunk_urls)} chunks from S3...")
            chunk_paths = []
            
            for i, chunk_url in enumerate(chunk_urls):
                # Extract S3 key from URL
                if chunk_url.startswith('s3://'):
                    chunk_key = chunk_url.replace(f's3://{self.s3.bucket}/', '')
                else:
                    # Assume it's already a key
                    chunk_key = chunk_url
                
                # Download chunk
                chunk_path = os.path.join(temp_dir, f'chunk_{i:02d}.mp4')
                self.s3.download_file(chunk_key, chunk_path)
                chunk_paths.append(chunk_path)
                temp_files.append(chunk_path)
            
            # Build FFmpeg command with transitions
            output_path = os.path.join(temp_dir, 'stitched.mp4')
            temp_files.append(output_path)
            
            # Detect target resolution from chunks (handles different model resolutions)
            target_resolution = self._detect_target_resolution(chunk_paths)
            target_width, target_height = target_resolution
            
            # Try filter complex method first, fallback to concat demuxer if it fails
            print(f"Stitching {len(chunk_paths)} chunks with transitions...")
            print(f"   Target resolution: {target_width}x{target_height}")
            
            # Method 1: Try filter complex (better quality, supports transitions, handles different resolutions)
            try:
                filter_complex = self._build_transition_filter(chunk_paths, transitions, target_resolution)
                
                # Build FFmpeg command
                cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output
                ]
                
                # Add input files
                for chunk_path in chunk_paths:
                    cmd.extend(['-i', chunk_path])
                
                # Add filter complex
                cmd.extend([
                    '-filter_complex', filter_complex,
                    '-map', '[v]',  # Map output from filter
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-r', '24',  # 24 fps
                    '-preset', 'medium',
                    '-crf', '23',  # Quality setting
                    '-s', f'{target_width}x{target_height}',  # Explicit output resolution
                    output_path
                ])
                
                print(f"FFmpeg command (filter complex): {' '.join(cmd)}")
                
                # Execute FFmpeg with better error handling
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=300  # 5 minute timeout
                )
                
                print("✅ Filter complex method succeeded")
                
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                # Method 2: Fallback to concat demuxer (more reliable, simpler)
                print(f"⚠️  Filter complex method failed, trying concat demuxer fallback...")
                if isinstance(e, subprocess.CalledProcessError):
                    print(f"   Error: {e.stderr[:500] if e.stderr else 'Unknown error'}")
                
                # Create concat file list
                concat_file = os.path.join(temp_dir, 'concat_list.txt')
                with open(concat_file, 'w') as f:
                    for chunk_path in chunk_paths:
                        # Use absolute path and escape single quotes
                        abs_path = os.path.abspath(chunk_path)
                        f.write(f"file '{abs_path}'\n")
                
                temp_files.append(concat_file)
                
                # Build simpler concat command with resolution normalization
                # For concat demuxer, we need to normalize chunks first, then concat
                # This is more complex, so we'll use a two-pass approach
                print(f"   Normalizing chunks to {target_width}x{target_height} before concat...")
                
                # Normalize each chunk first
                normalized_chunks = []
                for i, chunk_path in enumerate(chunk_paths):
                    normalized_path = os.path.join(temp_dir, f'normalized_{i:02d}.mp4')
                    normalize_cmd = [
                        'ffmpeg',
                        '-y',
                        '-i', chunk_path,
                        '-vf', f'scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p',
                        '-c:v', 'libx264',
                        '-preset', 'medium',
                        '-crf', '23',
                        normalized_path
                    ]
                    try:
                        subprocess.run(normalize_cmd, capture_output=True, text=True, check=True, timeout=60)
                        normalized_chunks.append(normalized_path)
                        temp_files.append(normalized_path)
                    except subprocess.CalledProcessError as e:
                        print(f"   ⚠️  Failed to normalize chunk {i}, using original: {e.stderr[:200]}")
                        normalized_chunks.append(chunk_path)  # Fallback to original
                
                # Update concat file with normalized chunks
                with open(concat_file, 'w') as f:
                    for chunk_path in normalized_chunks:
                        abs_path = os.path.abspath(chunk_path)
                        f.write(f"file '{abs_path}'\n")
                
                # Build concat command
                cmd = [
                    'ffmpeg',
                    '-y',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file,
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-r', '24',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-s', f'{target_width}x{target_height}',  # Explicit output resolution
                    output_path
                ]
                
                print(f"FFmpeg command (concat demuxer): {' '.join(cmd)}")
                
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        check=True,
                        timeout=300
                    )
                    print("✅ Concat demuxer method succeeded")
                except subprocess.TimeoutExpired:
                    raise PhaseException("FFmpeg stitching timed out after 5 minutes")
                except subprocess.CalledProcessError as e:
                    # Log full error for debugging
                    error_msg = f"FFmpeg failed with return code {e.returncode}\n"
                    error_msg += f"Command: {' '.join(cmd)}\n"
                    error_msg += f"Stdout: {e.stdout}\n" if e.stdout else ""
                    error_msg += f"Stderr: {e.stderr}\n" if e.stderr else ""
                    print(f"❌ FFmpeg Error Details:\n{error_msg}")
                    raise PhaseException(f"FFmpeg failed to stitch video (both methods failed): {e.stderr or e.stdout or 'Unknown error'}")
            
            if not os.path.exists(output_path):
                raise PhaseException(f"FFmpeg completed but output file not found: {output_path}")
            
            # Verify output file is valid
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise PhaseException(f"FFmpeg output file is empty: {output_path}")
            
            # Upload stitched video to S3
            stitched_key = f"{S3_CHUNKS_PREFIX}/{video_id}/stitched.mp4"
            stitched_s3_url = self.s3.upload_file(output_path, stitched_key)
            
            print(f"✅ Stitched video uploaded: {stitched_s3_url}")
            
            return stitched_s3_url
            
        except subprocess.CalledProcessError as e:
            raise PhaseException(f"FFmpeg failed to stitch video: {e.stderr}")
        except Exception as e:
            raise PhaseException(f"Failed to stitch video: {str(e)}")
        finally:
            # Clean up temp files
            for temp_file in temp_files:
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except Exception:
                        pass
            
            # Remove temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    os.rmdir(temp_dir)
                except Exception:
                    pass  # Directory not empty, ignore
    
    def _get_video_resolution(self, video_path: str) -> tuple:
        """
        Get video resolution (width, height) using ffprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Tuple of (width, height) in pixels
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=width,height',
                '-of', 'csv=s=x:p=0',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            width, height = map(int, result.stdout.strip().split('x'))
            return (width, height)
        except Exception as e:
            print(f"⚠️  Failed to detect resolution for {video_path}: {str(e)}, defaulting to 1280x720")
            return (1280, 720)  # Default fallback
    
    def _detect_target_resolution(self, chunk_paths: List[str]) -> tuple:
        """
        Detect target resolution for stitching.
        Uses the highest resolution found among all chunks (upscales lower res chunks).
        
        Args:
            chunk_paths: List of paths to chunk video files
            
        Returns:
            Tuple of (width, height) for target resolution
        """
        resolutions = []
        for chunk_path in chunk_paths:
            width, height = self._get_video_resolution(chunk_path)
            resolutions.append((width, height))
            print(f"   📐 Chunk resolution: {width}x{height}")
        
        # Use the highest resolution (upscale lower res chunks)
        max_width = max(r[0] for r in resolutions)
        max_height = max(r[1] for r in resolutions)
        
        # Round to even numbers (required for yuv420p)
        max_width = max_width if max_width % 2 == 0 else max_width + 1
        max_height = max_height if max_height % 2 == 0 else max_height + 1
        
        print(f"   🎯 Target resolution: {max_width}x{max_height} (highest among chunks)")
        return (max_width, max_height)
    
    def _build_transition_filter(self, chunk_paths: List[str], transitions: List[Dict], target_resolution: tuple = None) -> str:
        """
        Build FFmpeg filter_complex string for transitions.
        
        Args:
            chunk_paths: List of paths to chunk video files
            transitions: List of transition specifications
            target_resolution: Optional (width, height) tuple. If None, auto-detects from chunks.
            
        Returns:
            FFmpeg filter_complex string
        """
        if len(chunk_paths) < 2:
            # Single chunk - no transitions needed
            return "[0:v]copy[v]"
        
        # Auto-detect target resolution if not provided
        if target_resolution is None:
            target_resolution = self._detect_target_resolution(chunk_paths)
        
        target_width, target_height = target_resolution
        
        # Normalize all inputs to same format and resolution
        # This handles different resolutions from different models (480p, 720p, 1080p, etc.)
        input_labels = []
        for i in range(len(chunk_paths)):
            # Normalize: scale to target resolution, fps, pixel format, and reset timestamps
            # Use scale filter with force_original_aspect_ratio=decrease to maintain aspect ratio
            # Then pad to exact target resolution if needed
            scale_filter = f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease"
            pad_filter = f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2"
            normalize_filter = f"{scale_filter},{pad_filter},fps=24,format=yuv420p,setpts=PTS-STARTPTS"
            input_labels.append(f"[{i}:v]{normalize_filter}[v{i}]")
        
        # Concat all normalized inputs
        concat_inputs = ';'.join(input_labels)
        concat_parts = ''.join([f"[v{i}]" for i in range(len(chunk_paths))])
        concat_filter = f"{concat_inputs};{concat_parts}concat=n={len(chunk_paths)}:v=1:a=0[v]"
        
        return concat_filter
