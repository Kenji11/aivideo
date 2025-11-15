import pytest
import os
import tempfile
from PIL import Image
from app.phases.phase3_references.service import ReferenceAssetService
from app.phases.phase3_references.asset_handler import AssetHandler
from app.common.exceptions import ValidationException


def test_asset_handler_validation():
    """Test image validation"""
    handler = AssetHandler()
    
    # Create a valid test image
    test_image = Image.new('RGB', (1024, 1024), color='red')
    temp_path = tempfile.mktemp(suffix='.png')
    test_image.save(temp_path)
    
    assert handler.validate_image(temp_path) is True
    
    # Test invalid format (create a text file)
    invalid_path = tempfile.mktemp(suffix='.txt')
    with open(invalid_path, 'w') as f:
        f.write("not an image")
    
    assert handler.validate_image(invalid_path) is False
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
    if os.path.exists(invalid_path):
        os.remove(invalid_path)


def test_asset_handler_download():
    """Test asset download (mock test - requires actual URL or S3 key)"""
    handler = AssetHandler()
    
    # This test would require actual S3 access or HTTP URL
    # For now, just test that the method exists
    assert hasattr(handler, 'download_asset')
    assert hasattr(handler, 'process_uploaded_assets')


def test_asset_handler_resize():
    """Test image resizing"""
    handler = AssetHandler()
    
    # Create a large test image (3000x3000)
    large_image = Image.new('RGB', (3000, 3000), color='blue')
    temp_path = tempfile.mktemp(suffix='.png')
    large_image.save(temp_path)
    
    # Resize
    resized_path = handler._resize_if_needed(temp_path)
    
    # Check dimensions
    with Image.open(resized_path) as img:
        width, height = img.size
        assert width <= handler.max_dimension
        assert height <= handler.max_dimension
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
    if os.path.exists(resized_path) and resized_path != temp_path:
        os.remove(resized_path)


# Tests requiring API keys
@pytest.mark.skipif(
    not os.getenv("REPLICATE_API_TOKEN"),
    reason="Requires REPLICATE_API_TOKEN environment variable"
)
def test_generate_style_guide():
    """Test style guide generation with real API (if key available)"""
    service = ReferenceAssetService()
    
    style = {
        'aesthetic': 'cinematic',
        'color_palette': ['gold', 'black', 'white'],
        'mood': 'elegant',
        'lighting': 'soft'
    }
    
    # This would require actual S3 access
    # For now, just test that the method exists
    assert hasattr(service, '_generate_style_guide')


@pytest.mark.skipif(
    not os.getenv("REPLICATE_API_TOKEN"),
    reason="Requires REPLICATE_API_TOKEN environment variable"
)
def test_generate_product_reference():
    """Test product reference generation with real API (if key available)"""
    service = ReferenceAssetService()
    
    product = {
        'name': 'Luxury Watch',
        'category': 'accessories'
    }
    
    # This would require actual S3 access
    # For now, just test that the method exists
    assert hasattr(service, '_generate_product_reference')

