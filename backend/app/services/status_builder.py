# Helper functions for building StatusResponse from Redis or DB
from typing import Dict, Any, Optional, List
from app.common.schemas import StatusResponse, CheckpointInfo, CheckpointTreeNode, BranchInfo, CheckpointResponse, ArtifactResponse
from app.common.models import VideoGeneration
from app.services.redis import RedisClient
from app.services.s3 import s3_client
from app.database.checkpoint_queries import (
    get_current_checkpoint,
    get_checkpoint_artifacts,
    get_latest_artifacts_for_checkpoint,
    build_checkpoint_tree,
    get_leaf_checkpoints
)

# Initialize Redis client
redis_client = RedisClient()


def _convert_s3_to_presigned(url: str) -> str:
    """Convert S3 URL to presigned URL"""
    if url and url.startswith('s3://'):
        s3_path = url.replace(f's3://{s3_client.bucket}/', '')
        return s3_client.generate_presigned_url(s3_path, expiration=3600)
    return url


def _get_presigned_url_from_cache(video_id: str, key: str, s3_url: str) -> str:
    """Get presigned URL from Redis cache or generate and cache it"""
    if not s3_url or not s3_url.startswith('s3://'):
        return s3_url
    
    # Check Redis cache first
    if redis_client._client:
        try:
            cached_urls = redis_client.get_video_data(video_id)
            if cached_urls and cached_urls.get("presigned_urls"):
                cached = cached_urls["presigned_urls"].get(key)
                if cached:
                    return cached
        except Exception:
            pass
    
    # Generate presigned URL
    presigned = _convert_s3_to_presigned(s3_url)
    
    # Cache in Redis
    if redis_client._client:
        try:
            existing_data = redis_client.get_video_data(video_id)
            presigned_urls = existing_data.get("presigned_urls", {}) if existing_data else {}
            presigned_urls[key] = presigned
            redis_client.set_video_presigned_urls(video_id, presigned_urls)
        except Exception:
            pass
    
    return presigned


def _build_checkpoint_info(video_id: str) -> Optional[CheckpointInfo]:
    """Build CheckpointInfo from current checkpoint"""
    try:
        current_checkpoint = get_current_checkpoint(video_id)
        if not current_checkpoint:
            return None
        
        # Get artifacts for this checkpoint
        artifacts_dict = {}
        artifacts = get_latest_artifacts_for_checkpoint(current_checkpoint['id'])
        
        for artifact_key, artifact_data in artifacts.items():
            artifact_s3_url = artifact_data['s3_url']
            presigned_url = _get_presigned_url_from_cache(
                video_id,
                artifact_key,
                artifact_s3_url
            )
            
            artifacts_dict[artifact_key] = ArtifactResponse(
                id=artifact_data['id'],
                artifact_type=artifact_data['artifact_type'],
                artifact_key=artifact_key,
                s3_url=presigned_url,
                version=artifact_data['version'],
                metadata=artifact_data.get('metadata'),
                created_at=artifact_data['created_at']
            )
        
        return CheckpointInfo(
            checkpoint_id=current_checkpoint['id'],
            branch_name=current_checkpoint['branch_name'],
            phase_number=current_checkpoint['phase_number'],
            version=current_checkpoint['version'],
            status=current_checkpoint['status'],
            created_at=current_checkpoint['created_at'],
            artifacts=artifacts_dict
        )
    except Exception:
        return None


def _build_checkpoint_tree_nodes(video_id: str) -> Optional[List[CheckpointTreeNode]]:
    """Build checkpoint tree for status response"""
    try:
        tree_data = build_checkpoint_tree(video_id)
        if not tree_data:
            return None
        
        def convert_to_node(cp_data: Dict) -> CheckpointTreeNode:
            # Get artifacts for this checkpoint
            artifacts_list = []
            artifacts = get_latest_artifacts_for_checkpoint(cp_data['id'])
            
            for artifact_key, artifact_data in artifacts.items():
                artifact_s3_url = artifact_data['s3_url']
                presigned_url = _get_presigned_url_from_cache(
                    video_id,
                    artifact_key,
                    artifact_s3_url
                )
                
                artifacts_list.append(ArtifactResponse(
                    id=artifact_data['id'],
                    artifact_type=artifact_data['artifact_type'],
                    artifact_key=artifact_key,
                    s3_url=presigned_url,
                    version=artifact_data['version'],
                    metadata=artifact_data.get('metadata'),
                    created_at=artifact_data['created_at']
                ))
            
            checkpoint = CheckpointResponse(
                id=cp_data['id'],
                video_id=cp_data['video_id'],
                branch_name=cp_data['branch_name'],
                phase_number=cp_data['phase_number'],
                version=cp_data['version'],
                status=cp_data['status'],
                approved_at=cp_data.get('approved_at'),
                created_at=cp_data['created_at'],
                cost_usd=cp_data.get('cost_usd', 0.0),
                parent_checkpoint_id=cp_data.get('parent_checkpoint_id'),
                user_id=cp_data['user_id'],
                edit_description=cp_data.get('edit_description'),
                artifacts=artifacts_list
            )
            
            # Recursively convert children
            children = [convert_to_node(child) for child in cp_data.get('children', [])]
            
            return CheckpointTreeNode(checkpoint=checkpoint, children=children)
        
        return [convert_to_node(root) for root in tree_data]
    except Exception:
        return None


def _build_active_branches(video_id: str) -> Optional[List[BranchInfo]]:
    """Build active branches list from leaf checkpoints"""
    try:
        leaf_checkpoints = get_leaf_checkpoints(video_id)
        if not leaf_checkpoints:
            return None
        
        branches = []
        for cp in leaf_checkpoints:
            # Check if checkpoint can continue (is pending)
            can_continue = cp['status'] == 'pending'
            
            branches.append(BranchInfo(
                branch_name=cp['branch_name'],
                latest_checkpoint_id=cp['id'],
                phase_number=cp['phase_number'],
                status=cp['status'],
                can_continue=can_continue
            ))
        
        return branches
    except Exception:
        return None


def build_status_response_from_redis_video_data(redis_data: Dict[str, Any]) -> StatusResponse:
    """Build StatusResponse from Redis video data dict"""
    # Extract basic fields
    video_id = redis_data.get("video_id", "")
    status = redis_data.get("status", "queued")
    progress = redis_data.get("progress", 0.0)
    current_phase = redis_data.get("current_phase")
    error = redis_data.get("error_message")
    metadata = redis_data.get("metadata", {})
    phase_outputs = redis_data.get("phase_outputs", {})
    spec = redis_data.get("spec", {})
    
    # Calculate estimated time remaining
    estimated_time_remaining = None
    if status not in ["complete", "failed"]:
        if progress > 0:
            estimated_time_remaining = int((100 - progress) / progress * 600)  # seconds
    
    # Extract phase outputs
    storyboard_urls = None
    reference_assets = None
    stitched_video_url = None
    current_chunk_index = None
    total_chunks = None
    
    # Check Redis first for storyboard URLs
    storyboard_urls_raw = redis_data.get('storyboard_urls')
    
    if storyboard_urls_raw:
        # Convert S3 URLs to presigned URLs
        storyboard_urls = []
        for idx, url in enumerate(storyboard_urls_raw):
            presigned = _get_presigned_url_from_cache(video_id, f"storyboard_{idx}", url)
            storyboard_urls.append(presigned)
    elif phase_outputs:
        # Fallback: Extract from phase_outputs/spec
        phase2_output = phase_outputs.get('phase2_storyboard')
        if phase2_output and phase2_output.get('status') == 'success':
            phase2_data = phase2_output.get('output_data', {})
            spec_data = phase2_data.get('spec', {}) or spec
            beats = spec_data.get('beats', [])
            storyboard_urls_raw = []
            
            for beat in beats:
                image_url = beat.get('image_url')
                if image_url:
                    storyboard_urls_raw.append(image_url)
            
            if storyboard_urls_raw:
                storyboard_urls = []
                for idx, url in enumerate(storyboard_urls_raw):
                    presigned = _get_presigned_url_from_cache(video_id, f"storyboard_{idx}", url)
                    storyboard_urls.append(presigned)
        
        # Phase 3: Stitched video and chunk progress
        phase3_output = phase_outputs.get('phase3_chunks')
        chunk_urls = None
        if phase3_output:
            if isinstance(phase3_output, dict):
                current_chunk_index = phase3_output.get('current_chunk_index')
                total_chunks = phase3_output.get('total_chunks')
            
            if phase3_output.get('status') == 'success':
                phase3_data = phase3_output.get('output_data', {})
                stitched_url = phase3_data.get('stitched_video_url')
                if stitched_url:
                    stitched_video_url = _get_presigned_url_from_cache(
                        video_id, "stitched_video_url", stitched_url
                    )
                
                # Extract chunk URLs
                chunk_urls_raw = phase3_data.get('chunk_urls', [])
                if chunk_urls_raw:
                    chunk_urls = []
                    for idx, url in enumerate(chunk_urls_raw):
                        presigned = _get_presigned_url_from_cache(
                            video_id, f"chunk_{idx}", url
                        )
                        chunk_urls.append(presigned)
    
    # Phase 4: Final video
    final_video_url = None
    # Check metadata for final_video_url (set on completion)
    final_url = metadata.get('final_video_url')
    if final_url:
        final_video_url = _get_presigned_url_from_cache(video_id, "final_video_url", final_url)
    elif phase_outputs:
        phase4_output = phase_outputs.get('phase4_refine')
        if phase4_output and phase4_output.get('status') == 'success':
            phase4_data = phase4_output.get('output_data', {})
            refined_url = phase4_data.get('refined_video_url')
            if refined_url:
                final_video_url = _get_presigned_url_from_cache(
                    video_id, "refined_video_url", refined_url
                )
    
    # Build checkpoint information
    current_checkpoint = _build_checkpoint_info(video_id)
    checkpoint_tree = _build_checkpoint_tree_nodes(video_id)
    active_branches = _build_active_branches(video_id)
    
    return StatusResponse(
        video_id=video_id,
        status=status,
        progress=progress,
        current_phase=current_phase,
        estimated_time_remaining=estimated_time_remaining,
        error=error,
        storyboard_urls=storyboard_urls,
        reference_assets=reference_assets,
        chunk_urls=chunk_urls,
        stitched_video_url=stitched_video_url,
        final_video_url=final_video_url,
        current_chunk_index=current_chunk_index,
        total_chunks=total_chunks,
        current_checkpoint=current_checkpoint,
        checkpoint_tree=checkpoint_tree,
        active_branches=active_branches
    )


def build_status_response_from_db(video: VideoGeneration) -> StatusResponse:
    """Build StatusResponse from DB VideoGeneration model"""
    # Calculate estimated time remaining
    estimated_time_remaining = None
    if video.status.value not in ["complete", "failed"]:
        if video.progress > 0:
            estimated_time_remaining = int((100 - video.progress) / video.progress * 600)  # seconds
    
    # Extract phase outputs
    storyboard_urls = None
    reference_assets = None
    stitched_video_url = None
    current_chunk_index = None
    total_chunks = None
    
    # Check Redis first for storyboard URLs
    redis_data = redis_client.get_video_data(video.id)
    storyboard_urls_raw = redis_data.get('storyboard_urls') if redis_data else None
    
    if storyboard_urls_raw:
        # Convert S3 URLs to presigned URLs
        storyboard_urls = []
        for idx, url in enumerate(storyboard_urls_raw):
            presigned = _get_presigned_url_from_cache(video.id, f"storyboard_{idx}", url)
            storyboard_urls.append(presigned)
    elif video.phase_outputs:
        # Fallback: Extract from phase_outputs/spec
        phase2_output = video.phase_outputs.get('phase2_storyboard')
        if phase2_output and phase2_output.get('status') == 'success':
            phase2_data = phase2_output.get('output_data', {})
            spec = phase2_data.get('spec', {}) or video.spec or {}
            beats = spec.get('beats', [])
            storyboard_urls_raw = []
            
            for beat in beats:
                image_url = beat.get('image_url')
                if image_url:
                    storyboard_urls_raw.append(image_url)
            
            if storyboard_urls_raw:
                storyboard_urls = []
                for idx, url in enumerate(storyboard_urls_raw):
                    presigned = _get_presigned_url_from_cache(video.id, f"storyboard_{idx}", url)
                    storyboard_urls.append(presigned)
        
        # Phase 3: Stitched video and chunk progress
        phase3_output = video.phase_outputs.get('phase3_chunks')
        chunk_urls = None
        if phase3_output:
            if isinstance(phase3_output, dict):
                current_chunk_index = phase3_output.get('current_chunk_index')
                total_chunks = phase3_output.get('total_chunks')
            
            if phase3_output.get('status') == 'success':
                phase3_data = phase3_output.get('output_data', {})
                stitched_url = phase3_data.get('stitched_video_url') or video.stitched_url
                if stitched_url:
                    stitched_video_url = _get_presigned_url_from_cache(
                        video.id, "stitched_video_url", stitched_url
                    )
                
                # Extract chunk URLs from phase_outputs or video.chunk_urls
                chunk_urls_raw = phase3_data.get('chunk_urls') or video.chunk_urls or []
                if chunk_urls_raw:
                    chunk_urls = []
                    for idx, url in enumerate(chunk_urls_raw):
                        presigned = _get_presigned_url_from_cache(
                            video.id, f"chunk_{idx}", url
                        )
                        chunk_urls.append(presigned)
    
    # Phase 4: Final video
    final_video_url = None
    if video.final_video_url:
        final_video_url = _get_presigned_url_from_cache(
            video.id, "final_video_url", video.final_video_url
        )
    elif video.phase_outputs:
        phase4_output = video.phase_outputs.get('phase4_refine')
        if phase4_output and phase4_output.get('status') == 'success':
            phase4_data = phase4_output.get('output_data', {})
            refined_url = phase4_data.get('refined_video_url') or video.refined_url
            if refined_url:
                final_video_url = _get_presigned_url_from_cache(
                    video.id, "refined_video_url", refined_url
                )
    
    return StatusResponse(
        video_id=video.id,
        status=video.status.value,
        progress=video.progress,
        current_phase=video.current_phase,
        estimated_time_remaining=estimated_time_remaining,
        error=video.error_message,
        storyboard_urls=storyboard_urls,
        reference_assets=reference_assets,
        chunk_urls=chunk_urls,
        stitched_video_url=stitched_video_url,
        final_video_url=final_video_url,
        current_chunk_index=current_chunk_index,
        total_chunks=total_chunks,
        current_checkpoint=current_checkpoint,
        checkpoint_tree=checkpoint_tree,
        active_branches=active_branches
    )

