"""Checkpoint API endpoints for video generation pipeline"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging

from app.common.auth import get_current_user
from app.common.schemas import (
    CheckpointResponse,
    ArtifactResponse,
    CheckpointTreeNode,
    BranchInfo,
    ContinueRequest,
    ContinueResponse
)
from app.common.models import VideoGeneration, VideoStatus
from app.database import get_db
from app.database.checkpoint_queries import (
    get_checkpoint,
    list_checkpoints,
    get_checkpoint_artifacts,
    get_current_checkpoint,
    get_leaf_checkpoints,
    approve_checkpoint,
    has_checkpoint_been_edited,
    create_branch_from_checkpoint,
    get_checkpoint_tree,
    build_checkpoint_tree
)
from app.orchestrator.pipeline import dispatch_next_phase

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_artifact_response(artifact: Dict[str, Any]) -> ArtifactResponse:
    """Convert artifact dict to response schema"""
    return ArtifactResponse(
        id=artifact['id'],
        artifact_type=artifact['artifact_type'],
        artifact_key=artifact['artifact_key'],
        s3_url=artifact['s3_url'],
        version=artifact['version'],
        metadata=artifact.get('metadata'),
        created_at=artifact['created_at']
    )


def _build_checkpoint_response(checkpoint: Dict[str, Any], include_artifacts: bool = True) -> CheckpointResponse:
    """Convert checkpoint dict to response schema"""
    artifacts = []
    if include_artifacts:
        artifact_dicts = get_checkpoint_artifacts(checkpoint['id'])
        artifacts = [_build_artifact_response(a) for a in artifact_dicts]

    return CheckpointResponse(
        id=checkpoint['id'],
        video_id=checkpoint['video_id'],
        branch_name=checkpoint['branch_name'],
        phase_number=checkpoint['phase_number'],
        version=checkpoint['version'],
        status=checkpoint['status'],
        approved_at=checkpoint.get('approved_at'),
        created_at=checkpoint['created_at'],
        cost_usd=float(checkpoint['cost_usd']),
        parent_checkpoint_id=checkpoint.get('parent_checkpoint_id'),
        artifacts=artifacts,
        user_id=checkpoint['user_id'],
        edit_description=checkpoint.get('edit_description')
    )


def _verify_video_ownership(video_id: str, user_id: str, db: Session) -> VideoGeneration:
    """Verify user owns the video, raise 404 if not found or 403 if not owned"""
    video = db.query(VideoGeneration).filter(
        VideoGeneration.id == video_id
    ).first()

    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if video.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this video")

    return video


@router.get("/api/video/{video_id}/checkpoints")
async def list_video_checkpoints(
    video_id: str,
    branch_name: str = None,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[CheckpointResponse]:
    """
    List all checkpoints for a video, optionally filtered by branch.

    Returns checkpoints ordered by created_at.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get checkpoints
    checkpoints = list_checkpoints(video_id, branch_name)

    # Convert to response schema
    return [_build_checkpoint_response(cp, include_artifacts=False) for cp in checkpoints]


@router.get("/api/video/{video_id}/checkpoints/{checkpoint_id}")
async def get_checkpoint_details(
    video_id: str,
    checkpoint_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CheckpointResponse:
    """
    Get detailed checkpoint information including all artifacts.

    Artifacts include presigned S3 URLs for viewing.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get checkpoint
    checkpoint = get_checkpoint(checkpoint_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Verify checkpoint belongs to this video
    if checkpoint['video_id'] != video_id:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return _build_checkpoint_response(checkpoint, include_artifacts=True)


@router.get("/api/video/{video_id}/checkpoints/current")
async def get_current_video_checkpoint(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> CheckpointResponse:
    """
    Get the current pending checkpoint (most recent unapproved).

    Returns 404 if no pending checkpoint exists.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get current checkpoint
    checkpoint = get_current_checkpoint(video_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="No pending checkpoint found")

    return _build_checkpoint_response(checkpoint, include_artifacts=True)


@router.get("/api/video/{video_id}/branches")
async def list_active_branches(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[BranchInfo]:
    """
    List all active branches (leaf checkpoints) for a video.

    A branch is active if it has no child checkpoints.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get leaf checkpoints
    leaf_checkpoints = get_leaf_checkpoints(video_id)

    # Convert to branch info
    branches = []
    for checkpoint in leaf_checkpoints:
        branches.append(BranchInfo(
            branch_name=checkpoint['branch_name'],
            latest_checkpoint_id=checkpoint['id'],
            phase_number=checkpoint['phase_number'],
            status=checkpoint['status'],
            can_continue=checkpoint['status'] == 'pending'
        ))

    return branches


@router.get("/api/video/{video_id}/checkpoint-tree")
async def get_checkpoint_tree_structure(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[CheckpointTreeNode]:
    """
    Get the checkpoint tree structure for visualization.

    Returns root checkpoints with nested children.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Build tree structure (function takes video_id)
    tree = build_checkpoint_tree(video_id)

    # Convert to response schema
    def convert_tree_node(node: Dict) -> CheckpointTreeNode:
        checkpoint_response = _build_checkpoint_response(node, include_artifacts=False)
        children = [convert_tree_node(child) for child in node.get('children', [])]
        return CheckpointTreeNode(checkpoint=checkpoint_response, children=children)

    return [convert_tree_node(node) for node in tree]


@router.post("/api/video/{video_id}/continue")
async def continue_pipeline(
    video_id: str,
    request: ContinueRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ContinueResponse:
    """
    Approve checkpoint and continue to next phase.

    If checkpoint has been edited (artifacts versioned), creates new branch.
    Dispatches next phase with branch context.
    """
    # Verify ownership
    video = _verify_video_ownership(video_id, user_id, db)

    # Get checkpoint
    checkpoint = get_checkpoint(request.checkpoint_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Verify checkpoint belongs to this video
    if checkpoint['video_id'] != video_id:
        raise HTTPException(status_code=400, detail="Checkpoint does not belong to this video")

    # Verify checkpoint belongs to this user
    if checkpoint['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check if already approved
    if checkpoint['status'] == 'approved':
        raise HTTPException(status_code=400, detail="Checkpoint already approved")

    # Check if checkpoint has been edited
    has_edits = has_checkpoint_been_edited(request.checkpoint_id)

    # Determine branch for next phase
    if has_edits:
        # Create new branch: main → main-1, main-1 → main-1-1
        next_branch = create_branch_from_checkpoint(request.checkpoint_id, user_id)
        created_new_branch = True
    else:
        # Continue on same branch
        next_branch = checkpoint['branch_name']
        created_new_branch = False

    # Approve this checkpoint
    approve_checkpoint(request.checkpoint_id)

    # Get phase output to pass to next phase
    phase_output = checkpoint['phase_output']

    # Add branch context for next phase
    phase_output['_branch_name'] = next_branch
    phase_output['_parent_checkpoint_id'] = request.checkpoint_id
    phase_output['_version'] = 1  # First version on new/same branch

    # Determine next phase number
    next_phase_number = checkpoint['phase_number'] + 1

    if next_phase_number > 4:
        raise HTTPException(status_code=400, detail="Already at final phase")

    # Update video status
    status_map = {
        2: VideoStatus.GENERATING_ANIMATIC,
        3: VideoStatus.GENERATING_CHUNKS,
        4: VideoStatus.REFINING
    }
    video.status = status_map[next_phase_number]
    db.commit()

    # Dispatch next phase
    try:
        dispatch_next_phase(video_id, request.checkpoint_id)
    except Exception as e:
        logger.error(f"Failed to dispatch next phase: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to dispatch next phase: {str(e)}")

    return ContinueResponse(
        message="Pipeline continued",
        next_phase=next_phase_number,
        branch_name=next_branch,
        created_new_branch=created_new_branch
    )
