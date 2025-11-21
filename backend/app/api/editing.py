"""
API endpoints for Phase 6: User Editing & Chunk Regeneration
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.common.auth import get_current_user
from app.common.models import VideoGeneration
from app.phases.phase6_editing.service import EditingService
from app.phases.phase6_editing.chunk_manager import ChunkManager
from app.phases.phase6_editing.schemas import (
    EditingRequest,
    EditingResponse,
    CostEstimate,
    ChunksListResponse,
    ChunkMetadata,
    ChunkVersion,
)
from app.orchestrator.celery_app import celery_app
from app.phases.phase6_editing.task import edit_chunks
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/video/{video_id}/edit", response_model=EditingResponse)
async def submit_edits(
    video_id: str,
    request: EditingRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> EditingResponse:
    """
    Submit editing actions for a video.
    
    Args:
        video_id: Video ID
        request: EditingRequest with actions
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        EditingResponse with status and results
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # If only estimating cost, return estimate
        if request.estimate_cost_only:
            editing_service = EditingService(db)
            # Extract model from first replace action
            model = 'hailuo'
            chunk_indices = []
            for action in request.actions:
                if hasattr(action, 'action_type') and action.action_type.value == 'replace':
                    chunk_indices = action.chunk_indices
                    model = action.new_model or 'hailuo'
                    break
            
            if chunk_indices:
                cost_estimate = editing_service.estimate_regeneration_cost(
                    video_id, chunk_indices, model
                )
                return EditingResponse(
                    video_id=video_id,
                    status="success",
                    message="Cost estimate",
                    estimated_cost=cost_estimate.estimated_cost
                )
            else:
                return EditingResponse(
                    video_id=video_id,
                    status="success",
                    message="Cost estimate",
                    estimated_cost=0.0
                )
        
        # Enqueue editing task
        # Convert actions to dict format, ensuring all fields are included
        actions_dict = []
        for action in request.actions:
            if hasattr(action, 'dict'):
                # Pydantic model - use dict() method
                action_dict = action.dict()
            elif isinstance(action, dict):
                # Already a dict - use as-is
                action_dict = action
            else:
                # Fallback - convert to dict
                action_dict = dict(action) if hasattr(action, '__dict__') else {}
            
            # Log action for debugging
            logger.info(f"Action being queued: {action_dict}")
            actions_dict.append(action_dict)
        
        editing_request_dict = {
            'video_id': video_id,
            'actions': actions_dict,
            'estimate_cost_only': request.estimate_cost_only
        }
        
        logger.info(f"Queuing editing task with {len(actions_dict)} actions")
        task = edit_chunks.delay(editing_request_dict)
        
        return EditingResponse(
            video_id=video_id,
            status="processing",
            message=f"Editing task queued: {task.id}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error submitting edits for video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit edits: {str(e)}")


@router.post("/api/video/{video_id}/edit/estimate", response_model=CostEstimate)
async def estimate_edit_cost(
    video_id: str,
    chunk_indices: str = Query(..., description="Comma-separated chunk indices"),
    model: str = Query(default='hailuo'),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CostEstimate:
    """
    Get cost estimate before editing.
    
    Args:
        video_id: Video ID
        chunk_indices: List of chunk indices to regenerate
        model: Model to use for regeneration
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        CostEstimate with estimated cost and time
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Parse comma-separated chunk indices
        try:
            chunk_indices_list = [int(idx.strip()) for idx in chunk_indices.split(',')]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid chunk_indices format")
        
        editing_service = EditingService(db)
        cost_estimate = editing_service.estimate_regeneration_cost(
            video_id, chunk_indices_list, model
        )
        
        return cost_estimate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating cost for video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to estimate cost: {str(e)}")


@router.get("/api/video/{video_id}/chunks", response_model=ChunksListResponse)
async def get_chunks(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChunksListResponse:
    """
    Get all chunks metadata (with versions).
    
    Args:
        video_id: Video ID
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        ChunksListResponse with all chunks and their metadata
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        chunk_manager = ChunkManager(db)
        chunks = chunk_manager.list_all_chunks(video_id)
        
        return ChunksListResponse(
            video_id=video_id,
            chunks=chunks,
            total_chunks=len(chunks),
            stitched_video_url=video.stitched_url
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunks for video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunks: {str(e)}")


@router.get("/api/video/{video_id}/chunks/{chunk_index}", response_model=ChunkMetadata)
async def get_chunk(
    video_id: str,
    chunk_index: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChunkMetadata:
    """
    Get specific chunk metadata.
    
    Args:
        video_id: Video ID
        chunk_index: Chunk index (0-based)
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        ChunkMetadata for the specified chunk
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        chunk_manager = ChunkManager(db)
        metadata = chunk_manager.get_chunk_metadata(video_id, chunk_index)
        
        if not metadata:
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        versions = chunk_manager.get_chunk_versions(video_id, chunk_index)
        current_version = chunk_manager.get_current_chunk_version(video_id, chunk_index) or 'original'
        
        return ChunkMetadata(
            chunk_index=chunk_index,
            url=metadata['url'],
            prompt=metadata['prompt'],
            model=metadata['model'],
            cost=metadata['cost'],
            duration=metadata['duration'],
            versions=versions,
            current_version=current_version
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk {chunk_index} for video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunk: {str(e)}")


@router.get("/api/video/{video_id}/chunks/{chunk_index}/versions", response_model=List[ChunkVersion])
async def get_chunk_versions(
    video_id: str,
    chunk_index: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[ChunkVersion]:
    """
    Get all versions of a chunk.
    
    Args:
        video_id: Video ID
        chunk_index: Chunk index (0-based)
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        List of ChunkVersion objects
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        chunk_manager = ChunkManager(db)
        versions = chunk_manager.get_chunk_versions(video_id, chunk_index)
        
        return versions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk versions for video {video_id}, chunk {chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunk versions: {str(e)}")


@router.get("/api/video/{video_id}/chunks/{chunk_index}/preview")
async def get_chunk_preview(
    video_id: str,
    chunk_index: int,
    version: str = Query(default='current', description="Version identifier ('original', 'replacement_1', 'current', etc.)"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get chunk preview URL (original or new version).
    
    Args:
        video_id: Video ID
        chunk_index: Chunk index (0-based)
        version: Version identifier ('original', 'replacement_1', 'current', etc.)
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        Dictionary with preview_url
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Verify chunk exists
        chunk_urls = video.chunk_urls or []
        if chunk_index >= len(chunk_urls):
            raise HTTPException(status_code=404, detail=f"Chunk index {chunk_index} out of range (total chunks: {len(chunk_urls)})")
        
        chunk_manager = ChunkManager(db)
        preview_url = chunk_manager.get_chunk_preview_url(video_id, chunk_index, version)
        
        if not preview_url:
            logger.error(f"Failed to generate preview URL for video {video_id}, chunk {chunk_index}, version {version}")
            raise HTTPException(status_code=404, detail="Chunk preview not found")
        
        logger.info(f"Generated preview URL for chunk {chunk_index}: {preview_url[:100]}...")
        return {
            'video_id': video_id,
            'chunk_index': chunk_index,
            'version': version,
            'preview_url': preview_url
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk preview for video {video_id}, chunk {chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get chunk preview: {str(e)}")


@router.post("/api/video/{video_id}/chunks/{chunk_index}/select-version")
async def select_chunk_version(
    video_id: str,
    chunk_index: int,
    version: str = Query(..., description="Version identifier ('original', 'replacement_1', etc.)"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Select which version to keep (original or new).
    
    Args:
        video_id: Video ID
        chunk_index: Chunk index (0-based)
        version: Version identifier ('original', 'replacement_1', etc.)
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        Dictionary with status message
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        editing_service = EditingService(db)
        success = editing_service.select_chunk_version(video_id, chunk_index, version)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to select version")
        
        return {
            'video_id': video_id,
            'chunk_index': chunk_index,
            'selected_version': version,
            'status': 'success',
            'message': f'Version {version} selected for chunk {chunk_index}'
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error selecting chunk version for video {video_id}, chunk {chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to select version: {str(e)}")


@router.get("/api/video/{video_id}/editing/status")
async def get_editing_status(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get editing status for a video.
    
    Args:
        video_id: Video ID
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        Dictionary with editing status
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        phase_outputs = video.phase_outputs or {}
        editing_data = phase_outputs.get('phase6_editing', {})
        
        status = editing_data.get('status', 'not_started')
        
        # If status is 'failed', include error message
        response = {
            'video_id': video_id,
            'status': status,
            'updated_chunk_urls': editing_data.get('updated_chunk_urls'),
            'updated_stitched_url': editing_data.get('updated_stitched_url'),
            'total_cost': editing_data.get('total_cost', 0.0),
        }
        
        if status == 'failed':
            response['error_message'] = editing_data.get('error_message', 'Unknown error')
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting editing status for video {video_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get editing status: {str(e)}")


@router.get("/api/video/{video_id}/chunks/{chunk_index}/split-info")
async def get_chunk_split_info(
    video_id: str,
    chunk_index: int,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Check if a chunk is part of a split operation (can be undone).
    
    Args:
        video_id: Video ID
        chunk_index: Chunk index to check
        user_id: Authenticated user ID
        db: Database session
        
    Returns:
        Dictionary with split info or null if not a split part
    """
    try:
        # Verify video belongs to user
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        chunk_manager = ChunkManager(db)
        split_info = chunk_manager.is_chunk_split_part(video_id, chunk_index)
        
        return split_info or {'is_split_part': False}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chunk split info for video {video_id}, chunk {chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get split info: {str(e)}")

