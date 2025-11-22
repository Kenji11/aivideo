"""
Asset Search API Endpoints

Provides semantic search, visual similarity, duplicate detection, and style recommendations.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from PIL import Image
import logging

from app.database import get_db
from app.common.models import Asset, AssetSource, ReferenceAssetType
from app.common.auth import get_current_user
from app.services.asset_search import asset_search_service
from app.services.clip_embeddings import clip_service
from app.services.s3 import s3_client

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/assets")
async def get_assets(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    reference_asset_type: Optional[str] = Query(None, description="Filter by reference asset type"),
    is_logo: Optional[bool] = Query(None, description="Filter by logo flag"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Number of results per page"),
    offset: Optional[int] = Query(0, ge=0, description="Offset for pagination")
):
    """
    Get all assets for the authenticated user.
    
    Supports filtering by reference_asset_type and is_logo, with pagination.
    Returns list of assets with metadata including presigned URLs for access.
    """
    # Query assets for the authenticated user only
    # Use .name to get "USER_UPLOAD" for database enum compatibility
    query = db.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.source == AssetSource.USER_UPLOAD.name
    )
    
    # Apply filters
    if reference_asset_type:
        try:
            ref_type = ReferenceAssetType(reference_asset_type.lower())
            query = query.filter(Asset.reference_asset_type == ref_type)
        except ValueError:
            pass  # Invalid type, ignore filter
    
    if is_logo is not None:
        query = query.filter(Asset.is_logo == is_logo)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination and ordering
    assets = query.order_by(Asset.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    asset_list = []
    for asset in assets:
        # Generate fresh presigned URL (7 days expiration)
        presigned_url = s3_client.generate_presigned_url(asset.s3_key, expiration=3600 * 24 * 7)
        
        asset_list.append({
            "asset_id": asset.id,
            "filename": asset.file_name or "unknown",
            "name": asset.name or asset.file_name or "unknown",
            "asset_type": asset.asset_type.value,
            "reference_asset_type": asset.reference_asset_type,
            "file_size_bytes": asset.file_size_bytes or 0,
            "s3_url": presigned_url,
            "thumbnail_url": asset.thumbnail_url,
            "width": asset.width,
            "height": asset.height,
            "is_logo": asset.is_logo,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        })
    
    return {
        "assets": asset_list,
        "total": total,
        "limit": limit,
        "offset": offset,
        "user_id": user_id
    }


@router.get("/api/assets/search")
async def search_assets(
    q: str = Query(..., description="Search query"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type (product/logo/person/etc)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search assets by text query using semantic similarity.
    
    Returns assets ranked by similarity to the query, with similarity scores.
    """
    try:
        # Parse asset_type if provided
        parsed_asset_type = None
        if asset_type:
            try:
                parsed_asset_type = ReferenceAssetType(asset_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid asset_type: {asset_type}. Must be one of: {[e.value for e in ReferenceAssetType]}"
                )
        
        # Search assets
        assets = asset_search_service.search_assets_by_text(
            db=db,
            user_id=user_id,
            query=q,
            asset_type=parsed_asset_type,
            limit=limit
        )
        
        # Convert to response format
        asset_list = []
        for asset in assets:
            # Generate fresh presigned URL
            presigned_url = s3_client.generate_presigned_url(asset.s3_key, expiration=3600 * 24 * 7)
            
            asset_list.append({
                "asset_id": asset.id,
                "filename": asset.file_name or "unknown",
                "name": asset.name or asset.file_name or "unknown",
                "asset_type": asset.asset_type.value,
                "reference_asset_type": asset.reference_asset_type,
                "file_size_bytes": asset.file_size_bytes or 0,
                "s3_url": presigned_url,
                "thumbnail_url": asset.thumbnail_url,
                "width": asset.width,
                "height": asset.height,
                "is_logo": asset.is_logo,
                "primary_object": asset.primary_object,
                "similarity_score": getattr(asset, 'similarity_score', None),
                "created_at": asset.created_at.isoformat() if asset.created_at else None,
            })
        
        # Always return 200, even if no results
        return {
            "assets": asset_list,
            "total": len(asset_list),
            "query": q
        }
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/api/assets/{asset_id}/similar")
async def get_similar_assets(
    asset_id: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    exclude_self: bool = Query(True, description="Exclude the reference asset from results"),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Find visually similar assets to a given asset.
    
    Returns assets ranked by visual similarity, with similarity scores.
    """
    try:
        # Verify asset ownership
        asset = db.query(Asset).filter(
            Asset.id == asset_id,
            Asset.user_id == user_id
        ).first()
        
        # If asset not found, return empty results (200) instead of 404
        if not asset:
            return {
                "assets": [],
                "total": 0,
                "reference_asset_id": asset_id
            }
        
        # Find similar assets
        similar_assets = asset_search_service.find_similar_assets(
            db=db,
            reference_asset_id=asset_id,
            limit=limit,
            exclude_self=exclude_self
        )
        
        # Convert to response format
        asset_list = []
        for similar_asset in similar_assets:
            presigned_url = s3_client.generate_presigned_url(similar_asset.s3_key, expiration=3600 * 24 * 7)
            
            asset_list.append({
                "asset_id": similar_asset.id,
                "filename": similar_asset.file_name or "unknown",
                "name": similar_asset.name or similar_asset.file_name or "unknown",
                "asset_type": similar_asset.asset_type.value,
                "reference_asset_type": similar_asset.reference_asset_type,
                "s3_url": presigned_url,
                "thumbnail_url": similar_asset.thumbnail_url,
                "width": similar_asset.width,
                "height": similar_asset.height,
                "is_logo": similar_asset.is_logo,
                "primary_object": similar_asset.primary_object,
                "similarity_score": getattr(similar_asset, 'similarity_score', None),
                "created_at": similar_asset.created_at.isoformat() if similar_asset.created_at else None,
            })
        
        # Always return 200, even if no similar assets found
        return {
            "assets": asset_list,
            "total": len(asset_list),
            "reference_asset_id": asset_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in similar assets endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to find similar assets: {str(e)}")


@router.post("/api/assets/check-duplicate")
async def check_duplicate(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if an uploaded image is a duplicate of existing assets.
    
    Returns potential duplicates with similarity scores.
    """
    try:
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Load image
        from io import BytesIO
        image = Image.open(BytesIO(file_content))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Generate embedding
        embedding = clip_service.generate_image_embedding(image)
        
        # Check for duplicates
        duplicates = asset_search_service.check_duplicate_asset(
            db=db,
            user_id=user_id,
            new_image_embedding=embedding,
            similarity_threshold=0.95
        )
        
        # Convert to response format
        duplicate_list = []
        for duplicate in duplicates:
            presigned_url = s3_client.generate_presigned_url(duplicate.s3_key, expiration=3600 * 24 * 7)
            
            duplicate_list.append({
                "asset_id": duplicate.id,
                "filename": duplicate.file_name or "unknown",
                "name": duplicate.name or duplicate.file_name or "unknown",
                "s3_url": presigned_url,
                "thumbnail_url": duplicate.thumbnail_url,
                "similarity_score": getattr(duplicate, 'similarity_score', None),
            })
        
        return {
            "duplicates": duplicate_list,
            "is_duplicate": len(duplicate_list) > 0,
            "count": len(duplicate_list)
        }
        
    except Exception as e:
        logger.error(f"Error in duplicate check endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Duplicate check failed: {str(e)}")


@router.post("/api/assets/recommend")
async def recommend_assets(
    request: dict = Body(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recommend assets that match the style of already-selected assets.
    
    Request body: {"selected_asset_ids": ["id1", "id2", ...]}
    """
    try:
        selected_asset_ids = request.get("selected_asset_ids", [])
        
        if not selected_asset_ids or not isinstance(selected_asset_ids, list):
            raise HTTPException(
                status_code=400,
                detail="selected_asset_ids must be a non-empty list"
            )
        
        limit = request.get("limit", 10)
        if limit > 50:
            limit = 50
        
        # Get recommendations
        recommendations = asset_search_service.recommend_style_consistent_assets(
            db=db,
            user_id=user_id,
            selected_asset_ids=selected_asset_ids,
            limit=limit
        )
        
        # Convert to response format
        asset_list = []
        for asset in recommendations:
            presigned_url = s3_client.generate_presigned_url(asset.s3_key, expiration=3600 * 24 * 7)
            
            asset_list.append({
                "asset_id": asset.id,
                "filename": asset.file_name or "unknown",
                "name": asset.name or asset.file_name or "unknown",
                "asset_type": asset.asset_type.value,
                "reference_asset_type": asset.reference_asset_type,
                "s3_url": presigned_url,
                "thumbnail_url": asset.thumbnail_url,
                "width": asset.width,
                "height": asset.height,
                "is_logo": asset.is_logo,
                "primary_object": asset.primary_object,
                "similarity_score": getattr(asset, 'similarity_score', None),
                "created_at": asset.created_at.isoformat() if asset.created_at else None,
            })
        
        # Always return 200, even if no recommendations
        return {
            "assets": asset_list,
            "total": len(asset_list),
            "selected_asset_ids": selected_asset_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in recommend endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Recommendation failed: {str(e)}")

