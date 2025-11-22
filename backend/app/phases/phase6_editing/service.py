"""
Editing Service for Phase 6

Processes editing actions and coordinates chunk regeneration.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.common.models import VideoGeneration
from app.common.exceptions import PhaseException
from app.phases.phase6_editing.chunk_manager import ChunkManager
from app.phases.phase6_editing.schemas import (
    EditingAction,
    EditingActionType,
    ReplaceChunkAction,
    SelectVersionAction,
    ReorderChunkAction,
    DeleteChunkAction,
    SplitChunkAction,
    UndoSplitAction,
    CostEstimate,
)
from app.phases.phase3_chunks.chunk_generator import (
    generate_single_chunk_with_storyboard,
    generate_single_chunk_continuous,
    build_chunk_specs_with_storyboard,
    calculate_beat_to_chunk_mapping,
)
from app.phases.phase3_chunks.schemas import ChunkSpec
from app.phases.phase3_chunks.stitcher import VideoStitcher
from app.phases.phase3_chunks.model_config import get_model_config
from app.services.s3 import s3_client
from app.common.constants import get_video_s3_key
import logging
import subprocess
import os
import tempfile

logger = logging.getLogger(__name__)


class EditingService:
    """Service for processing editing actions and coordinating regeneration"""
    
    def __init__(self, db: Optional[Session] = None):
        """Initialize EditingService with optional database session"""
        self.db = db or SessionLocal()
        self.chunk_manager = ChunkManager(self.db)
        self.stitcher = VideoStitcher()
    
    def process_edits(self, video_id: str, editing_actions: List[EditingAction]) -> Dict:
        """
        Main entry point for processing edits.
        
        Args:
            video_id: Video ID
            editing_actions: List of editing actions to perform
            
        Returns:
            Dictionary with updated chunk_urls, stitched_url, total_cost, etc.
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                raise PhaseException(f"Video {video_id} not found")
            
            # Get current state
            chunk_urls = video.chunk_urls or []
            spec = video.spec or {}
            user_id = video.user_id
            
            # Process each action (actions can be dicts or objects)
            updated_chunk_urls = chunk_urls.copy()
            total_cost = 0.0
            
            for action in editing_actions:
                # Handle both dict and object formats
                if isinstance(action, dict):
                    action_type = action.get('action_type')
                    chunk_indices = action.get('chunk_indices', [])
                else:
                    action_type = action.action_type
                    chunk_indices = action.chunk_indices
                
                if action_type == EditingActionType.REPLACE.value or action_type == 'replace':
                    # Parse replace action
                    if isinstance(action, dict):
                        new_prompt = action.get('new_prompt')
                        new_model = action.get('new_model')
                        keep_original = action.get('keep_original', True)
                    else:
                        new_prompt = action.new_prompt
                        new_model = action.new_model
                        keep_original = action.keep_original
                    
                    result = self.replace_chunks(
                        video_id, chunk_indices, new_prompt,
                        new_model, keep_original, spec, user_id
                    )
                    # Update chunk URLs for replaced chunks
                    for idx, new_url in zip(chunk_indices, result['new_chunk_urls']):
                        if idx < len(updated_chunk_urls):
                            updated_chunk_urls[idx] = new_url
                    total_cost += result['cost']
                
                elif action_type == EditingActionType.SELECT_VERSION.value or action_type == 'select_version':
                    # Parse select version action
                    if isinstance(action, dict):
                        version = action.get('version')
                    else:
                        version = action.version
                    
                    self.select_chunk_version(video_id, chunk_indices[0], version)
                    # Update chunk URL to selected version
                    versions = self.chunk_manager.get_chunk_versions(video_id, chunk_indices[0])
                    for version_obj in versions:
                        if version_obj.version_id == version:
                            if chunk_indices[0] < len(updated_chunk_urls):
                                updated_chunk_urls[chunk_indices[0]] = version_obj.url
                            break
                
                elif action_type == EditingActionType.REORDER.value or action_type == 'reorder':
                    # Parse reorder action
                    if isinstance(action, dict):
                        new_order = action.get('new_order', [])
                    else:
                        new_order = action.new_order
                    
                    updated_chunk_urls = self.reorder_chunks(updated_chunk_urls, new_order)
                
                elif action_type == EditingActionType.DELETE.value or action_type == 'delete':
                    updated_chunk_urls = self.delete_chunks(updated_chunk_urls, chunk_indices)
                
                elif action_type == EditingActionType.SPLIT.value or action_type == 'split':
                    # Parse split action - support time, frame, or percentage
                    if isinstance(action, dict):
                        split_time = action.get('split_time')
                        split_frame = action.get('split_frame')
                        split_percentage = action.get('split_percentage')
                        logger.info(f"Split action received: {action}")
                    else:
                        split_time = getattr(action, 'split_time', None)
                        split_frame = getattr(action, 'split_frame', None)
                        split_percentage = getattr(action, 'split_percentage', None)
                    
                    # Convert to appropriate types
                    if split_time is not None:
                        try:
                            split_time = float(split_time)
                        except (ValueError, TypeError):
                            raise PhaseException(f"split_time must be a number, got {split_time}")
                    
                    if split_frame is not None:
                        try:
                            split_frame = int(split_frame)
                        except (ValueError, TypeError):
                            raise PhaseException(f"split_frame must be a number, got {split_frame}")
                    
                    if split_percentage is not None:
                        try:
                            split_percentage = float(split_percentage)
                        except (ValueError, TypeError):
                            raise PhaseException(f"split_percentage must be a number, got {split_percentage}")
                    
                    # At least one must be provided
                    if split_time is None and split_frame is None and split_percentage is None:
                        raise PhaseException("Must provide split_time, split_frame, or split_percentage")
                    
                    logger.info(f"Splitting chunk {chunk_indices[0]} - time: {split_time}, frame: {split_frame}, percentage: {split_percentage}")
                    
                    result = self.split_chunk(
                        video_id, chunk_indices[0],
                        split_time=split_time,
                        split_frame=split_frame,
                        split_percentage=split_percentage,
                        spec=spec,
                        user_id=user_id
                    )
                    # Replace chunk with two new chunks
                    idx = chunk_indices[0]
                    updated_chunk_urls = (
                        updated_chunk_urls[:idx] +
                        result['new_chunk_urls'] +
                        updated_chunk_urls[idx+1:]
                    )
                    total_cost += result['cost']
                
                elif action_type == EditingActionType.UNDO_SPLIT.value or action_type == 'undo_split':
                    # Undo split: restore original chunk
                    # chunk_indices[0] should be the first part of the split
                    # We need to find the split history and restore the original
                    first_part_index = chunk_indices[0]
                    result = self.undo_split(video_id, first_part_index, spec, user_id)
                    if result:
                        # Replace the two split parts with the original chunk
                        updated_chunk_urls = result['updated_chunk_urls']
                        total_cost += result.get('cost', 0.0)
                    else:
                        raise PhaseException(f"Failed to undo split for chunk {first_part_index}")
            
            # Re-stitch video with updated chunks
            # Always re-stitch after edits (replace, delete, split, reorder)
            # select_version doesn't change chunk URLs, so no re-stitch needed
            transitions = spec.get('transitions', [])
            stitched_video_url = self.restitch_video(
                video_id, updated_chunk_urls, transitions, user_id
            )
            
            return {
                'updated_chunk_urls': updated_chunk_urls,
                'updated_stitched_url': stitched_video_url,
                'total_cost': total_cost,
            }
        except Exception as e:
            logger.error(f"Error processing edits for video {video_id}: {e}")
            raise PhaseException(f"Failed to process edits: {str(e)}")
    
    def replace_chunks(
        self,
        video_id: str,
        chunk_indices: List[int],
        new_prompt: Optional[str],
        new_model: Optional[str],
        keep_original: bool,
        spec: Dict,
        user_id: Optional[str]
    ) -> Dict:
        """
        Replace chunks (generate new version, keep original).
        
        Args:
            video_id: Video ID
            chunk_indices: List of chunk indices to replace
            new_prompt: New prompt (if None, uses original)
            new_model: New model (if None, uses original)
            keep_original: Whether to keep original version
            spec: Video specification
            user_id: User ID
            
        Returns:
            Dictionary with new_chunk_urls and cost
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                raise PhaseException(f"Video {video_id} not found")
            
            chunk_urls = video.chunk_urls or []
            beats = spec.get('beats', [])
            chunk_duration = spec.get('chunk_duration', 5.0)
            model = new_model or spec.get('model', 'hailuo')
            
            # Get model config
            model_config = get_model_config(model)
            actual_chunk_duration = model_config.get('actual_chunk_duration', chunk_duration)
            
            # Calculate beat-to-chunk mapping
            beat_to_chunk_map = calculate_beat_to_chunk_mapping(beats, actual_chunk_duration)
            
            new_chunk_urls = []
            total_cost = 0.0
            
            for chunk_idx in chunk_indices:
                if chunk_idx >= len(chunk_urls):
                    continue
                
                # Get original chunk metadata
                chunk_metadata = self.chunk_manager.get_chunk_metadata(video_id, chunk_idx)
                if not chunk_metadata:
                    continue
                
                original_prompt = new_prompt or chunk_metadata['prompt']
                original_model = model
                
                # Build chunk spec for regeneration
                chunk_start_time = chunk_idx * actual_chunk_duration
                
                # Find beat for this chunk
                beat_info = None
                for beat in beats:
                    beat_start = beat.get('start_time', 0)
                    beat_duration = beat.get('duration', 0)
                    if beat_start <= chunk_start_time < beat_start + beat_duration:
                        beat_info = beat
                        break
                
                if not beat_info:
                    beat_info = beats[0] if beats else {}
                
                # Determine if this chunk starts a beat (uses storyboard image)
                use_storyboard = chunk_idx in beat_to_chunk_map
                storyboard_image_url = beat_info.get('image_url') if use_storyboard else None
                
                # Only use storyboard if image actually exists
                if use_storyboard and not storyboard_image_url:
                    use_storyboard = False
                
                # Get previous chunk's last frame for temporal coherence
                previous_last_frame = None
                if chunk_idx > 0:
                    prev_chunk_url = chunk_urls[chunk_idx - 1]
                    previous_last_frame = self._extract_last_frame(prev_chunk_url, video_id, chunk_idx - 1)
                
                # Build ChunkSpec
                chunk_spec = ChunkSpec(
                    video_id=video_id,
                    user_id=user_id,
                    chunk_num=chunk_idx,
                    start_time=chunk_start_time,
                    duration=actual_chunk_duration,
                    beat=beat_info,
                    animatic_frame_url=None,  # Not used in storyboard mode
                    style_guide_url=storyboard_image_url,  # Storyboard image or None
                    product_reference_url=None,  # Not used for regeneration
                    previous_chunk_last_frame=previous_last_frame,
                    prompt=original_prompt,
                    model=original_model,
                    use_text_to_video=not use_storyboard and not previous_last_frame,
                )
                
                # Generate new chunk
                if use_storyboard and storyboard_image_url:
                    # Use storyboard image from beat
                    chunk_spec_dict = chunk_spec.dict()
                    result = generate_single_chunk_with_storyboard(
                        chunk_spec_dict,
                        beat_to_chunk_map
                    )
                elif previous_last_frame:
                    # Use last frame continuation
                    result = generate_single_chunk_continuous(chunk_spec)
                else:
                    # Text-to-video fallback (no storyboard, no previous frame)
                    chunk_spec_dict = chunk_spec.dict()
                    result = generate_single_chunk_with_storyboard(
                        chunk_spec_dict,
                        beat_to_chunk_map
                    )
                
                new_chunk_url = result['chunk_url']
                chunk_cost = result.get('cost', 0.0)
                
                # Track version
                replacement_num = self._get_next_replacement_number(video_id, chunk_idx)
                version_id = f'replacement_{replacement_num}'
                
                self.chunk_manager.track_chunk_version(
                    video_id=video_id,
                    chunk_index=chunk_idx,
                    version_type=version_id,
                    version_url=new_chunk_url,
                    prompt=original_prompt,
                    model=original_model,
                    cost=chunk_cost
                )
                
                new_chunk_urls.append(new_chunk_url)
                total_cost += chunk_cost
            
            return {
                'new_chunk_urls': new_chunk_urls,
                'cost': total_cost,
            }
        except Exception as e:
            logger.error(f"Error replacing chunks for video {video_id}: {e}")
            raise PhaseException(f"Failed to replace chunks: {str(e)}")
    
    def select_chunk_version(self, video_id: str, chunk_index: int, version: str) -> bool:
        """
        User selects which version to keep (original or new).
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index
            version: Version identifier ('original', 'replacement_1', etc.)
            
        Returns:
            True if successful
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                return False
            
            # Update current_selected in phase_outputs
            if not video.phase_outputs:
                video.phase_outputs = {}
            if 'phase6_editing' not in video.phase_outputs:
                video.phase_outputs['phase6_editing'] = {}
            if 'chunk_versions' not in video.phase_outputs['phase6_editing']:
                video.phase_outputs['phase6_editing']['chunk_versions'] = {}
            
            chunk_key = f'chunk_{chunk_index}'
            chunk_versions = video.phase_outputs['phase6_editing']['chunk_versions']
            
            if chunk_key not in chunk_versions:
                return False
            
            chunk_versions[chunk_key]['current_selected'] = version
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(video, 'phase_outputs')
            self.db.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error selecting chunk version for video {video_id}, chunk {chunk_index}: {e}")
            self.db.rollback()
            return False
    
    def get_chunk_versions(self, video_id: str, chunk_index: int) -> List:
        """Get all versions of a chunk (original + replacements)"""
        return self.chunk_manager.get_chunk_versions(video_id, chunk_index)
    
    def reorder_chunks(self, chunk_urls: List[str], new_order: List[int]) -> List[str]:
        """
        Reorder chunks.
        
        Args:
            chunk_urls: Current list of chunk URLs
            new_order: New order of chunk indices
            
        Returns:
            Reordered list of chunk URLs
        """
        if len(new_order) != len(chunk_urls):
            raise PhaseException("New order must have same length as chunk URLs")
        
        return [chunk_urls[i] for i in new_order]
    
    def delete_chunks(self, chunk_urls: List[str], chunk_indices: List[int]) -> List[str]:
        """
        Delete chunks.
        
        Args:
            chunk_urls: Current list of chunk URLs
            chunk_indices: List of chunk indices to delete
            
        Returns:
            Updated list of chunk URLs (with deleted chunks removed)
        """
        # Sort indices in descending order to delete from end
        sorted_indices = sorted(chunk_indices, reverse=True)
        
        updated_urls = chunk_urls.copy()
        for idx in sorted_indices:
            if 0 <= idx < len(updated_urls):
                updated_urls.pop(idx)
        
        return updated_urls
    
    def split_chunk(
        self,
        video_id: str,
        chunk_index: int,
        split_time: Optional[float] = None,
        split_frame: Optional[int] = None,
        split_percentage: Optional[float] = None,
        spec: Dict = None,
        user_id: Optional[str] = None
    ) -> Dict:
        """
        Split chunk at specific frame.
        
        Args:
            video_id: Video ID
            chunk_index: Chunk index to split
            split_frame: Frame number to split at (0-indexed)
            spec: Video specification
            user_id: User ID
            
        Returns:
            Dictionary with new_chunk_urls (2 chunks), original_url, and cost
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                raise PhaseException(f"Video {video_id} not found")
            
            chunk_urls = video.chunk_urls or []
            if chunk_index >= len(chunk_urls):
                raise PhaseException(f"Chunk index {chunk_index} out of range")
            
            chunk_url = chunk_urls[chunk_index]
            chunk_duration = spec.get('chunk_duration', 5.0)
            fps = spec.get('fps', 24)
            
            # Get metadata for original chunk
            beats = spec.get('beats', [])
            chunk_start_time = chunk_index * chunk_duration
            beat_info = None
            for beat in beats:
                beat_start = beat.get('start_time', 0)
                beat_duration = beat.get('duration', 0)
                if beat_start <= chunk_start_time < beat_start + beat_duration:
                    beat_info = beat
                    break
            
            prompt = beat_info.get('prompt', '') if beat_info else ''
            model = spec.get('model', 'hailuo')
            
            # Track original chunk as a version BEFORE splitting
            # This allows undo functionality
            self.chunk_manager.track_chunk_version(
                video_id=video_id,
                chunk_index=chunk_index,
                version_type='original',
                version_url=chunk_url,
                prompt=prompt,
                model=model,
                cost=0.0
            )
            
            # Download chunk
            temp_dir = tempfile.mkdtemp()
            chunk_path = os.path.join(temp_dir, 'chunk.mp4')
            
            if chunk_url.startswith('s3://'):
                chunk_key = chunk_url.replace(f's3://{s3_client.bucket}/', '')
            else:
                chunk_key = chunk_url
            
            s3_client.download_file(chunk_key, chunk_path)
            
            # Get actual video duration from file
            probe_cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', chunk_path
            ]
            try:
                probe_result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True, timeout=10)
                video_duration = float(probe_result.stdout.strip())
            except (subprocess.CalledProcessError, ValueError) as e:
                logger.warning(f"Could not probe video duration, using spec duration: {e}")
                video_duration = chunk_duration
            
            # Calculate split_time from various input methods
            calculated_split_time = None
            
            if split_time is not None:
                # Direct time input (preferred)
                if split_time <= 0:
                    raise PhaseException(f"Split time must be greater than 0, got {split_time}")
                if split_time >= video_duration:
                    raise PhaseException(f"Split time {split_time}s exceeds video duration {video_duration:.2f}s")
                calculated_split_time = split_time
            elif split_percentage is not None:
                # Percentage-based split
                if split_percentage <= 0 or split_percentage >= 100:
                    raise PhaseException(f"Split percentage must be between 0 and 100, got {split_percentage}")
                calculated_split_time = video_duration * (split_percentage / 100.0)
            elif split_frame is not None:
                # Frame-based split (fallback)
                if split_frame <= 0:
                    raise PhaseException(f"Split frame must be greater than 0, got {split_frame}")
                max_frame = int(video_duration * fps)
                if split_frame >= max_frame:
                    raise PhaseException(f"Split frame {split_frame} exceeds video length ({max_frame} frames)")
                calculated_split_time = split_frame / fps
            else:
                raise PhaseException("Must provide split_time, split_percentage, or split_frame")
            
            # Ensure split_time is within valid range
            calculated_split_time = max(0.1, min(calculated_split_time, video_duration - 0.1))
            
            logger.info(f"Splitting chunk {chunk_index} at {calculated_split_time:.2f}s (duration: {video_duration:.2f}s)")
            
            # First part: 0 to calculated_split_time
            part1_path = os.path.join(temp_dir, 'part1.mp4')
            cmd1 = [
                'ffmpeg', '-y', '-i', chunk_path,
                '-t', str(calculated_split_time),
                '-c', 'copy',
                part1_path
            ]
            logger.info(f"Running FFmpeg command: {' '.join(cmd1)}")
            result1 = subprocess.run(cmd1, capture_output=True, text=True, check=False, timeout=60)
            if result1.returncode != 0:
                error_msg = result1.stderr or result1.stdout or 'Unknown FFmpeg error'
                logger.error(f"FFmpeg failed for part1: {error_msg}")
                raise PhaseException(f"Failed to create first part: {error_msg}")
            
            # Second part: calculated_split_time to end
            part2_path = os.path.join(temp_dir, 'part2.mp4')
            cmd2 = [
                'ffmpeg', '-y', '-i', chunk_path,
                '-ss', str(calculated_split_time),
                '-c', 'copy',
                part2_path
            ]
            logger.info(f"Running FFmpeg command: {' '.join(cmd2)}")
            result2 = subprocess.run(cmd2, capture_output=True, text=True, check=False, timeout=60)
            if result2.returncode != 0:
                error_msg = result2.stderr or result2.stdout or 'Unknown FFmpeg error'
                logger.error(f"FFmpeg failed for part2: {error_msg}")
                raise PhaseException(f"Failed to create second part: {error_msg}")
            
            # Verify both parts were created
            if not os.path.exists(part1_path):
                raise PhaseException("First part was not created")
            if not os.path.exists(part2_path):
                raise PhaseException("Second part was not created")
            
            logger.info(f"Successfully split chunk into two parts: {os.path.getsize(part1_path)} bytes and {os.path.getsize(part2_path)} bytes")
            
            # Upload both parts to S3
            part1_key = get_video_s3_key(user_id, video_id, f'chunks/chunk_{chunk_index:02d}_part1.mp4')
            part2_key = get_video_s3_key(user_id, video_id, f'chunks/chunk_{chunk_index:02d}_part2.mp4')
            
            part1_url = s3_client.upload_file(part1_path, part1_key)
            part2_url = s3_client.upload_file(part2_path, part2_key)
            
            # Track split parts as versions (for potential undo)
            # Store metadata about the split in phase_outputs
            if not video.phase_outputs:
                video.phase_outputs = {}
            if 'phase6_editing' not in video.phase_outputs:
                video.phase_outputs['phase6_editing'] = {}
            if 'split_history' not in video.phase_outputs['phase6_editing']:
                video.phase_outputs['phase6_editing']['split_history'] = {}
            
            # Record split operation for undo capability
            split_key = f'chunk_{chunk_index}'
            video.phase_outputs['phase6_editing']['split_history'][split_key] = {
                'original_url': chunk_url,
                'original_index': chunk_index,
                'split_time': calculated_split_time,
                'split_frame': int(calculated_split_time * fps) if split_frame is None else split_frame,
                'video_duration': video_duration,
                'part1_url': part1_url,
                'part2_url': part2_url,
                'part1_index': chunk_index,  # First part replaces original
                'part2_index': chunk_index + 1,  # Second part is inserted after
                'created_at': datetime.now().isoformat()
            }
            
            # Track split parts as versions for the new chunk indices
            # Part 1 (at original index)
            self.chunk_manager.track_chunk_version(
                video_id=video_id,
                chunk_index=chunk_index,
                version_type='split_part1',
                version_url=part1_url,
                prompt=prompt,
                model=model,
                cost=0.0
            )
            
            # Part 2 (at original index + 1)
            self.chunk_manager.track_chunk_version(
                video_id=video_id,
                chunk_index=chunk_index + 1,
                version_type='split_part2',
                version_url=part2_url,
                prompt=prompt,
                model=model,
                cost=0.0
            )
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(video, 'phase_outputs')
            self.db.commit()
            
            # Cleanup
            os.remove(chunk_path)
            os.remove(part1_path)
            os.remove(part2_path)
            os.rmdir(temp_dir)
            
            return {
                'new_chunk_urls': [part1_url, part2_url],
                'original_url': chunk_url,  # Keep original for undo
                'cost': 0.0,  # No generation cost, just splitting
            }
        except Exception as e:
            logger.error(f"Error splitting chunk for video {video_id}, chunk {chunk_index}: {e}")
            raise PhaseException(f"Failed to split chunk: {str(e)}")
    
    def undo_split(
        self,
        video_id: str,
        first_part_index: int,
        spec: Dict,
        user_id: Optional[str]
    ) -> Optional[Dict]:
        """
        Undo a split operation by restoring the original chunk.
        
        Args:
            video_id: Video ID
            first_part_index: Index of the first part of the split (chunk that was split)
            spec: Video specification
            user_id: User ID
            
        Returns:
            Dictionary with updated_chunk_urls and cost, or None if undo failed
        """
        try:
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                logger.error(f"Video {video_id} not found")
                return None
            
            chunk_urls = video.chunk_urls or []
            if first_part_index >= len(chunk_urls):
                logger.error(f"Chunk index {first_part_index} out of range")
                return None
            
            # Get split history
            phase_outputs = video.phase_outputs or {}
            split_history = phase_outputs.get('phase6_editing', {}).get('split_history', {})
            
            # Find the split that created this chunk
            # The split history is keyed by the original chunk index
            # We need to find which original chunk was split to create first_part_index
            original_chunk_index = None
            split_info = None
            
            for key, info in split_history.items():
                # Check if first_part_index matches the position where part1 would be
                original_idx = info.get('original_index')
                if original_idx is not None:
                    # After split, part1 is at original_idx, part2 is at original_idx+1
                    if original_idx == first_part_index:
                        original_chunk_index = original_idx
                        split_info = info
                        break
            
            if not split_info:
                logger.error(f"No split history found for chunk {first_part_index}")
                return None
            
            original_url = split_info.get('original_url')
            if not original_url:
                logger.error(f"No original URL found in split history")
                return None
            
            # Verify that chunk_urls[first_part_index] and chunk_urls[first_part_index+1] are the split parts
            if first_part_index + 1 >= len(chunk_urls):
                logger.error(f"Cannot undo split: second part not found at index {first_part_index + 1}")
                return None
            
            part1_url = chunk_urls[first_part_index]
            part2_url = chunk_urls[first_part_index + 1]
            
            # Replace the two parts with the original chunk
            updated_chunk_urls = (
                chunk_urls[:first_part_index] +
                [original_url] +
                chunk_urls[first_part_index + 2:]
            )
            
            # Remove from split history
            split_key = f'chunk_{original_chunk_index}'
            if split_key in split_history:
                del split_history[split_key]
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(video, 'phase_outputs')
                self.db.commit()
            
            logger.info(f"Successfully undid split for chunk {first_part_index}, restored original chunk")
            
            return {
                'updated_chunk_urls': updated_chunk_urls,
                'cost': 0.0,  # No cost for undo
            }
        except Exception as e:
            logger.error(f"Error undoing split for video {video_id}, chunk {first_part_index}: {e}")
            self.db.rollback()
            return None
    
    def restitch_video(
        self,
        video_id: str,
        chunk_urls: List[str],
        transitions: List[Dict],
        user_id: Optional[str]
    ) -> str:
        """
        Re-stitch video after edits.
        
        Args:
            video_id: Video ID
            chunk_urls: Updated list of chunk URLs
            transitions: Transition specifications
            user_id: User ID
            
        Returns:
            S3 URL of re-stitched video
        """
        return self.stitcher.stitch_with_transitions(
            video_id=video_id,
            chunk_urls=chunk_urls,
            transitions=transitions,
            user_id=user_id
        )
    
    def estimate_regeneration_cost(
        self,
        video_id: str,
        chunk_indices: List[int],
        model: str
    ) -> CostEstimate:
        """
        Calculate cost before regeneration.
        
        Args:
            video_id: Video ID
            chunk_indices: List of chunk indices to regenerate
            model: Model to use for regeneration
            
        Returns:
            CostEstimate object
        """
        try:
            model_config = get_model_config(model)
            cost_per_generation = model_config.get('cost_per_generation', 0.0)
            actual_chunk_duration = model_config.get('actual_chunk_duration', 5.0)
            
            # Cost is per generation (per chunk), not per second
            cost_per_chunk = cost_per_generation
            total_cost = cost_per_chunk * len(chunk_indices)
            
            # Estimate time (rough: 45 seconds per chunk)
            estimated_time = 45 * len(chunk_indices)
            
            cost_per_chunk_dict = {idx: cost_per_chunk for idx in chunk_indices}
            
            return CostEstimate(
                video_id=video_id,
                chunk_indices=chunk_indices,
                model=model,
                estimated_cost=total_cost,
                estimated_time_seconds=estimated_time,
                cost_per_chunk=cost_per_chunk_dict
            )
        except Exception as e:
            logger.error(f"Error estimating cost for video {video_id}: {e}")
            raise PhaseException(f"Failed to estimate cost: {str(e)}")
    
    def _extract_last_frame(self, chunk_url: str, video_id: str, chunk_index: int) -> Optional[str]:
        """Extract last frame from chunk for temporal coherence"""
        try:
            temp_dir = tempfile.mkdtemp()
            chunk_path = os.path.join(temp_dir, 'chunk.mp4')
            frame_path = os.path.join(temp_dir, 'last_frame.jpg')
            
            # Download chunk
            if chunk_url.startswith('s3://'):
                chunk_key = chunk_url.replace(f's3://{s3_client.bucket}/', '')
            else:
                chunk_key = chunk_url
            
            s3_client.download_file(chunk_key, chunk_path)
            
            # Extract last frame using FFmpeg
            # Get total frames first
            probe_cmd = [
                'ffprobe', '-v', 'error', '-select_streams', 'v:0',
                '-count_frames', '-show_entries', 'stream=nb_frames',
                '-of', 'default=nokey=1:noprint_wrappers=1',
                chunk_path
            ]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            total_frames = int(result.stdout.strip()) if result.stdout.strip() else None
            
            if total_frames:
                # Extract last frame
                fps = 24  # Default FPS
                last_frame_time = (total_frames - 1) / fps
                cmd = [
                    'ffmpeg', '-y', '-i', chunk_path,
                    '-ss', str(last_frame_time),
                    '-vframes', '1',
                    frame_path
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            else:
                # Fallback: use sseof to get last frame
                cmd = [
                    'ffmpeg', '-y', '-sseof', '-1', '-i', chunk_path,
                    '-update', '1',
                    '-q:v', '2',
                    frame_path
                ]
                subprocess.run(cmd, check=True, capture_output=True)
            
            # Upload frame to S3
            video = self.db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            user_id = video.user_id if video else None
            
            frame_key = get_video_s3_key(user_id, video_id, f'frames/last_frame_{chunk_index}.jpg')
            frame_url = s3_client.upload_file(frame_path, frame_key)
            
            # Cleanup
            os.remove(chunk_path)
            os.remove(frame_path)
            os.rmdir(temp_dir)
            
            return frame_url
        except Exception as e:
            logger.error(f"Error extracting last frame from {chunk_url}: {e}")
            return None
    
    def _get_next_replacement_number(self, video_id: str, chunk_index: int) -> int:
        """Get next replacement number for a chunk"""
        versions = self.chunk_manager.get_chunk_versions(video_id, chunk_index)
        replacement_nums = []
        for version in versions:
            if version.version_id.startswith('replacement_'):
                try:
                    num = int(version.version_id.split('_')[1])
                    replacement_nums.append(num)
                except:
                    pass
        return max(replacement_nums) + 1 if replacement_nums else 1

