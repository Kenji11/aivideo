import os
import tempfile
import requests
from typing import Dict, List, Optional
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.phases.phase3_references.asset_handler import AssetHandler
from app.phases.phase3_references.schemas import ReferenceAssetsOutput
from app.common.constants import COST_SDXL_IMAGE, S3_REFERENCES_PREFIX
from app.common.exceptions import PhaseException


class ReferenceAssetService:
    """Service for generating reference assets (style guide, product references)"""
    
    def __init__(self):
        self.replicate = replicate_client
        self.s3 = s3_client
        self.asset_handler = AssetHandler()
        self.total_cost = 0.0
    
    def generate_all_references(self, video_id: str, spec: Dict) -> Dict:
        """
        Generate all reference assets for a video.
        
        Args:
            video_id: Unique video generation ID
            spec: Video specification from Phase 1
            
        Returns:
            Dictionary with reference URLs and metadata
        """
        try:
            # Extract style information
            style = spec.get('style', {})
            product = spec.get('product')
            uploaded_assets = spec.get('uploaded_assets', [])
            
            # Generate style guide
            style_guide_url = self._generate_style_guide(video_id, style)
            
            # Generate product reference if product exists
            product_reference_url = None
            if product:
                product_reference_url = self._generate_product_reference(video_id, product)
            
            # Process uploaded assets
            processed_assets = []
            if uploaded_assets:
                processed_assets = self.asset_handler.process_uploaded_assets(
                    uploaded_assets,
                    video_id
                )
            
            # Build output
            output = {
                'style_guide_url': style_guide_url,
                'product_reference_url': product_reference_url,
                'uploaded_assets': processed_assets,
                'total_cost': self.total_cost
            }
            
            return output
            
        except Exception as e:
            raise PhaseException(f"Failed to generate references: {str(e)}")
    
    def _generate_style_guide(self, video_id: str, style: Dict) -> str:
        """
        Generate style guide image using SDXL.
        
        Args:
            video_id: Video ID
            style: Style specification dictionary
            
        Returns:
            S3 URL of generated style guide
        """
        # Build prompt from style information
        aesthetic = style.get('aesthetic', 'cinematic')
        color_palette = style.get('color_palette', [])
        mood = style.get('mood', 'elegant')
        lighting = style.get('lighting', 'soft')
        
        # Format color palette
        colors_str = ', '.join(color_palette) if color_palette else 'neutral tones'
        
        # Build prompt
        prompt = f"{aesthetic} style, {colors_str} colors, {mood} mood, {lighting} lighting, high quality reference image"
        
        try:
            # Call Replicate SDXL model
            output = self.replicate.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": prompt,
                    "width": 1024,
                    "height": 1024,
                    "num_outputs": 1
                }
            )
            
            # Download generated image
            # Replicate returns a URL or list of URLs
            if isinstance(output, list):
                image_url = output[0]
            else:
                image_url = output
            
            # Download image
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            
            # Save to temp file
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            # Upload to S3
            s3_key = f"{S3_REFERENCES_PREFIX}/{video_id}/style_guide.png"
            s3_url = self.s3.upload_file(temp_path, s3_key)
            
            # Track cost
            self.total_cost += COST_SDXL_IMAGE
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return s3_url
            
        except Exception as e:
            raise PhaseException(f"Failed to generate style guide: {str(e)}")
    
    def _generate_product_reference(self, video_id: str, product: Dict) -> Optional[str]:
        """
        Generate product reference image using SDXL.
        
        Args:
            video_id: Video ID
            product: Product specification dictionary
            
        Returns:
            S3 URL of generated product reference, or None if no product
        """
        if not product:
            return None
        
        product_name = product.get('name', 'product')
        product_category = product.get('category', 'item')
        
        # Build prompt
        prompt = f"Professional product photography of {product_name}, {product_category}, studio lighting, high quality, clean background"
        
        try:
            # Call Replicate SDXL model
            output = self.replicate.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": prompt,
                    "width": 1024,
                    "height": 1024,
                    "num_outputs": 1
                }
            )
            
            # Download generated image
            if isinstance(output, list):
                image_url = output[0]
            else:
                image_url = output
            
            # Download image
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            
            # Save to temp file
            temp_path = tempfile.mktemp(suffix='.png')
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            # Upload to S3
            s3_key = f"{S3_REFERENCES_PREFIX}/{video_id}/product_reference.png"
            s3_url = self.s3.upload_file(temp_path, s3_key)
            
            # Track cost
            self.total_cost += COST_SDXL_IMAGE
            
            # Cleanup
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return s3_url
            
        except Exception as e:
            raise PhaseException(f"Failed to generate product reference: {str(e)}")
