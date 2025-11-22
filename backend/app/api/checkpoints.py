"""Checkpoint API endpoints for video generation pipeline"""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import uuid
import os

from app.common.auth import get_current_user
from app.common.schemas import (
    CheckpointResponse,
    ArtifactResponse,
    CheckpointTreeNode,
    BranchInfo,
    ContinueRequest,
    ContinueResponse,
    SpecEditRequest,
    RegenerateBeatRequest,
    RegenerateChunkRequest,
    ArtifactEditResponse
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
    build_checkpoint_tree,
    get_latest_artifact_version,
    get_next_version_number,
    create_artifact,
    update_checkpoint_phase_output,
    update_artifact
)
from app.orchestrator.pipeline import dispatch_next_phase
from app.services.s3 import s3_client
from app.phases.phase2_storyboard.image_generation import generate_beat_image
from app.phases.phase3_chunks.chunk_generator import generate_single_chunk_with_storyboard
from app.phases.phase3_chunks.schemas import ChunkSpec

logger = logging.getLogger(__name__)

router = APIRouter()


def _build_artifact_response(artifact: Dict[str, Any]) -> ArtifactResponse:
    """Convert artifact dict to response schema"""
    # Convert S3 URI to presigned URL
    s3_url = artifact['s3_url']
    if s3_url and s3_url.startswith('s3://'):
        s3_path = s3_url.replace(f's3://{s3_client.bucket}/', '')
        s3_url = s3_client.generate_presigned_url(s3_path, expiration=3600)

    return ArtifactResponse(
        id=artifact['id'],
        artifact_type=artifact['artifact_type'],
        artifact_key=artifact['artifact_key'],
        s3_url=s3_url,
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
        checkpoint_response = _build_checkpoint_response(node, include_artifacts=True)
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

    # Check if checkpoint has been edited
    has_edits = has_checkpoint_been_edited(request.checkpoint_id)

    # Check if already approved (only reject if approved AND no edits)
    if checkpoint['status'] == 'approved' and not has_edits:
        raise HTTPException(status_code=400, detail="Checkpoint already approved and has no edits")

    # Determine branch for next phase
    if has_edits:
        # Create new branch: main → main-1, main-1 → main-1-1
        next_branch = create_branch_from_checkpoint(request.checkpoint_id, user_id)
        created_new_branch = True
    else:
        # Continue on same branch
        next_branch = checkpoint['branch_name']
        created_new_branch = False

    # Approve this checkpoint (if not already approved)
    if checkpoint['status'] != 'approved':
        approve_checkpoint(request.checkpoint_id)

    # Determine next phase number
    next_phase_number = checkpoint['phase_number'] + 1

    if next_phase_number > 4:
        raise HTTPException(status_code=400, detail="Already at final phase")

    # Update checkpoint's phase_output with branch context BEFORE dispatching
    # This ensures dispatch_next_phase reads the correct branch info from DB
    phase_output_updates = {
        '_branch_name': next_branch,
        '_parent_checkpoint_id': request.checkpoint_id,
        '_version': 1  # First version on new/same branch
    }
    update_checkpoint_phase_output(request.checkpoint_id, phase_output_updates)

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


@router.patch("/api/video/{video_id}/checkpoints/{checkpoint_id}/spec")
async def edit_spec(
    video_id: str,
    checkpoint_id: str,
    spec_edits: SpecEditRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ArtifactEditResponse:
    """
    Edit Phase 1 spec (beats, style, product, audio).

    Merges provided fields with existing spec and creates new artifact version.
    Only works at Phase 1 checkpoints.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get checkpoint
    checkpoint = get_checkpoint(checkpoint_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Verify checkpoint belongs to this video
    if checkpoint['video_id'] != video_id:
        raise HTTPException(status_code=400, detail="Checkpoint does not belong to this video")

    # Verify checkpoint belongs to this user
    if checkpoint['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify checkpoint is Phase 1
    if checkpoint['phase_number'] != 1:
        raise HTTPException(status_code=400, detail="Can only edit spec at Phase 1 checkpoint")

    # Get current spec artifact
    current_spec_artifact = get_latest_artifact_version(
        checkpoint_id, 'spec', 'spec'
    )

    if not current_spec_artifact:
        raise HTTPException(status_code=404, detail="Spec artifact not found")

    # Get current spec from metadata
    current_spec = current_spec_artifact.get('metadata', {}).get('spec', {})

    # Apply edits (merge with existing)
    updated_spec = {**current_spec}
    edit_dict = spec_edits.model_dump(exclude_unset=True)

    for key, value in edit_dict.items():
        if value is not None:
            updated_spec[key] = value

    # Increment version number
    next_version = current_spec_artifact['version'] + 1

    # Update existing artifact
    update_artifact(
        artifact_id=current_spec_artifact['id'],
        version=next_version,
        metadata={'spec': updated_spec}
    )

    # Update checkpoint's phase_output
    if 'output_data' in checkpoint['phase_output']:
        checkpoint['phase_output']['output_data']['spec'] = updated_spec
    else:
        checkpoint['phase_output']['spec'] = updated_spec

    update_checkpoint_phase_output(checkpoint_id, checkpoint['phase_output'])

    logger.info(f"Edited spec for checkpoint {checkpoint_id}, updated artifact to version {next_version}")

    return ArtifactEditResponse(
        artifact_id=current_spec_artifact['id'],
        version=next_version,
        s3_url=None,
        message=f"Spec updated successfully (version {next_version})"
    )


@router.post("/api/video/{video_id}/checkpoints/{checkpoint_id}/upload-image")
async def upload_replacement_image(
    video_id: str,
    checkpoint_id: str,
    beat_index: int = Form(...),
    image: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ArtifactEditResponse:
    """
    Upload replacement image for specific beat at Phase 2.

    Uploads to S3 with versioned path and creates new artifact version.
    Only works at Phase 2 checkpoints.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get checkpoint
    checkpoint = get_checkpoint(checkpoint_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Verify checkpoint belongs to this video
    if checkpoint['video_id'] != video_id:
        raise HTTPException(status_code=400, detail="Checkpoint does not belong to this video")

    # Verify checkpoint belongs to this user
    if checkpoint['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify checkpoint is Phase 2
    if checkpoint['phase_number'] != 2:
        raise HTTPException(status_code=400, detail="Can only upload images at Phase 2 checkpoint")

    # Get spec to validate beat_index
    phase_output = checkpoint['phase_output']
    spec = phase_output.get('output_data', {}).get('spec', {})
    beats = spec.get('beats', [])

    if beat_index < 0 or beat_index >= len(beats):
        raise HTTPException(status_code=400, detail=f"Beat index {beat_index} out of range (0-{len(beats)-1})")

    # Save uploaded file temporarily
    temp_path = f"/tmp/{uuid.uuid4()}{os.path.splitext(image.filename)[1]}"
    try:
        with open(temp_path, 'wb') as f:
            contents = await image.read()
            f.write(contents)

        # Get current artifact
        current_artifact = get_latest_artifact_version(
            checkpoint_id, 'beat_image', f'beat_{beat_index}'
        )

        if not current_artifact:
            raise HTTPException(status_code=404, detail=f"Beat {beat_index} artifact not found")

        # Increment version
        next_version = current_artifact['version'] + 1

        # Upload to S3 with versioned path (keep version in filename for reference)
        s3_key = f"{user_id}/videos/{video_id}/beat_{beat_index:02d}_edited.png"
        s3_url = s3_client.upload_file(temp_path, s3_key)

        # Update existing artifact
        beat = beats[beat_index]
        update_artifact(
            artifact_id=current_artifact['id'],
            s3_url=s3_url,
            s3_key=s3_key,
            version=next_version,
            metadata={
                'beat_id': beat.get('beat_id', f'beat_{beat_index}'),
                'uploaded_by_user': True,
                'original_filename': image.filename
            }
        )

        logger.info(f"Uploaded image for checkpoint {checkpoint_id} beat {beat_index}, updated to version {next_version}")

        return ArtifactEditResponse(
            artifact_id=current_artifact['id'],
            version=next_version,
            s3_url=s3_url,
            message=f"Image uploaded successfully for beat {beat_index} (version {next_version})"
        )

    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-beat")
async def regenerate_beat(
    video_id: str,
    checkpoint_id: str,
    request: RegenerateBeatRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ArtifactEditResponse:
    """
    Regenerate specific beat image at Phase 2 using FLUX.

    Calls FLUX to generate new image and uploads to S3 with versioned path.
    Only works at Phase 2 checkpoints.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get checkpoint
    checkpoint = get_checkpoint(checkpoint_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Verify checkpoint belongs to this video
    if checkpoint['video_id'] != video_id:
        raise HTTPException(status_code=400, detail="Checkpoint does not belong to this video")

    # Verify checkpoint belongs to this user
    if checkpoint['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify checkpoint is Phase 2
    if checkpoint['phase_number'] != 2:
        raise HTTPException(status_code=400, detail="Can only regenerate beats at Phase 2 checkpoint")

    # Get spec and beat
    phase_output = checkpoint['phase_output']
    spec = phase_output.get('output_data', {}).get('spec', {})
    beats = spec.get('beats', [])
    style = spec.get('style', {})
    product = spec.get('product', {})

    if request.beat_index < 0 or request.beat_index >= len(beats):
        raise HTTPException(status_code=400, detail=f"Beat index {request.beat_index} out of range (0-{len(beats)-1})")

    beat = beats[request.beat_index]

    # Use override prompt if provided
    if request.prompt_override:
        beat = {**beat, 'prompt_template': request.prompt_override}

    # Get current artifact
    current_artifact = get_latest_artifact_version(
        checkpoint_id, 'beat_image', f'beat_{request.beat_index}'
    )

    if not current_artifact:
        raise HTTPException(status_code=404, detail=f"Beat {request.beat_index} artifact not found")

    # Increment version
    next_version = current_artifact['version'] + 1

    try:
        # Call FLUX to regenerate image
        logger.info(f"Regenerating beat {request.beat_index} for checkpoint {checkpoint_id}")
        new_beat_image = generate_beat_image(
            video_id=video_id,
            beat_index=request.beat_index,
            beat=beat,
            style=style,
            product=product,
            user_id=user_id,
            version=next_version
        )

        # Update existing artifact
        update_artifact(
            artifact_id=current_artifact['id'],
            s3_url=new_beat_image['image_url'],
            s3_key=new_beat_image['s3_key'],
            version=next_version,
            metadata={
                'beat_id': beat.get('beat_id'),
                'prompt_used': new_beat_image['prompt_used'],
                'shot_type': new_beat_image['shot_type'],
                'regenerated': True,
                'prompt_override': request.prompt_override
            }
        )

        logger.info(f"Successfully regenerated beat {request.beat_index}, updated to version {next_version}")

        return ArtifactEditResponse(
            artifact_id=current_artifact['id'],
            version=next_version,
            s3_url=new_beat_image['image_url'],
            message=f"Beat {request.beat_index} regenerated successfully (version {next_version})"
        )

    except Exception as e:
        logger.error(f"Failed to regenerate beat {request.beat_index}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate beat: {str(e)}")


@router.post("/api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-chunk")
async def regenerate_chunk(
    video_id: str,
    checkpoint_id: str,
    request: RegenerateChunkRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ArtifactEditResponse:
    """
    Regenerate specific video chunk at Phase 3.

    Calls video generation model (hailuo/kling/veo) to regenerate chunk.
    Only works at Phase 3 checkpoints.
    """
    # Verify ownership
    _verify_video_ownership(video_id, user_id, db)

    # Get checkpoint
    checkpoint = get_checkpoint(checkpoint_id)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    # Verify checkpoint belongs to this video
    if checkpoint['video_id'] != video_id:
        raise HTTPException(status_code=400, detail="Checkpoint does not belong to this video")

    # Verify checkpoint belongs to this user
    if checkpoint['user_id'] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Verify checkpoint is Phase 3
    if checkpoint['phase_number'] != 3:
        raise HTTPException(status_code=400, detail="Can only regenerate chunks at Phase 3 checkpoint")

    # Get phase output to extract chunk information
    phase_output = checkpoint['phase_output']
    output_data = phase_output.get('output_data', {})
    chunk_specs = output_data.get('chunk_specs', [])

    if request.chunk_index < 0 or request.chunk_index >= len(chunk_specs):
        raise HTTPException(
            status_code=400,
            detail=f"Chunk index {request.chunk_index} out of range (0-{len(chunk_specs)-1})"
        )

    # Get the chunk spec to regenerate
    chunk_spec_dict = chunk_specs[request.chunk_index]

    # Apply model override if provided
    if request.model_override:
        chunk_spec_dict['model'] = request.model_override

    # Get current artifact
    current_artifact = get_latest_artifact_version(
        checkpoint_id, 'video_chunk', f'chunk_{request.chunk_index}'
    )

    if not current_artifact:
        raise HTTPException(status_code=404, detail=f"Chunk {request.chunk_index} artifact not found")

    # Increment version
    next_version = current_artifact['version'] + 1

    # Update chunk_spec with version information
    chunk_spec_dict['version'] = next_version

    try:
        # Call chunk generation function
        logger.info(
            f"Regenerating chunk {request.chunk_index} for checkpoint {checkpoint_id} "
            f"with model {chunk_spec_dict.get('model', 'hailuo')}"
        )

        # Get beat_to_chunk_map if available
        beat_to_chunk_map = output_data.get('beat_to_chunk_map', {})

        # Generate the chunk
        result = generate_single_chunk_with_storyboard(
            chunk_spec=chunk_spec_dict,
            beat_to_chunk_map=beat_to_chunk_map
        )

        # Extract S3 URL and key from result
        chunk_url = result['chunk_url']
        s3_key = chunk_url.replace(f's3://{s3_client.bucket}/', '') if chunk_url.startswith('s3://') else chunk_url

        # Update existing artifact
        update_artifact(
            artifact_id=current_artifact['id'],
            s3_url=chunk_url,
            s3_key=s3_key,
            version=next_version,
            metadata={
                'chunk_index': request.chunk_index,
                'model': chunk_spec_dict.get('model', 'hailuo'),
                'regenerated': True,
                'model_override': request.model_override,
                'cost_usd': result.get('cost', 0),
                'init_image_source': result.get('init_image_source')
            }
        )

        logger.info(f"Successfully regenerated chunk {request.chunk_index}, updated to version {next_version}")

        return ArtifactEditResponse(
            artifact_id=current_artifact['id'],
            version=next_version,
            s3_url=chunk_url,
            message=f"Chunk {request.chunk_index} regenerated successfully (version {next_version})"
        )

    except Exception as e:
        logger.error(f"Failed to regenerate chunk {request.chunk_index}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to regenerate chunk: {str(e)}")
