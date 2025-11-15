from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import StatusResponse
from app.common.models import VideoGeneration
from app.database import get_db

router = APIRouter()

@router.get("/api/status/{video_id}")
async def get_status(video_id: str, db: Session = Depends(get_db)) -> StatusResponse:
    """Get video generation status"""
    
    video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
    
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
    
    if video.phase_outputs:
        # Look for Phase 2 output (animatic frames)
        phase2_output = video.phase_outputs.get('phase2_animatic')
        if phase2_output and phase2_output.get('status') == 'success':
            animatic_data = phase2_output.get('output_data', {})
            animatic_urls_raw = animatic_data.get('animatic_urls', []) or video.animatic_urls or []
            
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
            if reference_assets.get('style_guide_url', '').startswith('s3://'):
                # Extract key from s3://bucket/key
                s3_path = reference_assets['style_guide_url'].replace(f's3://{s3_client.bucket}/', '')
                reference_assets['style_guide_url'] = s3_client.generate_presigned_url(s3_path, expiration=3600)
            
            if reference_assets.get('product_reference_url', '').startswith('s3://'):
                s3_path = reference_assets['product_reference_url'].replace(f's3://{s3_client.bucket}/', '')
                reference_assets['product_reference_url'] = s3_client.generate_presigned_url(s3_path, expiration=3600)
            
            # Convert uploaded assets S3 URLs
            if reference_assets.get('uploaded_assets'):
                for asset in reference_assets['uploaded_assets']:
                    if asset.get('s3_url', '').startswith('s3://'):
                        s3_path = asset['s3_url'].replace(f's3://{s3_client.bucket}/', '')
                        asset['s3_url'] = s3_client.generate_presigned_url(s3_path, expiration=3600)
        
        # Look for Phase 4 output (stitched video)
        phase4_output = video.phase_outputs.get('phase4_chunks')
        if phase4_output and phase4_output.get('status') == 'success':
            phase4_data = phase4_output.get('output_data', {})
            stitched_url = phase4_data.get('stitched_video_url') or video.stitched_url
            
            if stitched_url and stitched_url.startswith('s3://'):
                # Convert S3 URL to presigned URL
                from app.services.s3 import s3_client
                s3_path = stitched_url.replace(f's3://{s3_client.bucket}/', '')
                stitched_video_url = s3_client.generate_presigned_url(s3_path, expiration=3600)
            elif stitched_url:
                stitched_video_url = stitched_url
    
    return StatusResponse(
        video_id=video.id,
        status=video.status.value,
        progress=video.progress,
        current_phase=video.current_phase,
        estimated_time_remaining=estimated_time_remaining,
        error=video.error_message,
        animatic_urls=animatic_urls,
        reference_assets=reference_assets,
        stitched_video_url=stitched_video_url
    )
