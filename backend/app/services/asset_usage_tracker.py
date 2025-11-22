"""
Asset Usage Tracking Service

Tracks when reference assets are used in video generation.
Increments usage_count and updates last_used_at timestamp.
"""
import logging
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session
from app.common.models import Asset
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class AssetUsageTracker:
    """Service for tracking asset usage in video generation"""
    
    def increment_usage(self, asset_ids: List[str], db: Session = None) -> None:
        """
        Increment usage count for assets that were used in video generation.
        
        Args:
            asset_ids: List of asset IDs that were used
            db: Optional database session (creates new one if not provided)
        """
        if not asset_ids:
            logger.info("No assets to track usage for")
            return
        
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            # Update usage count and last_used_at for each asset
            updated_count = 0
            for asset_id in asset_ids:
                asset = db.query(Asset).filter(Asset.id == asset_id).first()
                if asset:
                    # Increment usage count
                    if asset.usage_count is None:
                        asset.usage_count = 1
                    else:
                        asset.usage_count += 1
                    
                    # Update timestamp (triggers updated_at via onupdate)
                    asset.updated_at = datetime.utcnow()
                    
                    updated_count += 1
                    logger.info(
                        f"Incremented usage for asset {asset_id}: "
                        f"count={asset.usage_count}, name={asset.name}"
                    )
                else:
                    logger.warning(f"Asset {asset_id} not found for usage tracking")
            
            db.commit()
            logger.info(f"Updated usage tracking for {updated_count}/{len(asset_ids)} assets")
            
        except Exception as e:
            logger.error(f"Error tracking asset usage: {str(e)}", exc_info=True)
            db.rollback()
            raise
        finally:
            if close_db:
                db.close()
    
    def increment_usage_for_video(self, video_id: str, db: Session = None) -> None:
        """
        Increment usage for all assets referenced in a video.
        
        Fetches referenced_asset_ids from Phase 2 output in database.
        
        Args:
            video_id: Video generation ID
            db: Optional database session
        """
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            from app.common.models import VideoGeneration
            
            # Fetch video record
            video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
            if not video:
                logger.warning(f"Video {video_id} not found for usage tracking")
                return
            
            # Extract referenced_asset_ids from Phase 2 output
            phase_outputs = video.phase_outputs or {}
            phase2_output = phase_outputs.get('phase2_storyboard', {})
            output_data = phase2_output.get('output_data', {})
            referenced_asset_ids = output_data.get('referenced_asset_ids', [])
            
            if not referenced_asset_ids:
                logger.info(f"No referenced assets found for video {video_id}")
                return
            
            logger.info(f"Tracking usage for {len(referenced_asset_ids)} assets in video {video_id}")
            
            # Increment usage for all referenced assets
            self.increment_usage(referenced_asset_ids, db=db)
            
        except Exception as e:
            logger.error(f"Error tracking usage for video {video_id}: {str(e)}", exc_info=True)
            raise
        finally:
            if close_db:
                db.close()


# Singleton instance
asset_usage_tracker = AssetUsageTracker()

