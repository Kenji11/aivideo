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
            
            # Build filter complex for transitions
            filter_complex = self._build_transition_filter(chunk_paths, transitions)
            
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
                output_path
            ])
            
            print(f"Stitching {len(chunk_paths)} chunks with transitions...")
            print(f"FFmpeg command: {' '.join(cmd)}")
            
            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not os.path.exists(output_path):
                raise PhaseException(f"FFmpeg completed but output file not found: {output_path}")
            
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
    
    def _build_transition_filter(self, chunk_paths: List[str], transitions: List[Dict]) -> str:
        """
        Build FFmpeg filter_complex string for transitions.
        
        Args:
            chunk_paths: List of paths to chunk video files
            transitions: List of transition specifications
            
        Returns:
            FFmpeg filter_complex string
        """
        if len(chunk_paths) < 2:
            # Single chunk - no transitions needed
            return "[0:v]copy[v]"
        
        # For now, always use simple concat (most reliable)
        # xfade requires constant frame rate which our chunks don't have
        # TODO: Add fps filter to normalize frame rate if we want transitions later
        
        # Simple concatenation - use concat filter (most reliable)
        # Label all inputs and normalize frame rate
        input_labels = []
        for i in range(len(chunk_paths)):
            # Normalize to 24fps and reset timestamps
            input_labels.append(f"[{i}:v]fps=24,setpts=PTS-STARTPTS[v{i}]")
        
        # Build concat filter
        concat_inputs = ';'.join(input_labels)
        concat_parts = ''.join([f"[v{i}]" for i in range(len(chunk_paths))])
        concat_filter = f"{concat_inputs};{concat_parts}concat=n={len(chunk_paths)}:v=1:a=0[v]"
        return concat_filter
