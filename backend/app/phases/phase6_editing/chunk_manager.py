"""
Chunk Manager for Phase 6 Editing

Manages chunk metadata, retrieval, and version tracking.
"""
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.common.models import VideoGeneration
from app.services.s3 import s3_client
from app.services.redis import RedisClient
from app.phases.phase6_editing.schemas import ChunkVersion, ChunkMetadata
from app.phases.phase3_chunks.model_config import get_model_config, get_default_model
import logging
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)
redis_client = RedisClient()


class ChunkManager:
    """Manages chunk metadata, retrieval, and version tracking"""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize ChunkManager with optional database session"""
        self.db = db or SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.db:
            return
        try:
            if exc_type:
                self.db.rollback()
            else:
                self.db.commit()
        finally:
            if self.db != SessionLocal():
                self.db.close()
    
    def get_chunk_metadata(self, video_id: str, chunk_index: int) -> Optional[Dict]:
        """
        Get chunk info (URL, prompt, model, cost).
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index (0-based)
            
        Returns:
            Dictionary with chunk metadata or None if not found
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return None
            
            # Get chunk URLs
            chunk_urls = video.chunk_urls or []
            if chunk_index >= len(chunk_urls):
                return None
            
            chunk_url = chunk_urls[chunk_index]
            
            # Get chunk metadata from spec
            spec = video.spec or {}
            beats = spec.get('beats', [])
            
            # Get model from current selected version, or from phase3 output, or fallback to spec
            # Phase3 stores the actual model used in spec.model
            model = spec.get('model', 'hailuo_fast')
            
            # Also check phase3 output for the model that was actually used
            phase_outputs = video.phase_outputs or {}
            phase3_output = phase_outputs.get('phase3_chunks', {})
            phase3_spec = phase3_output.get('output_data', {}).get('spec', {})
            if phase3_spec.get('model'):
                model = phase3_spec.get('model')
            
            prompt = ''
            cost = 0.0
            
            # Check if this chunk has versions tracked (for replaced/split chunks)
            versions = self.get_chunk_versions(video_id, chunk_index)
            if versions:
                # Find the currently selected version
                selected_version = None
                for v in versions:
                    if v.is_selected:
                        selected_version = v
                        break
                
                # If no version is explicitly selected, use the first one (should be the chunk URL)
                if not selected_version and versions:
                    selected_version = versions[0]
                
                if selected_version:
                    # Use URL, model, and prompt from selected version
                    if selected_version.url:
                        chunk_url = selected_version.url
                    if selected_version.model:
                        model = selected_version.model
                    if selected_version.prompt:
                        prompt = selected_version.prompt
                    if selected_version.cost is not None:
                        cost = selected_version.cost
            else:
                # No versions tracked, use phase3 cost breakdown
                phase_outputs = video.phase_outputs or {}
                phase3_output = phase_outputs.get('phase3_chunks', {})
                phase3_data = phase3_output.get('output_data', {})
                total_cost = phase3_output.get('cost_usd', phase3_data.get('total_cost', 0.0))
                chunk_count = len(chunk_urls)
                cost = total_cost / chunk_count if chunk_count > 0 else 0.0
            
            # Get duration - use model config first (fast), extract from file only if cache exists
            # For performance, we use model config as primary source and only extract when explicitly needed
            phase_outputs = video.phase_outputs or {}
            editing_data = phase_outputs.get('phase6_editing', {})
            chunk_durations_cache = editing_data.get('chunk_durations', {})
            
            chunk_key = f'chunk_{chunk_index}'
            if chunk_key in chunk_durations_cache:
                # Use cached duration (fast, from previous extraction)
                chunk_duration = chunk_durations_cache[chunk_key]
                logger.debug(f"Using cached duration {chunk_duration:.2f}s for chunk {chunk_index}")
            else:
                # Use model config duration (fast, no file download needed)
                # We'll extract actual duration later if needed (e.g., for split operations)
                try:
                    model_config = get_model_config(model)
                    chunk_duration = model_config.get('actual_chunk_duration', 5.0)
                    logger.debug(f"Using model config duration {chunk_duration:.2f}s for chunk {chunk_index} (model: {model})")
                except Exception as e:
                    logger.warning(f"Could not get model config for {model}, using fallback: {e}")
                    chunk_duration = spec.get('chunk_duration', 5.0)
            
            # Calculate chunk start time using cached durations or model config (fast)
            chunk_start_time = 0.0
            for i in range(chunk_index):
                prev_chunk_key = f'chunk_{i}'
                if prev_chunk_key in chunk_durations_cache:
                    # Use cached duration
                    chunk_start_time += chunk_durations_cache[prev_chunk_key]
                else:
                    # Use model config duration for previous chunks (fast, no file download)
                    try:
                        prev_model_config = get_model_config(model)
                        prev_duration = prev_model_config.get('actual_chunk_duration', 5.0)
                        chunk_start_time += prev_duration
                    except Exception:
                        # Fallback to current chunk duration
                        chunk_start_time += chunk_duration
            
            # Find beat that contains this chunk
            beat_info = None
            for beat in beats:
                beat_start = beat.get('start_time', 0)
                beat_duration = beat.get('duration', 0)
                if beat_start <= chunk_start_time < beat_start + beat_duration:
                    beat_info = beat
                    break
            
            # Use prompt from beat if not set from version
            if not prompt and beat_info:
                prompt = beat_info.get('prompt', '')
            
            # Ensure chunk_url is set (fallback to chunk_urls array)
            if not chunk_url and chunk_index < len(chunk_urls):
                chunk_url = chunk_urls[chunk_index]
            
            return {
                'chunk_index': chunk_index,
                'url': chunk_url,
                'prompt': prompt,
                'model': model,
                'cost': cost,
                'duration': chunk_duration,
                'start_time': chunk_start_time,
            }
        except Exception as e:
            logger.error(f"Error getting chunk metadata for video {video_id}, chunk {chunk_index}: {e}")
            return None
    
    def get_chunk_versions(self, video_id: str, chunk_index: int) -> List[ChunkVersion]:
        """
        Get all versions of a chunk (original + replacements).
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index (0-based)
            
        Returns:
            List of ChunkVersion objects
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return []
            
            # Get chunk versions from phase_outputs or initialize
            phase_outputs = video.phase_outputs or {}
            editing_data = phase_outputs.get('phase6_editing', {})
            chunk_versions_data = editing_data.get('chunk_versions', {})
            
            chunk_key = f'chunk_{chunk_index}'
            versions_data = chunk_versions_data.get(chunk_key, {})
            
            # Build ChunkVersion list
            versions = []
            
            # Original version - use chunk URL from list if available
            chunk_urls = video.chunk_urls or []
            original_url = None
            if chunk_index < len(chunk_urls):
                original_url = chunk_urls[chunk_index]
            
            # Get original version data from tracking, or use chunk URL
            original_data = versions_data.get('original', {})
            if not original_url and original_data.get('url'):
                original_url = original_data.get('url')
            
            current_selected = versions_data.get('current_selected', 'original')
            
            # Only add original version if URL exists
            if original_url:
                versions.append(ChunkVersion(
                    version_id='original',
                    url=original_url,
                    prompt=original_data.get('prompt'),
                    model=original_data.get('model'),
                    cost=original_data.get('cost'),
                    created_at=original_data.get('created_at'),
                    is_selected=(current_selected == 'original')
                ))
            
            # Check for split parts FIRST - these override stored versions
            # Split parts should always use URLs from chunk_urls (which are updated after split)
            split_history = editing_data.get('split_history', {})
            is_split_part = False
            split_version_id = None
            split_info_found = None
            
            for split_key, split_info in split_history.items():
                part1_index = split_info.get('part1_index')
                part2_index = split_info.get('part2_index')
                
                if chunk_index == part1_index:
                    is_split_part = True
                    split_version_id = 'split_part1'
                    split_info_found = split_info
                    break
                elif chunk_index == part2_index:
                    is_split_part = True
                    split_version_id = 'split_part2'
                    split_info_found = split_info
                    break
            
            # Replacement versions (but skip split_part1/split_part2 if this is a split part)
            replacements = versions_data.get('replacements', {})
            for version_id, version_data in replacements.items():
                # If this is a split part, skip the stored split_part version (we'll use chunk_urls URL)
                if is_split_part and version_id in ('split_part1', 'split_part2'):
                    continue
                    
                versions.append(ChunkVersion(
                    version_id=version_id,
                    url=version_data.get('url', ''),
                    prompt=version_data.get('prompt'),
                    model=version_data.get('model'),
                    cost=version_data.get('cost'),
                    created_at=version_data.get('created_at'),
                    is_selected=(current_selected == version_id)
                ))
            
            # Add split part version using URL from chunk_urls (most up-to-date)
            if is_split_part and split_version_id and original_url:
                versions.append(ChunkVersion(
                    version_id=split_version_id,
                    url=original_url,  # Always use URL from chunk_urls (updated after split)
                    prompt=original_data.get('prompt') if original_data else None,
                    model=original_data.get('model') if original_data else None,
                    cost=0.0,
                    created_at=split_info_found.get('created_at') if split_info_found else None,
                    is_selected=(current_selected == split_version_id or not any(v.is_selected for v in versions))
                ))
            
            # If no versions found, ensure we at least have the chunk URL from chunk_urls
            if not versions and original_url:
                versions.append(ChunkVersion(
                    version_id='original',
                    url=original_url,
                    prompt=None,
                    model=None,
                    cost=None,
                    created_at=None,
                    is_selected=True
                ))
            
            return versions
        except Exception as e:
            logger.error(f"Error getting chunk versions for video {video_id}, chunk {chunk_index}: {e}")
            return []
    
    def list_all_chunks(self, video_id: str) -> List[ChunkMetadata]:
        """
        Get all chunks for a video (with version info).
        
        Args:
            video_id: Video ID
            
        Returns:
            List of ChunkMetadata objects
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return []
            
            chunk_urls = video.chunk_urls or []
            chunks = []
            
            for i in range(len(chunk_urls)):
                metadata = self.get_chunk_metadata(video_id, i)
                if metadata:
                    versions = self.get_chunk_versions(video_id, i)
                    current_version = 'original'
                    
                    # Find current selected version
                    for version in versions:
                        if version.is_selected:
                            current_version = version.version_id
                            break
                    
                    # Convert S3 URL to presigned URL for frontend
                    chunk_url = metadata['url']
                    if chunk_url.startswith('s3://'):
                        s3_path = chunk_url.replace(f's3://{s3_client.bucket}/', '')
                        chunk_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
                    elif chunk_url and not chunk_url.startswith('http'):
                        # Assume it's an S3 key
                        chunk_url = s3_client.generate_presigned_url(chunk_url, expiration=3600)
                    
                    chunks.append(ChunkMetadata(
                        chunk_index=i,
                        url=chunk_url,
                        prompt=metadata['prompt'],
                        model=metadata['model'],
                        cost=metadata['cost'],
                        duration=metadata['duration'],
                        versions=versions,
                        current_version=current_version
                    ))
            
            return chunks
        except Exception as e:
            logger.error(f"Error listing chunks for video {video_id}: {e}")
            return []
    
    def is_chunk_split_part(self, video_id: str, chunk_index: int) -> Optional[Dict]:
        """
        Check if a chunk is part of a split operation (can be undone).
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index to check
            
        Returns:
            Dictionary with split info if chunk is a split part, None otherwise
            Format: {
                'is_split_part': True,
                'original_index': int,  # Original chunk index before split
                'part_number': 1 or 2,  # Which part (1 or 2)
                'original_url': str,  # Original chunk URL
                'split_time': float,  # Time where split occurred
            }
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return None
            
            phase_outputs = video.phase_outputs or {}
            split_history = phase_outputs.get('phase6_editing', {}).get('split_history', {})
            
            # Check if this chunk index matches part1_index or part2_index
            for key, split_info in split_history.items():
                part1_index = split_info.get('part1_index')
                part2_index = split_info.get('part2_index')
                original_index = split_info.get('original_index')
                
                if chunk_index == part1_index:
                    return {
                        'is_split_part': True,
                        'original_index': original_index,
                        'part_number': 1,
                        'original_url': split_info.get('original_url'),
                        'split_time': split_info.get('split_time'),
                        'part2_index': part2_index,
                    }
                elif chunk_index == part2_index:
                    return {
                        'is_split_part': True,
                        'original_index': original_index,
                        'part_number': 2,
                        'original_url': split_info.get('original_url'),
                        'split_time': split_info.get('split_time'),
                        'part1_index': part1_index,
                    }
            
            return None
        except Exception as e:
            logger.error(f"Error checking if chunk is split part for video {video_id}, chunk {chunk_index}: {e}")
            return None
    
    def get_chunk_preview_url(self, video_id: str, chunk_index: int, version: str = 'current') -> Optional[str]:
        """
        Generate presigned URL for preview (original or new version).
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index (0-based)
            version: Version identifier ('original', 'replacement_1', 'current', etc.)
            
        Returns:
            Presigned URL or None if not found
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return None
            
            chunk_urls = video.chunk_urls or []
            if chunk_index >= len(chunk_urls):
                return None
            
            versions = self.get_chunk_versions(video_id, chunk_index)
            
            # If no versions exist (e.g., split chunks), use chunk URL directly
            if not versions:
                url = chunk_urls[chunk_index]
                if not url:
                    logger.error(f"Empty URL for chunk {chunk_index}")
                    return None
                
                # Convert S3 URL to presigned URL
                try:
                    if url.startswith('s3://'):
                        s3_path = url.replace(f's3://{s3_client.bucket}/', '')
                        presigned_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
                        logger.debug(f"Generated presigned URL for s3:// URL: {presigned_url[:100]}...")
                        return presigned_url
                    elif 's3.amazonaws.com' in url or url.startswith('https://'):
                        # Already a presigned URL or HTTP URL
                        logger.debug(f"Using existing HTTP/presigned URL: {url[:100]}...")
                        return url
                    else:
                        # Assume it's an S3 key
                        presigned_url = s3_client.generate_presigned_url(url, expiration=3600)
                        logger.debug(f"Generated presigned URL for S3 key: {presigned_url[:100]}...")
                        return presigned_url
                except Exception as e:
                    logger.error(f"Error generating presigned URL for chunk {chunk_index}, URL: {url[:100]}... Error: {e}")
                    return None
            
            # Find the requested version
            target_version = None
            if version == 'current':
                # Find currently selected version
                for v in versions:
                    if v.is_selected:
                        target_version = v
                        break
                # If no selected version, use first available
                if not target_version and versions:
                    target_version = versions[0]
            else:
                # Find specific version
                for v in versions:
                    if v.version_id == version:
                        target_version = v
                        break
            
            if not target_version:
                # Fallback to chunk URL from list
                url = chunk_urls[chunk_index] if chunk_index < len(chunk_urls) else None
                if not url:
                    logger.error(f"No URL found for chunk {chunk_index} (no version and no chunk_urls entry)")
                    return None
            else:
                url = target_version.url
                if not url:
                    logger.error(f"Version {target_version.version_id} has no URL for chunk {chunk_index}")
                    # Fallback to chunk URL
                    url = chunk_urls[chunk_index] if chunk_index < len(chunk_urls) else None
                    if not url:
                        return None
            
            # Convert S3 URL to presigned URL
            try:
                if url.startswith('s3://'):
                    # Extract S3 key
                    s3_path = url.replace(f's3://{s3_client.bucket}/', '')
                    presigned_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
                    logger.debug(f"Generated presigned URL for s3:// URL (chunk {chunk_index}): {presigned_url[:100]}...")
                    return presigned_url
                elif 's3.amazonaws.com' in url or url.startswith('https://'):
                    # Already a presigned URL or HTTP URL
                    logger.debug(f"Using existing HTTP/presigned URL (chunk {chunk_index}): {url[:100]}...")
                    return url
                else:
                    # Assume it's an S3 key
                    presigned_url = s3_client.generate_presigned_url(url, expiration=3600)
                    logger.debug(f"Generated presigned URL for S3 key (chunk {chunk_index}): {presigned_url[:100]}...")
                    return presigned_url
            except Exception as e:
                logger.error(f"Error generating presigned URL for chunk {chunk_index}, URL: {url[:100] if url else 'None'}... Error: {e}")
                return None
        except Exception as e:
            logger.error(f"Error getting chunk preview URL for video {video_id}, chunk {chunk_index}, version {version}: {e}")
            return None
    
    def track_chunk_version(
        self,
        video_id: str,
        chunk_index: int,
        version_type: str,
        version_url: str,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        cost: Optional[float] = None
    ) -> bool:
        """
        Track chunk versions (original, replacement_1, replacement_2, etc.).
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index (0-based)
            version_type: Version type ('original', 'replacement_1', 'replacement_2', etc.)
            version_url: S3 URL of the version
            prompt: Prompt used for this version (optional)
            model: Model used for this version (optional)
            cost: Cost of generating this version (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return False
            
            # Initialize phase_outputs if needed
            if not video.phase_outputs:
                video.phase_outputs = {}
            if 'phase6_editing' not in video.phase_outputs:
                video.phase_outputs['phase6_editing'] = {}
            if 'chunk_versions' not in video.phase_outputs['phase6_editing']:
                video.phase_outputs['phase6_editing']['chunk_versions'] = {}
            
            chunk_key = f'chunk_{chunk_index}'
            chunk_versions = video.phase_outputs['phase6_editing']['chunk_versions']
            
            if chunk_key not in chunk_versions:
                chunk_versions[chunk_key] = {
                    'original': {},
                    'replacements': {},
                    'current_selected': 'original'
                }
            
            # Store version data
            version_data = {
                'url': version_url,
                'prompt': prompt,
                'model': model,
                'cost': cost,
                'created_at': datetime.now().isoformat()
            }
            
            if version_type == 'original':
                chunk_versions[chunk_key]['original'] = version_data
            else:
                if 'replacements' not in chunk_versions[chunk_key]:
                    chunk_versions[chunk_key]['replacements'] = {}
                chunk_versions[chunk_key]['replacements'][version_type] = version_data
            
            # Mark as modified for SQLAlchemy
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(video, 'phase_outputs')
            self.db.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error tracking chunk version for video {video_id}, chunk {chunk_index}: {e}")
            self.db.rollback()
            return False
    
    def get_current_chunk_version(self, video_id: str, chunk_index: int) -> Optional[str]:
        """
        Get currently selected version.
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index (0-based)
            
        Returns:
            Version identifier ('original', 'replacement_1', etc.) or None
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return None
            
            phase_outputs = video.phase_outputs or {}
            editing_data = phase_outputs.get('phase6_editing', {})
            chunk_versions_data = editing_data.get('chunk_versions', {})
            
            chunk_key = f'chunk_{chunk_index}'
            versions_data = chunk_versions_data.get(chunk_key, {})
            
            return versions_data.get('current_selected', 'original')
        except Exception as e:
            logger.error(f"Error getting current chunk version for video {video_id}, chunk {chunk_index}: {e}")
            return None
    
    def set_selected_version(self, video_id: str, chunk_index: int, version_id: str) -> bool:
        """
        Set the currently selected version for a chunk.
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index (0-based)
            version_id: Version identifier ('original', 'replacement_1', etc.)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return False
            
            # Initialize phase_outputs if needed
            if not video.phase_outputs:
                video.phase_outputs = {}
            if 'phase6_editing' not in video.phase_outputs:
                video.phase_outputs['phase6_editing'] = {}
            if 'chunk_versions' not in video.phase_outputs['phase6_editing']:
                video.phase_outputs['phase6_editing']['chunk_versions'] = {}
            
            chunk_key = f'chunk_{chunk_index}'
            chunk_versions = video.phase_outputs['phase6_editing']['chunk_versions']
            
            if chunk_key not in chunk_versions:
                chunk_versions[chunk_key] = {
                    'original': {},
                    'replacements': {},
                    'current_selected': 'original'
                }
            
            # Set the selected version
            chunk_versions[chunk_key]['current_selected'] = version_id
            
            # Mark as modified for SQLAlchemy
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(video, 'phase_outputs')
            self.db.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error setting selected version for video {video_id}, chunk {chunk_index}: {e}")
            self.db.rollback()
            return False
    
    def _get_video_duration_from_file(self, video_url: str, video_id: str, chunk_index: int) -> float:
        """
        Extract actual video duration from the video file using ffprobe.
        
        Args:
            video_url: S3 URL or key of the video file
            video_id: Video ID (for logging)
            chunk_index: Chunk index (for logging)
            
        Returns:
            Duration in seconds, or 5.0 as fallback
        """
        temp_dir = None
        try:
            # Download video to temp file
            temp_dir = tempfile.mkdtemp()
            temp_video_path = os.path.join(temp_dir, f'chunk_{chunk_index}.mp4')
            
            # Extract S3 key from URL
            if video_url.startswith('s3://'):
                chunk_key = video_url.replace(f's3://{s3_client.bucket}/', '')
                s3_client.download_file(chunk_key, temp_video_path)
            elif video_url.startswith('http'):
                # Presigned URL - download using requests
                import requests
                response = requests.get(video_url, stream=True, timeout=30)
                response.raise_for_status()
                with open(temp_video_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
            else:
                # Assume it's an S3 key
                chunk_key = video_url
                s3_client.download_file(chunk_key, temp_video_path)
            
            # Use ffprobe to get duration
            probe_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', temp_video_path
            ]
            probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True, timeout=10)
            duration = float(probe_result.stdout.strip())
            
            logger.debug(f"Extracted duration {duration:.2f}s from video file for chunk {chunk_index}")
            return duration
            
        except Exception as e:
            logger.warning(f"Could not extract duration from video file for chunk {chunk_index}: {e}. Using fallback.")
            # Fallback: try to get from model config if we have the model
            try:
                video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
                if video:
                    spec = video.spec or {}
                    model = spec.get('model', 'hailuo_fast')
                    phase_outputs = video.phase_outputs or {}
                    phase3_output = phase_outputs.get('phase3_chunks', {})
                    phase3_spec = phase3_output.get('output_data', {}).get('spec', {})
                    if phase3_spec.get('model'):
                        model = phase3_spec.get('model')
                    model_config = get_model_config(model)
                    return model_config.get('actual_chunk_duration', 5.0)
            except Exception:
                pass
            return 5.0  # Final fallback
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass

