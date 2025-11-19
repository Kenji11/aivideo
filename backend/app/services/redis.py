# Redis client wrapper for video progress tracking
import redis
import json
import logging
from typing import Optional, Dict, Any
from app.config import get_settings

logger = logging.getLogger(__name__)

# Redis TTL: 60 minutes (3600 seconds)
REDIS_TTL = 3600


class RedisClient:
    """Singleton Redis client for video progress tracking"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            try:
                settings = get_settings()
                self._client = redis.from_url(settings.redis_url, decode_responses=True)
                # Test connection
                self._client.ping()
                logger.info("Redis client connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                self._client = None
    
    def _key(self, video_id: str, field: str) -> str:
        """Generate Redis key for video field"""
        return f"video:{video_id}:{field}"
    
    def set_video_progress(self, video_id: str, progress: float) -> bool:
        """Set video progress (0-100)"""
        if not self._client:
            return False
        try:
            self._client.set(self._key(video_id, "progress"), str(progress), ex=REDIS_TTL)
            return True
        except Exception as e:
            logger.warning(f"Failed to set video progress in Redis: {e}")
            return False
    
    def set_video_status(self, video_id: str, status: str) -> bool:
        """Set video status string"""
        if not self._client:
            return False
        try:
            self._client.set(self._key(video_id, "status"), status, ex=REDIS_TTL)
            return True
        except Exception as e:
            logger.warning(f"Failed to set video status in Redis: {e}")
            return False
    
    def set_video_phase(self, video_id: str, phase: str) -> bool:
        """Set current phase"""
        if not self._client:
            return False
        try:
            self._client.set(self._key(video_id, "current_phase"), phase, ex=REDIS_TTL)
            return True
        except Exception as e:
            logger.warning(f"Failed to set video phase in Redis: {e}")
            return False
    
    def set_video_metadata(self, video_id: str, metadata: Dict[str, Any]) -> bool:
        """Set video metadata (title, description, prompt, user_id, etc.)"""
        if not self._client:
            return False
        try:
            self._client.set(
                self._key(video_id, "metadata"),
                json.dumps(metadata),
                ex=REDIS_TTL
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set video metadata in Redis: {e}")
            return False
    
    def set_video_user_id(self, video_id: str, user_id: str) -> bool:
        """Set video user_id (for access checks)"""
        if not self._client:
            return False
        try:
            self._client.set(
                self._key(video_id, "user_id"),
                user_id,
                ex=REDIS_TTL
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set video user_id in Redis: {e}")
            return False
    
    def set_video_phase_outputs(self, video_id: str, phase_outputs: Dict[str, Any]) -> bool:
        """Set phase outputs (nested JSON structure, same as DB)"""
        if not self._client:
            return False
        try:
            self._client.set(
                self._key(video_id, "phase_outputs"),
                json.dumps(phase_outputs),
                ex=REDIS_TTL
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set video phase outputs in Redis: {e}")
            return False
    
    def set_video_spec(self, video_id: str, spec: Dict[str, Any]) -> bool:
        """Set video spec"""
        if not self._client:
            return False
        try:
            self._client.set(
                self._key(video_id, "spec"),
                json.dumps(spec),
                ex=REDIS_TTL
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set video spec in Redis: {e}")
            return False
    
    def set_video_presigned_urls(self, video_id: str, urls: Dict[str, str]) -> bool:
        """Cache presigned URLs for S3 assets"""
        if not self._client:
            return False
        try:
            self._client.set(
                self._key(video_id, "presigned_urls"),
                json.dumps(urls),
                ex=REDIS_TTL
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set presigned URLs in Redis: {e}")
            return False
    
    def set_video_storyboard_urls(self, video_id: str, urls: list) -> bool:
        """Set storyboard image URLs (from Phase 2)"""
        if not self._client:
            return False
        try:
            self._client.set(
                self._key(video_id, "storyboard_urls"),
                json.dumps(urls),
                ex=REDIS_TTL
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to set storyboard URLs in Redis: {e}")
            return False
    
    def get_video_data(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get all video data as dict"""
        if not self._client:
            return None
        try:
            data = {}
            
            # Get all fields
            progress = self._client.get(self._key(video_id, "progress"))
            status = self._client.get(self._key(video_id, "status"))
            current_phase = self._client.get(self._key(video_id, "current_phase"))
            error_message = self._client.get(self._key(video_id, "error_message"))
            user_id = self._client.get(self._key(video_id, "user_id"))
            metadata_str = self._client.get(self._key(video_id, "metadata"))
            phase_outputs_str = self._client.get(self._key(video_id, "phase_outputs"))
            spec_str = self._client.get(self._key(video_id, "spec"))
            presigned_urls_str = self._client.get(self._key(video_id, "presigned_urls"))
            storyboard_urls_str = self._client.get(self._key(video_id, "storyboard_urls"))
            
            # Parse and add to data dict
            if progress is not None:
                data["progress"] = float(progress)
            if status is not None:
                data["status"] = status
            if current_phase is not None:
                data["current_phase"] = current_phase
            if error_message is not None:
                data["error_message"] = error_message
            if user_id is not None:
                data["user_id"] = user_id
            if metadata_str:
                try:
                    data["metadata"] = json.loads(metadata_str)
                except json.JSONDecodeError:
                    pass
            if phase_outputs_str:
                try:
                    data["phase_outputs"] = json.loads(phase_outputs_str)
                except json.JSONDecodeError:
                    pass
            if spec_str:
                try:
                    data["spec"] = json.loads(spec_str)
                except json.JSONDecodeError:
                    pass
            if presigned_urls_str:
                try:
                    data["presigned_urls"] = json.loads(presigned_urls_str)
                except json.JSONDecodeError:
                    pass
            if storyboard_urls_str:
                try:
                    data["storyboard_urls"] = json.loads(storyboard_urls_str)
                except json.JSONDecodeError:
                    pass
            
            # Add video_id
            data["video_id"] = video_id
            
            # Return None if no data found
            if not data or len(data) == 1:  # Only video_id
                return None
            
            return data
        except Exception as e:
            logger.warning(f"Failed to get video data from Redis: {e}")
            return None
    
    def delete_video_data(self, video_id: str) -> bool:
        """Delete all keys for video (cleanup)"""
        if not self._client:
            return False
        try:
            keys = [
                self._key(video_id, "progress"),
                self._key(video_id, "status"),
                self._key(video_id, "current_phase"),
                self._key(video_id, "error_message"),
                self._key(video_id, "user_id"),
                self._key(video_id, "metadata"),
                self._key(video_id, "phase_outputs"),
                self._key(video_id, "spec"),
                self._key(video_id, "presigned_urls"),
                self._key(video_id, "storyboard_urls"),
            ]
            self._client.delete(*keys)
            return True
        except Exception as e:
            logger.warning(f"Failed to delete video data from Redis: {e}")
            return False

