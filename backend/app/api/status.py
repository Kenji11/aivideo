from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json
import logging
from app.common.schemas import StatusResponse
from app.common.models import VideoGeneration
from app.common.auth import get_current_user
from app.database import get_db
from app.services.redis import RedisClient
from app.services.status_builder import (
    build_status_response_from_redis_video_data,
    build_status_response_from_db
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Redis client
redis_client = RedisClient()


def _re_add_to_redis(video: VideoGeneration):
    """Re-add video data to Redis if DB entry exists but Redis doesn't"""
    if not redis_client._client:
        return
    
    try:
        # Build metadata
        metadata = {
            "title": video.title,
            "prompt": video.prompt,
            "description": video.description,
            "total_cost": video.cost_usd,
            "generation_time": video.generation_time_seconds,
        }
        if video.final_video_url:
            metadata["final_video_url"] = video.final_video_url
        
        # Set basic fields
        redis_client.set_video_progress(video.id, video.progress)
        redis_client.set_video_status(video.id, video.status.value)
        redis_client.set_video_user_id(video.id, video.user_id)  # Store user_id for access checks
        if video.current_phase:
            redis_client.set_video_phase(video.id, video.current_phase)
        if video.error_message:
            redis_client._client.set(
                redis_client._key(video.id, "error_message"),
                video.error_message,
                ex=3600
            )
        
        # Set metadata
        redis_client.set_video_metadata(video.id, metadata)
        
        # Set phase outputs
        if video.phase_outputs:
            redis_client.set_video_phase_outputs(video.id, video.phase_outputs)
        
        # Set spec (if exists)
        if video.spec:
            redis_client.set_video_spec(video.id, video.spec)
        
        logger.info(f"Re-added video {video.id} to Redis")
    except Exception as e:
        logger.warning(f"Failed to re-add video to Redis: {e}")


@router.get("/api/status/{video_id}")
async def get_status(
    video_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StatusResponse:
    """Get video generation status (checks Redis first, falls back to DB)"""
    
    # Try Redis first
    redis_data = None
    if redis_client._client:
        try:
            redis_data = redis_client.get_video_data(video_id)
            # Verify user access from Redis
            if redis_data and redis_data.get("user_id") != user_id:
                raise HTTPException(status_code=404, detail="Video not found")
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Redis read failed, using DB: {e}")
    
    if redis_data:
        # Build response from Redis data
        return build_status_response_from_redis_video_data(redis_data)
    
    # Fallback to DB
    video = db.query(VideoGeneration).filter(
        VideoGeneration.id == video_id,
        VideoGeneration.user_id == user_id
    ).first()
    
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    # Re-add to Redis if DB entry found but Redis missing
    if redis_client._client:
        _re_add_to_redis(video)
    
    # Build response from DB
    return build_status_response_from_db(video)


@router.get("/api/status/{video_id}/stream")
async def stream_status(
    video_id: str,
    token: str = Query(..., description="Auth token as query parameter (required for SSE - EventSource doesn't support headers)"),
    db: Session = Depends(get_db)
):
    """Server-Sent Events stream for real-time status updates (polling-based)
    
    Note: EventSource doesn't support custom headers, so token must be passed as query parameter.
    All requests to this endpoint are assumed to be SSE streaming requests.
    """
    from app.services.firebase_auth import get_user_id_from_token
    
    # Authenticate using token from query parameter (required for SSE)
    try:
        user_id = get_user_id_from_token(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
    # Check Redis first for access verification
    redis_data = None
    if redis_client._client:
        try:
            redis_data = redis_client.get_video_data(video_id)
            # Verify user access from Redis
            if redis_data and redis_data.get("user_id") != user_id:
                raise HTTPException(status_code=404, detail="Video not found")
        except HTTPException:
            raise
        except Exception:
            pass
    
    # Fallback to DB for access verification if Redis missing
    if not redis_data:
        video = db.query(VideoGeneration).filter(
            VideoGeneration.id == video_id,
            VideoGeneration.user_id == user_id
        ).first()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Re-add to Redis
        if redis_client._client:
            _re_add_to_redis(video)
    
    async def event_generator():
        last_data = None
        while True:
            try:
                # Check Redis first
                redis_data = None
                if redis_client._client:
                    try:
                        redis_data = redis_client.get_video_data(video_id)
                    except Exception:
                        pass
                
                # Fallback to DB if Redis missing
                if not redis_data:
                    video = db.query(VideoGeneration).filter(
                        VideoGeneration.id == video_id,
                        VideoGeneration.user_id == user_id
                    ).first()
                    
                    if not video:
                        yield f"event: error\ndata: {json.dumps({'error': 'Video not found'})}\n\n"
                        break
                    
                    # Re-add to Redis
                    if redis_client._client:
                        _re_add_to_redis(video)
                    
                    # Build response from DB
                    status_response = build_status_response_from_db(video)
                else:
                    # Build response from Redis
                    status_response = build_status_response_from_redis_video_data(redis_data)
                
                # Only send event if data changed
                current_data = status_response.dict()
                if current_data != last_data:
                    yield f"data: {json.dumps(current_data)}\n\n"
                    last_data = current_data
                
                # Check if complete or failed (stop streaming)
                if status_response.status in ['complete', 'failed']:
                    yield "event: close\ndata: {}\n\n"
                    break
                
                # Poll every 1.5 seconds
                await asyncio.sleep(1.5)
                
            except Exception as e:
                logger.error(f"Error in SSE stream: {e}")
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
