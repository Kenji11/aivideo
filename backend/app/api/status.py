from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import StatusResponse
from app.common.models import VideoGeneration
from app.common.auth import get_current_user
from app.database import get_db

router = APIRouter()

@router.get("/api/status/{video_id}")
async def get_status(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StatusResponse:
    """Get video generation status"""
    
    # Only allow access to videos owned by the authenticated user
    video = db.query(VideoGeneration).filter(
        VideoGeneration.id == video_id,
        VideoGeneration.user_id == user_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Calculate estimated time remaining (rough estimate)
    estimated_time_remaining = None
    if video.status.value not in ["complete", "failed"]:
        # Rough estimate: 10 minutes total, based on progress
        if video.progress > 0:
            estimated_time_remaining = int((100 - video.progress) / video.progress * 600)  # seconds
    
    # Extract phase outputs if available
    animatic_urls = None
    reference_assets = None
    stitched_video_url = None
    current_chunk_index = None  # Current chunk being processed in Phase 4
    total_chunks = None  # Total number of chunks in Phase 4
    
    if video.phase_outputs:
        # Look for Phase 2 output (storyboard images)
        # Check both phase2_storyboard (new) and phase2_animatic (legacy) for backward compatibility
        phase2_output = video.phase_outputs.get('phase2_storyboard') or video.phase_outputs.get('phase2_animatic')
        if phase2_output and phase2_output.get('status') == 'success':
            phase2_data = phase2_output.get('output_data', {})
            
            # Extract storyboard image URLs from beats (new Phase 2 structure)
            spec = phase2_data.get('spec', {})
            beats = spec.get('beats', [])
            animatic_urls_raw = []
            
            # Extract image_url from each beat (storyboard images)
            for beat in beats:
                image_url = beat.get('image_url')
                if image_url:
                    animatic_urls_raw.append(image_url)
            
            # Fallback to old animatic_urls format if no beats found (backward compatibility)
            if not animatic_urls_raw:
                animatic_urls_raw = phase2_data.get('animatic_urls', []) or video.animatic_urls or []
            
            # Convert S3 URLs to presigned URLs for frontend access
            if animatic_urls_raw:
                from app.services.s3 import s3_client
                animatic_urls = []
                for url in animatic_urls_raw:
                    if url.startswith('s3://'):
                        s3_path = url.replace(f's3://{s3_client.bucket}/', '')
                        presigned_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
                        animatic_urls.append(presigned_url)
                    else:
                        animatic_urls.append(url)
        
        # Look for Phase 3 output
        phase3_output = video.phase_outputs.get('phase3_references')
        if phase3_output and phase3_output.get('status') == 'success':
            reference_assets = phase3_output.get('output_data', {}).copy()
            
            # Convert S3 URLs to presigned URLs for frontend access
            from app.services.s3 import s3_client
            
            # Convert style_guide_url if it exists and is an S3 URL
            style_guide_url = reference_assets.get('style_guide_url')
            if style_guide_url and style_guide_url.startswith('s3://'):
                # Extract key from s3://bucket/key
                s3_path = style_guide_url.replace(f's3://{s3_client.bucket}/', '')
                reference_assets['style_guide_url'] = s3_client.generate_presigned_url(s3_path, expiration=3600)
            
            # Convert product_reference_url if it exists and is an S3 URL
            product_reference_url = reference_assets.get('product_reference_url')
            if product_reference_url and product_reference_url.startswith('s3://'):
                s3_path = product_reference_url.replace(f's3://{s3_client.bucket}/', '')
                reference_assets['product_reference_url'] = s3_client.generate_presigned_url(s3_path, expiration=3600)
            
            # Convert uploaded assets S3 URLs
            uploaded_assets = reference_assets.get('uploaded_assets')
            if uploaded_assets:
                for asset in uploaded_assets:
                    s3_url = asset.get('s3_url')
                    if s3_url and s3_url.startswith('s3://'):
                        s3_path = s3_url.replace(f's3://{s3_client.bucket}/', '')
                        asset['s3_url'] = s3_client.generate_presigned_url(s3_path, expiration=3600)
        
        # Look for Phase 4 output (stitched video) and current chunk progress
        phase4_output = video.phase_outputs.get('phase4_chunks')
        if phase4_output:
            # Extract current chunk info if Phase 4 is in progress
            if isinstance(phase4_output, dict):
                current_chunk_index = phase4_output.get('current_chunk_index')
                total_chunks = phase4_output.get('total_chunks')
                if current_chunk_index is not None:
                    current_chunk_index = current_chunk_index
                    total_chunks = total_chunks
            
            # Extract stitched video if Phase 4 completed
            if phase4_output.get('status') == 'success':
                phase4_data = phase4_output.get('output_data', {})
                stitched_url = phase4_data.get('stitched_video_url') or video.stitched_url
                
                if stitched_url and stitched_url.startswith('s3://'):
                    # Convert S3 URL to presigned URL
                    from app.services.s3 import s3_client
                    s3_path = stitched_url.replace(f's3://{s3_client.bucket}/', '')
                    stitched_video_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
                elif stitched_url:
                    stitched_video_url = stitched_url
    
    # Look for Phase 5 output (final video with audio)
    final_video_url = None
    if video.final_video_url:
        # Phase 5 completed - use final_video_url (with audio)
        final_url = video.final_video_url
        if final_url.startswith('s3://'):
            # Convert S3 URL to presigned URL
            from app.services.s3 import s3_client
            s3_path = final_url.replace(f's3://{s3_client.bucket}/', '')
            final_video_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
        else:
            final_video_url = final_url
    elif video.phase_outputs:
        # Check Phase 5 output if final_video_url not set yet
        phase5_output = video.phase_outputs.get('phase5_refine')
        if phase5_output and phase5_output.get('status') == 'success':
            phase5_data = phase5_output.get('output_data', {})
            refined_url = phase5_data.get('refined_video_url') or video.refined_url
            if refined_url:
                if refined_url.startswith('s3://'):
                    from app.services.s3 import s3_client
                    s3_path = refined_url.replace(f's3://{s3_client.bucket}/', '')
                    final_video_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
                else:
                    final_video_url = refined_url
    
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
