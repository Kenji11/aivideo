from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Form, Query, BackgroundTasks
import logging

logger = logging.getLogger(__name__)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import uuid
import tempfile
import os
from pathlib import Path
import mimetypes
from PIL import Image

from app.database import get_db, SessionLocal
from app.common.models import Asset, AssetType, AssetSource, ReferenceAssetType
from app.common.auth import get_current_user
from app.common.schemas import UploadedAsset, UploadResponse
from app.services.s3 import s3_client
from app.common.constants import get_asset_s3_key
from app.services.asset_analysis import asset_analysis_service
from app.services.clip_embeddings import clip_service

router = APIRouter()

# Allowed MIME types
ALLOWED_IMAGE_TYPES = {
    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
    'image/webp', 'image/bmp', 'image/svg+xml'
}
ALLOWED_VIDEO_TYPES = {
    'video/mp4', 'video/mpeg', 'video/quicktime', 'video/x-msvideo',
    'video/x-ms-wmv', 'video/webm', 'video/ogg'
}
ALLOWED_AUDIO_TYPES = {
    'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg',
    'audio/webm', 'audio/aac', 'audio/flac'
}
ALLOWED_DOCUMENT_TYPES = {
    'application/pdf'
}

ALL_ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_VIDEO_TYPES | ALLOWED_AUDIO_TYPES | ALLOWED_DOCUMENT_TYPES

# Max file size: 100MB (general), 10MB for images (reference assets)
MAX_FILE_SIZE = 100 * 1024 * 1024
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB for reference asset images


def determine_asset_type(mime_type: str) -> AssetType:
    """Determine asset type from MIME type"""
    if mime_type in ALLOWED_IMAGE_TYPES:
        return AssetType.IMAGE
    elif mime_type in ALLOWED_VIDEO_TYPES:
        return AssetType.VIDEO
    elif mime_type in ALLOWED_AUDIO_TYPES:
        return AssetType.AUDIO
    else:
        # Default to IMAGE for PDFs and unknown types (will be handled as reference)
        return AssetType.IMAGE


def analyze_asset_background(
    asset_id: str,
    s3_url: str,
    image_path: str,
    user_provided_name: Optional[str],
    user_provided_description: Optional[str]
):
    """
    Background task to analyze asset with GPT-4o and generate CLIP embedding.
    
    This runs after the upload endpoint returns success to the user.
    """
    db = SessionLocal()
    try:
        # Get asset record
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            logger.error(f"Asset {asset_id} not found for analysis")
            return
        
        # Generate presigned URL for GPT-4o (valid for 1 hour)
        from app.services.s3 import s3_client
        presigned_url = s3_client.generate_presigned_url(asset.s3_key, expiration=3600)
        
        # Step 1: GPT-4o Analysis
        try:
            logger.info(f"Starting GPT-4o analysis for asset {asset_id}")
            analysis_result = asset_analysis_service.analyze_reference_asset(
                image_url=presigned_url,
                user_provided_name=user_provided_name,
                user_provided_description=user_provided_description
            )
            
            # Log the full analysis result for debugging
            logger.info(f"GPT-4o analysis result for asset {asset_id}: {analysis_result}")
            logger.info(f"asset_type from analysis: {analysis_result.get('asset_type')} (type: {type(analysis_result.get('asset_type'))})")
            
            # Extract fields from analysis
            asset.analysis = analysis_result
            asset.primary_object = analysis_result.get("primary_object")
            asset.colors = analysis_result.get("colors", [])
            asset.dominant_colors_rgb = analysis_result.get("dominant_colors_rgb", [])
            asset.style_tags = analysis_result.get("style_tags", [])
            asset.recommended_shot_types = analysis_result.get("recommended_shot_types", [])
            asset.usage_contexts = analysis_result.get("usage_contexts", [])
            asset.is_logo = analysis_result.get("is_logo", False)
            asset.logo_position_preference = analysis_result.get("logo_position_preference")
            
            # Update reference_asset_type if not already set
            if not asset.reference_asset_type and analysis_result.get("asset_type"):
                asset_type_str = analysis_result["asset_type"].lower().strip()
                # Validate it's a valid enum value
                valid_values = {e.value for e in ReferenceAssetType}
                if asset_type_str in valid_values:
                    asset.reference_asset_type = asset_type_str
                else:
                    logger.warning(f"Invalid asset_type from GPT-4o: '{analysis_result.get('asset_type')}' (normalized: '{asset_type_str}')")
            
            logger.info(f"✓ GPT-4o analysis complete for asset {asset_id}")
            
            # Step 2: CLIP Embedding (only if GPT-4o succeeded)
            try:
                # Load image from file path
                with Image.open(image_path) as img:
                    # Convert to RGB if needed (CLIP expects RGB)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    logger.info(f"Generating CLIP embedding for asset {asset_id}")
                    embedding = clip_service.generate_image_embedding(img)
                    
                    # Store embedding (pgvector format)
                    # Use raw SQL to set embedding since it's a pgvector type
                    # Format: '[0.1, 0.2, ...]' as string for pgvector
                    embedding_str = '[' + ','.join(str(f) for f in embedding) + ']'
                    db.execute(
                        text("UPDATE assets SET embedding = CAST(:embedding AS vector) WHERE id = :asset_id"),
                        {"embedding": embedding_str, "asset_id": asset_id}
                    )
                    
                    logger.info(f"✓ CLIP embedding generated for asset {asset_id}")
            except Exception as e:
                logger.error(f"Failed to generate CLIP embedding for asset {asset_id}: {str(e)}", exc_info=True)
                # Continue without embedding - asset still has GPT-4o analysis
            
            db.commit()
            logger.info(f"✓ Asset {asset_id} analysis complete and saved")
            
        except Exception as e:
            logger.error(f"GPT-4o analysis failed for asset {asset_id}: {str(e)}", exc_info=True)
            # Asset remains in database with basic metadata (no analysis)
            db.rollback()
        
    finally:
        db.close()
        # Clean up temporary image file
        if os.path.exists(image_path):
            try:
                os.unlink(image_path)
            except Exception as e:
                logger.warning(f"Failed to delete temp file {image_path}: {str(e)}")


@router.post("/api/upload")
async def upload_assets(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    # Optional form fields for reference assets
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    reference_asset_type: Optional[str] = Form(None)
):
    """
    Upload one or more assets (images, videos, PDFs) to S3 and create database records.
    
    For reference assets (images), accepts optional metadata:
    - name: User-defined name (defaults to filename)
    - description: Optional description
    - reference_asset_type: product, logo, person, environment, texture, prop
    
    Returns list of asset IDs that can be used as reference_assets in video generation.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    uploaded_assets = []
    errors = []
    
    for file in files:
        try:
            # Validate file size
            file_content = await file.read()
            file_size = len(file_content)
            
            # Validate MIME type
            mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
            
            # Check if it's an image (reference asset)
            is_image = mime_type in ALLOWED_IMAGE_TYPES
            
            # Apply size limit based on file type
            max_size = MAX_IMAGE_SIZE if is_image else MAX_FILE_SIZE
            if file_size > max_size:
                errors.append(f"{file.filename}: File too large (max {max_size / (1024*1024)}MB)")
                continue
            
            if file_size == 0:
                errors.append(f"{file.filename}: File is empty")
                continue
            
            if mime_type not in ALL_ALLOWED_TYPES:
                errors.append(f"{file.filename}: File type not allowed. Allowed: images, videos, PDFs")
                continue
            
            # Determine asset type
            asset_type = determine_asset_type(mime_type)
            
            # Generate unique asset ID
            asset_id = str(uuid.uuid4())
            
            # Get filename and sanitize
            filename = file.filename or f"file_{asset_id}"
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ").strip()
            if not safe_filename:
                safe_filename = f"file_{asset_id}"
            
            # Create S3 key: {user_id}/assets/{filename} (new flat structure)
            s3_key = get_asset_s3_key(user_id, safe_filename)
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name
            
            try:
                # Extract image properties if it's an image
                width = None
                height = None
                has_transparency = False
                thumbnail_url = None
                
                # Keep image in memory for CLIP embedding (if it's an image)
                image_for_analysis = None
                if is_image:
                    try:
                        with Image.open(temp_path) as img:
                            width, height = img.size
                            # Check for transparency (alpha channel)
                            has_transparency = img.mode in ('RGBA', 'LA') or 'transparency' in img.info
                            
                            # Generate and upload thumbnail
                            thumbnail_url = s3_client.upload_thumbnail(img, user_id, safe_filename)
                            
                            # Keep image copy for background analysis (save to new temp file)
                            # We'll pass the temp_path to background task, but need to ensure it's not deleted
                            image_for_analysis = temp_path
                    except Exception as e:
                        logger.warning(f"Failed to process image properties for {filename}: {str(e)}")
                
                # Upload original to S3
                s3_url = s3_client.upload_file(temp_path, s3_key)
                
                # Generate presigned URL for access
                presigned_url = s3_client.generate_presigned_url(s3_key, expiration=3600 * 24 * 7)  # 7 days
                
                # Parse reference_asset_type if provided
                parsed_reference_type = None
                if reference_asset_type:
                    try:
                        parsed_reference_type = ReferenceAssetType(reference_asset_type.lower())
                    except ValueError:
                        # Invalid type, will be None
                        pass
                
                # Set name (default to filename if not provided)
                asset_name = name or safe_filename
                
                # Create asset metadata
                asset_metadata = {
                    "original_filename": filename,
                    "mime_type": mime_type,
                }
                
                # Create database record
                asset_record = Asset(
                    id=asset_id,
                    user_id=user_id,
                    s3_key=s3_key,
                    s3_url=presigned_url,
                    asset_type=asset_type,
                    source=AssetSource.USER_UPLOAD,
                    file_name=safe_filename,
                    file_size_bytes=file_size,
                    mime_type=mime_type,
                    asset_metadata=asset_metadata,
                    # Reference asset fields
                    name=asset_name,
                    description=description,
                    reference_asset_type=parsed_reference_type,
                    thumbnail_url=thumbnail_url,
                    width=width,
                    height=height,
                    has_transparency=has_transparency
                )
                
                db.add(asset_record)
                db.commit()
                db.refresh(asset_record)
                
                # Trigger background analysis for images (reference assets)
                if is_image and image_for_analysis:
                    # Create a copy of the temp file for background task (since we'll delete original)
                    import shutil
                    analysis_temp_path = temp_path + "_analysis"
                    shutil.copy2(temp_path, analysis_temp_path)
                    
                    # Add background task for analysis
                    background_tasks.add_task(
                        analyze_asset_background,
                        asset_id=asset_id,
                        s3_url=s3_url,
                        image_path=analysis_temp_path,
                        user_provided_name=asset_name,
                        user_provided_description=description
                    )
                    logger.info(f"Queued background analysis for asset {asset_id}")
                
                uploaded_assets.append({
                    "asset_id": asset_id,
                    "filename": safe_filename,
                    "name": asset_name,
                    "asset_type": asset_type.value,
                    "reference_asset_type": parsed_reference_type.value if parsed_reference_type else None,
                    "file_size_bytes": file_size,
                    "s3_url": presigned_url,
                    "thumbnail_url": thumbnail_url,
                    "width": width,
                    "height": height,
                    "analysis_status": "pending" if is_image else None
                })
                
            finally:
                # Clean up temporary file (background task has its own copy)
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            continue
    
    if not uploaded_assets and errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    response_data = {
        "assets": uploaded_assets,
        "total": len(uploaded_assets)
    }
    
    if errors:
        response_data["errors"] = errors
        response_data["partial_success"] = True
    
    return JSONResponse(content=response_data)


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
    query = db.query(Asset).filter(
        Asset.user_id == user_id,
        Asset.source == AssetSource.USER_UPLOAD
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


@router.get("/api/assets/{asset_id}")
async def get_asset(
    asset_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a single asset by ID.
    
    Returns full asset details including all reference asset fields.
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == user_id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Generate fresh presigned URL
    presigned_url = s3_client.generate_presigned_url(asset.s3_key, expiration=3600 * 24 * 7)
    
    return {
        "asset_id": asset.id,
        "filename": asset.file_name or "unknown",
        "name": asset.name or asset.file_name or "unknown",
        "description": asset.description,
        "asset_type": asset.asset_type.value,
        "reference_asset_type": asset.reference_asset_type,
        "file_size_bytes": asset.file_size_bytes or 0,
        "mime_type": asset.mime_type,
        "s3_url": presigned_url,
        "thumbnail_url": asset.thumbnail_url,
        "width": asset.width,
        "height": asset.height,
        "has_transparency": asset.has_transparency,
        "is_logo": asset.is_logo,
        "logo_position_preference": asset.logo_position_preference,
        "primary_object": asset.primary_object,
        "colors": asset.colors,
        "dominant_colors_rgb": asset.dominant_colors_rgb,
        "style_tags": asset.style_tags,
        "recommended_shot_types": asset.recommended_shot_types,
        "usage_contexts": asset.usage_contexts,
        "usage_count": asset.usage_count or 0,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


@router.patch("/api/assets/{asset_id}")
async def update_asset(
    asset_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    reference_asset_type: Optional[str] = Form(None),
    logo_position_preference: Optional[str] = Form(None)
):
    """
    Update asset metadata.
    
    Accepts partial updates: name, description, reference_asset_type, logo_position_preference.
    S3 key remains unchanged - only DB fields update.
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == user_id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Update fields if provided
    if name is not None:
        asset.name = name
    if description is not None:
        asset.description = description
    if reference_asset_type is not None:
        try:
            asset.reference_asset_type = ReferenceAssetType(reference_asset_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid reference_asset_type: {reference_asset_type}")
    if logo_position_preference is not None:
        if asset.is_logo:
            asset.logo_position_preference = logo_position_preference
        else:
            raise HTTPException(status_code=400, detail="logo_position_preference can only be set for logos")
    
    db.commit()
    db.refresh(asset)
    
    # Generate fresh presigned URL
    presigned_url = s3_client.generate_presigned_url(asset.s3_key, expiration=3600 * 24 * 7)
    
    return {
        "asset_id": asset.id,
        "filename": asset.file_name or "unknown",
        "name": asset.name or asset.file_name or "unknown",
        "description": asset.description,
        "reference_asset_type": asset.reference_asset_type,
        "logo_position_preference": asset.logo_position_preference,
        "s3_url": presigned_url,
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else None,
    }


@router.delete("/api/assets/{asset_id}")
async def delete_asset(
    asset_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete an asset.
    
    Removes the asset from S3 (including thumbnail and related files) and from the database.
    """
    asset = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.user_id == user_id
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get original filename for S3 deletion
    filename = asset.file_name
    if not filename:
        raise HTTPException(status_code=400, detail="Asset filename not found")
    
    # Delete from S3 (all related files: original, thumbnail, preprocessed)
    s3_client.delete_asset_files(user_id, filename)
    
    # Delete from database
    db.delete(asset)
    db.commit()
    
    return {
        "message": "Asset deleted successfully",
        "asset_id": asset_id
    }

