from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.common.schemas import GenerateRequest, GenerateResponse
from app.common.models import VideoGeneration, VideoStatus, Asset
from app.common.auth import get_current_user
from app.database import get_db
from app.orchestrator.pipeline import run_pipeline
from app.services.redis import RedisClient
import uuid

router = APIRouter()

# Initialize Redis client
redis_client = RedisClient()

@router.post("/api/generate")
async def generate_video(
    request: GenerateRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> GenerateResponse:
    """Submit video generation job"""
    
    # Create video record
    video_id = str(uuid.uuid4())
    
    # Convert asset IDs to asset dictionaries for Phase 1
    # Only include assets that belong to the authenticated user
    asset_dicts = []
    if request.reference_assets:
        for asset_id in request.reference_assets:
            asset = db.query(Asset).filter(
                Asset.id == asset_id,
                Asset.user_id == user_id
            ).first()
            if asset:
                # Create asset dict with s3_key for Phase 1/3 processing
                asset_dicts.append({
                    's3_key': asset.s3_key,
                    'url': None,  # Will use s3_key
                    'asset_id': asset_id
                })
            else:
                # Asset not found or doesn't belong to user - log warning but continue
                print(f"⚠️  Asset ID {asset_id} not found or not accessible, skipping")
    
    # Create database record
    video_record = VideoGeneration(
        id=video_id,
        user_id=user_id,  # Use authenticated user ID
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
    
    # CRITICAL POINT 1: Write to Redis immediately after DB creation
    if redis_client._client:
        try:
            redis_client.set_video_progress(video_id, 0.0)
            redis_client.set_video_status(video_id, VideoStatus.QUEUED.value)
            redis_client.set_video_phase(video_id, "phase1_planning")  # Initial phase (intelligent planning)
            redis_client.set_video_user_id(video_id, user_id)  # Store user_id for access checks
            redis_client.set_video_metadata(video_id, {
                "title": video_record.title,
                "prompt": video_record.prompt,
                "description": video_record.description,
                "total_cost": 0.0,
            })
            print(f"✅ Initialized video {video_id} in Redis")
        except Exception as e:
            print(f"⚠️  Failed to initialize Redis for video {video_id}: {e}")
            # Continue anyway - Redis is optional, DB write succeeded
    
    # Enqueue job
    try:
        # Pass asset dictionaries (with s3_key) and model selection to pipeline for Phase 1
        selected_model = request.model or 'hailuo'  # Default to 'hailuo' if not specified
        run_pipeline.delay(video_id, request.prompt, asset_dicts, selected_model)
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
