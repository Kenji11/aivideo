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
    
    # Extract reference assets from phase outputs if available
    reference_assets = None
    if video.phase_outputs:
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
    
    return StatusResponse(
        video_id=video.id,
        status=video.status.value,
        progress=video.progress,
        current_phase=video.current_phase,
        estimated_time_remaining=estimated_time_remaining,
        error=video.error_message,
        reference_assets=reference_assets
    )
