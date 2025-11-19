from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import uuid
import tempfile
import os
from pathlib import Path
import mimetypes

from app.database import get_db
from app.common.models import Asset, AssetType, AssetSource
from app.common.auth import get_current_user
from app.common.schemas import UploadedAsset, UploadResponse
from app.services.s3 import s3_client

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

# Max file size: 100MB
MAX_FILE_SIZE = 100 * 1024 * 1024


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


@router.post("/api/upload")
async def upload_assets(
    files: List[UploadFile] = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload one or more assets (images, videos, PDFs) to S3 and create database records.
    
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
            
            if file_size > MAX_FILE_SIZE:
                errors.append(f"{file.filename}: File too large (max {MAX_FILE_SIZE / (1024*1024)}MB)")
                continue
            
            if file_size == 0:
                errors.append(f"{file.filename}: File is empty")
                continue
            
            # Validate MIME type
            mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
            
            if mime_type not in ALL_ALLOWED_TYPES:
                errors.append(f"{file.filename}: File type not allowed. Allowed: images, videos, PDFs")
                continue
            
            # Determine asset type
            asset_type = determine_asset_type(mime_type)
            
            # Generate unique asset ID
            asset_id = str(uuid.uuid4())
            
            # Create S3 key: assets/{user_id}/{asset_id}/{filename}
            filename = file.filename or f"file_{asset_id}"
            # Sanitize filename
            safe_filename = "".join(c for c in filename if c.isalnum() or c in "._- ").strip()
            s3_key = f"assets/{user_id}/{asset_id}/{safe_filename}"
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as temp_file:
                temp_file.write(file_content)
                temp_path = temp_file.name
            
            try:
                # Upload to S3
                s3_url = s3_client.upload_file(temp_path, s3_key)
                
                # Generate presigned URL for access
                presigned_url = s3_client.generate_presigned_url(s3_key, expiration=3600 * 24 * 7)  # 7 days
                
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
                    file_name=filename,
                    file_size_bytes=file_size,
                    mime_type=mime_type,
                    asset_metadata=asset_metadata
                )
                
                db.add(asset_record)
                db.commit()
                db.refresh(asset_record)
                
                uploaded_assets.append({
                    "asset_id": asset_id,
                    "filename": filename,
                    "asset_type": asset_type.value,
                    "file_size_bytes": file_size,
                    "s3_url": presigned_url
                })
                
            finally:
                # Clean up temporary file
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
    db: Session = Depends(get_db)
):
    """
    Get all assets for the authenticated user.
    
    Returns list of assets with metadata including presigned URLs for access.
    """
    # Query assets for the authenticated user only
    assets = db.query(Asset).filter(Asset.user_id == user_id).order_by(Asset.created_at.desc()).all()
    
    # Convert to response format
    asset_list = []
    for asset in assets:
        # Generate fresh presigned URL (7 days expiration)
        presigned_url = s3_client.generate_presigned_url(asset.s3_key, expiration=3600 * 24 * 7)
        
        asset_list.append({
            "asset_id": asset.id,
            "filename": asset.file_name or "unknown",
            "asset_type": asset.asset_type.value,
            "file_size_bytes": asset.file_size_bytes or 0,
            "s3_url": presigned_url,
            "created_at": asset.created_at.isoformat() if asset.created_at else None,
        })
    
    return {
        "assets": asset_list,
        "total": len(asset_list),
        "user_id": user_id
    }

