from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import GenerateRequest, GenerateResponse
from app.common.models import VideoGeneration, VideoStatus, Asset
from app.common.constants import MOCK_USER_ID
from app.database import get_db
from app.orchestrator.pipeline import run_pipeline
import uuid

router = APIRouter()

@router.post("/api/generate")
async def generate_video(request: GenerateRequest, db: Session = Depends(get_db)) -> GenerateResponse:
    """Submit video generation job"""
    
    # Create video record
    video_id = str(uuid.uuid4())
    
    # Convert asset IDs to asset dictionaries for Phase 1
    asset_dicts = []
    if request.reference_assets:
        for asset_id in request.reference_assets:
            asset = db.query(Asset).filter(Asset.id == asset_id).first()
            if asset:
                # Create asset dict with s3_key for Phase 1/3 processing
                asset_dicts.append({
                    's3_key': asset.s3_key,
                    'url': None,  # Will use s3_key
                    'asset_id': asset_id
                })
            else:
                # Asset not found - log warning but continue
                print(f"⚠️  Asset ID {asset_id} not found in database, skipping")
    
    # Create database record
    video_record = VideoGeneration(
        id=video_id,
        user_id=MOCK_USER_ID,  # TODO: Get from auth token in future
        title=request.title or "Untitled Video",  # Default title if not provided
        description=request.description,
        prompt=request.prompt,
        reference_assets=request.reference_assets,  # Store asset IDs
        status=VideoStatus.QUEUED,
        progress=0.0
    )
    
    db.add(video_record)
    db.commit()
    db.refresh(video_record)
    
    # Enqueue job
    try:
        # Pass asset dictionaries (with s3_key) to pipeline for Phase 1
        run_pipeline.delay(video_id, request.prompt, asset_dicts)
    except Exception as e:
        # If enqueue fails, update status
        video_record.status = VideoStatus.FAILED
        video_record.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to enqueue job: {str(e)}")
    
    return GenerateResponse(
        video_id=video_id,
        status="queued",
        message="Video generation started"
    )
