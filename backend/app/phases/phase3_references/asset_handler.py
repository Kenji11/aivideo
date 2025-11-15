import os
import tempfile
import requests
from typing import List, Dict, Optional
from PIL import Image
from app.services.s3 import s3_client
from app.common.exceptions import ValidationException


class AssetHandler:
    """Handle uploaded assets and reference images"""
    
    def __init__(self):
        self.s3 = s3_client
        self.max_dimension = 2048
        self.allowed_formats = ['JPEG', 'PNG', 'JPG']
    
    def process_uploaded_assets(self, assets: List[Dict], video_id: str) -> List[Dict]:
        """
        Process and validate uploaded assets.
        
        Args:
            assets: List of asset dictionaries with 'url' or 's3_key'
            video_id: Video ID for organizing assets
            
        Returns:
            List of processed asset metadata dictionaries
        """
        processed_assets = []
        
        for i, asset in enumerate(assets):
            try:
                # Download asset
                asset_path = self.download_asset(asset.get('url') or asset.get('s3_key'))
                
                # Validate image
                if not self.validate_image(asset_path):
                    raise ValidationException(f"Invalid image format or dimensions: {asset.get('url', 'unknown')}")
                
                # Resize if needed
                resized_path = self._resize_if_needed(asset_path)
                
                # Upload to S3
                asset_key = f"references/{video_id}/uploaded_assets/asset_{i:02d}.png"
                s3_url = self.s3.upload_file(resized_path, asset_key)
                
                # Get image metadata
                with Image.open(resized_path) as img:
                    width, height = img.size
                    format_name = img.format
                
                # Store metadata
                processed_asset = {
                    's3_key': asset_key,
                    's3_url': s3_url,
                    'width': width,
                    'height': height,
                    'format': format_name,
                    'original_url': asset.get('url') or asset.get('s3_key')
                }
                
                processed_assets.append(processed_asset)
                
                # Cleanup temp file
                if os.path.exists(resized_path) and resized_path != asset_path:
                    os.remove(resized_path)
                if os.path.exists(asset_path):
                    os.remove(asset_path)
                    
            except Exception as e:
                raise ValidationException(f"Failed to process asset {i}: {str(e)}")
        
        return processed_assets
    
    def download_asset(self, asset_url: str) -> str:
        """
        Download asset to temp file for processing.
        
        Args:
            asset_url: URL or S3 key of the asset
            
        Returns:
            Path to temporary file
        """
        # Check if it's an S3 key (starts with s3:// or is just a key)
        if asset_url.startswith('s3://'):
            # Extract bucket and key
            parts = asset_url.replace('s3://', '').split('/', 1)
            if len(parts) == 2:
                bucket, key = parts
                if bucket == self.s3.bucket:
                    return self.s3.download_temp(key)
        
        # Check if it's just an S3 key (no s3:// prefix)
        if not asset_url.startswith('http'):
            # Assume it's an S3 key
            return self.s3.download_temp(asset_url)
        
        # Otherwise, download from HTTP/HTTPS URL
        response = requests.get(asset_url, timeout=30)
        response.raise_for_status()
        
        # Create temp file
        suffix = os.path.splitext(asset_url)[1] or '.jpg'
        temp_path = tempfile.mktemp(suffix=suffix)
        
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        return temp_path
    
    def validate_image(self, image_path: str) -> bool:
        """
        Validate image format and dimensions.
        
        Args:
            image_path: Path to image file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                # Check format
                if img.format not in self.allowed_formats:
                    return False
                
                # Check dimensions
                width, height = img.size
                if width > self.max_dimension or height > self.max_dimension:
                    return False
                
                # Check if image is valid
                img.verify()
                
            return True
            
        except Exception:
            return False
    
    def _resize_if_needed(self, image_path: str) -> str:
        """
        Resize image if it exceeds max dimensions.
        
        Args:
            image_path: Path to image
            
        Returns:
            Path to resized image (or original if no resize needed)
        """
        with Image.open(image_path) as img:
            width, height = img.size
            
            # Check if resize needed
            if width <= self.max_dimension and height <= self.max_dimension:
                return image_path
            
            # Calculate new dimensions (maintain aspect ratio)
            if width > height:
                new_width = self.max_dimension
                new_height = int(height * (self.max_dimension / width))
            else:
                new_height = self.max_dimension
                new_width = int(width * (self.max_dimension / height))
            
            # Resize
            resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save to new temp file
            suffix = os.path.splitext(image_path)[1] or '.png'
            resized_path = tempfile.mktemp(suffix=suffix)
            resized.save(resized_path, format=img.format or 'PNG')
            
            return resized_path
