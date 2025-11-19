# Helper functions for building StatusResponse from Redis or DB
from typing import Dict, Any, Optional
from app.common.schemas import StatusResponse
from app.common.models import VideoGeneration
from app.services.redis import RedisClient
from app.services.s3 import s3_client

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
    animatic_urls = None
    reference_assets = None
    stitched_video_url = None
    current_chunk_index = None
    total_chunks = None
    
    if phase_outputs:
        # Phase 2: Storyboard images
        phase2_output = phase_outputs.get('phase2_storyboard') or phase_outputs.get('phase2_animatic')
        if phase2_output and phase2_output.get('status') == 'success':
            phase2_data = phase2_output.get('output_data', {})
            spec_data = phase2_data.get('spec', {}) or spec
            beats = spec_data.get('beats', [])
            animatic_urls_raw = []
            
            for beat in beats:
                image_url = beat.get('image_url')
                if image_url:
                    animatic_urls_raw.append(image_url)
            
            if not animatic_urls_raw:
                animatic_urls_raw = phase2_data.get('animatic_urls', [])
            
            if animatic_urls_raw:
                animatic_urls = []
                for url in animatic_urls_raw:
                    presigned = _get_presigned_url_from_cache(video_id, f"animatic_{len(animatic_urls)}", url)
                    animatic_urls.append(presigned)
        
        # Phase 3: Reference assets
        phase3_output = phase_outputs.get('phase3_references')
        if phase3_output and phase3_output.get('status') == 'success':
            reference_assets = phase3_output.get('output_data', {}).copy()
            
            # Convert S3 URLs to presigned URLs
            style_guide_url = reference_assets.get('style_guide_url')
            if style_guide_url:
                reference_assets['style_guide_url'] = _get_presigned_url_from_cache(
                    video_id, "style_guide_url", style_guide_url
                )
            
            product_reference_url = reference_assets.get('product_reference_url')
            if product_reference_url:
                reference_assets['product_reference_url'] = _get_presigned_url_from_cache(
                    video_id, "product_reference_url", product_reference_url
                )
            
            uploaded_assets = reference_assets.get('uploaded_assets')
            if uploaded_assets:
                for i, asset in enumerate(uploaded_assets):
                    s3_url = asset.get('s3_url')
                    if s3_url:
                        asset['s3_url'] = _get_presigned_url_from_cache(
                            video_id, f"uploaded_asset_{i}", s3_url
                        )
        
        # Phase 4: Stitched video and chunk progress
        phase4_output = phase_outputs.get('phase4_chunks')
        if phase4_output:
            if isinstance(phase4_output, dict):
                current_chunk_index = phase4_output.get('current_chunk_index')
                total_chunks = phase4_output.get('total_chunks')
            
            if phase4_output.get('status') == 'success':
                phase4_data = phase4_output.get('output_data', {})
                stitched_url = phase4_data.get('stitched_video_url')
                if stitched_url:
                    stitched_video_url = _get_presigned_url_from_cache(
                        video_id, "stitched_video_url", stitched_url
                    )
    
    # Phase 5: Final video
    final_video_url = None
    # Check metadata for final_video_url (set on completion)
    final_url = metadata.get('final_video_url')
    if final_url:
        final_video_url = _get_presigned_url_from_cache(video_id, "final_video_url", final_url)
    elif phase_outputs:
        phase5_output = phase_outputs.get('phase5_refine')
        if phase5_output and phase5_output.get('status') == 'success':
            phase5_data = phase5_output.get('output_data', {})
            refined_url = phase5_data.get('refined_video_url')
            if refined_url:
                final_video_url = _get_presigned_url_from_cache(
                    video_id, "refined_video_url", refined_url
                )
    
    return StatusResponse(
        video_id=video_id,
        status=status,
        progress=progress,
        current_phase=current_phase,
        estimated_time_remaining=estimated_time_remaining,
        error=error,
        animatic_urls=animatic_urls,
        reference_assets=reference_assets,
        stitched_video_url=stitched_video_url,
        final_video_url=final_video_url,
        current_chunk_index=current_chunk_index,
        total_chunks=total_chunks
    )


def build_status_response_from_db(video: VideoGeneration) -> StatusResponse:
    """Build StatusResponse from DB VideoGeneration model"""
    # Calculate estimated time remaining
    estimated_time_remaining = None
    if video.status.value not in ["complete", "failed"]:
        if video.progress > 0:
            estimated_time_remaining = int((100 - video.progress) / video.progress * 600)  # seconds
    
    # Extract phase outputs
    animatic_urls = None
    reference_assets = None
    stitched_video_url = None
    current_chunk_index = None
    total_chunks = None
    
    if video.phase_outputs:
        # Phase 2: Storyboard images
        phase2_output = video.phase_outputs.get('phase2_storyboard') or video.phase_outputs.get('phase2_animatic')
        if phase2_output and phase2_output.get('status') == 'success':
            phase2_data = phase2_output.get('output_data', {})
            spec = phase2_data.get('spec', {}) or video.spec or {}
            beats = spec.get('beats', [])
            animatic_urls_raw = []
            
            for beat in beats:
                image_url = beat.get('image_url')
                if image_url:
                    animatic_urls_raw.append(image_url)
            
            if not animatic_urls_raw:
                animatic_urls_raw = phase2_data.get('animatic_urls', []) or video.animatic_urls or []
            
            if animatic_urls_raw:
                animatic_urls = []
                for url in animatic_urls_raw:
                    presigned = _get_presigned_url_from_cache(video.id, f"animatic_{len(animatic_urls)}", url)
                    animatic_urls.append(presigned)
        
        # Phase 3: Reference assets
        phase3_output = video.phase_outputs.get('phase3_references')
        if phase3_output and phase3_output.get('status') == 'success':
            reference_assets = phase3_output.get('output_data', {}).copy()
            
            # Convert S3 URLs to presigned URLs
            style_guide_url = reference_assets.get('style_guide_url')
            if style_guide_url:
                reference_assets['style_guide_url'] = _get_presigned_url_from_cache(
                    video.id, "style_guide_url", style_guide_url
                )
            
            product_reference_url = reference_assets.get('product_reference_url')
            if product_reference_url:
                reference_assets['product_reference_url'] = _get_presigned_url_from_cache(
                    video.id, "product_reference_url", product_reference_url
                )
            
            uploaded_assets = reference_assets.get('uploaded_assets')
            if uploaded_assets:
                for i, asset in enumerate(uploaded_assets):
                    s3_url = asset.get('s3_url')
                    if s3_url:
                        asset['s3_url'] = _get_presigned_url_from_cache(
                            video.id, f"uploaded_asset_{i}", s3_url
                        )
        
        # Phase 4: Stitched video and chunk progress
        phase4_output = video.phase_outputs.get('phase4_chunks')
        if phase4_output:
            if isinstance(phase4_output, dict):
                current_chunk_index = phase4_output.get('current_chunk_index')
                total_chunks = phase4_output.get('total_chunks')
            
            if phase4_output.get('status') == 'success':
                phase4_data = phase4_output.get('output_data', {})
                stitched_url = phase4_data.get('stitched_video_url') or video.stitched_url
                if stitched_url:
                    stitched_video_url = _get_presigned_url_from_cache(
                        video.id, "stitched_video_url", stitched_url
                    )
    
    # Phase 5: Final video
    final_video_url = None
    if video.final_video_url:
        final_video_url = _get_presigned_url_from_cache(
            video.id, "final_video_url", video.final_video_url
        )
    elif video.phase_outputs:
        phase5_output = video.phase_outputs.get('phase5_refine')
        if phase5_output and phase5_output.get('status') == 'success':
            phase5_data = phase5_output.get('output_data', {})
            refined_url = phase5_data.get('refined_video_url') or video.refined_url
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
        animatic_urls=animatic_urls,
        reference_assets=reference_assets,
        stitched_video_url=stitched_video_url,
        final_video_url=final_video_url,
        current_chunk_index=current_chunk_index,
        total_chunks=total_chunks
    )

