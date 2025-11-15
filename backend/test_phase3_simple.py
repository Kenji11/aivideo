#!/usr/bin/env python3
"""
Simple Phase 3 test - API calls only (no S3 uploads).
Useful for testing Replicate API integration without AWS setup.
"""

import sys
import os
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Check for required env vars
replicate_token = os.getenv("REPLICATE_API_TOKEN")
if not replicate_token:
    print("❌ ERROR: REPLICATE_API_TOKEN not found in environment")
    print("   Set it with: export REPLICATE_API_TOKEN='your-token'")
    print("   Or add to backend/.env file")
    sys.exit(1)

# Set dummy vars if not present (for config loading)
if not os.getenv("AWS_ACCESS_KEY_ID"):
    os.environ["AWS_ACCESS_KEY_ID"] = "dummy"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "dummy"
    os.environ["S3_BUCKET"] = "dummy"
    os.environ["AWS_REGION"] = "us-east-2"
    print("⚠️  AWS credentials not found - using dummy values (S3 uploads will fail)")
    print("   This test only validates Replicate API calls\n")

# Set dummy database/redis if not present (for config loading)
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://dummy:dummy@localhost/dummy"
if not os.getenv("REDIS_URL"):
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "dummy"

# Import directly to avoid initializing other services
import replicate
from app.config import get_settings

settings = get_settings()
replicate_client_obj = replicate.Client(api_token=settings.replicate_api_token)


def test_sdxl_generation():
    """Test SDXL image generation directly"""
    
    print("=" * 70)
    print("PHASE 3 SIMPLE TEST - SDXL API Only")
    print("=" * 70)
    print("This test generates images using Replicate API")
    print("but does NOT upload to S3 (no AWS needed)")
    print()
    
    # Test 1: Style Guide Prompt
    print("\n" + "="*70)
    print("TEST 1: Style Guide Generation")
    print("="*70)
    
    style_prompt = "cinematic style, gold black white colors, elegant mood, dramatic soft lighting, high quality reference image"
    
    try:
        print(f"Prompt: {style_prompt}")
        print("Calling Replicate SDXL...")
        
        output = replicate_client_obj.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": style_prompt,
                "width": 1024,
                "height": 1024,
                "num_outputs": 1
            }
        )
        
        # Get image URL
        if isinstance(output, list):
            image_url = output[0]
        else:
            image_url = output
        
        print(f"✅ SUCCESS!")
        print(f"Image URL: {image_url}")
        print(f"Cost: $0.0055 (SDXL)")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False
    
    # Test 2: Product Reference Prompt
    print("\n" + "="*70)
    print("TEST 2: Product Reference Generation")
    print("="*70)
    
    product_prompt = "Professional product photography of Chronos Elite Watch, luxury timepiece, studio lighting, high quality, clean background"
    
    try:
        print(f"Prompt: {product_prompt}")
        print("Calling Replicate SDXL...")
        
        output = replicate_client_obj.run(
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            input={
                "prompt": product_prompt,
                "width": 1024,
                "height": 1024,
                "num_outputs": 1
            }
        )
        
        # Get image URL
        if isinstance(output, list):
            image_url = output[0]
        else:
            image_url = output
        
        print(f"✅ SUCCESS!")
        print(f"Image URL: {image_url}")
        print(f"Cost: $0.0055 (SDXL)")
        
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print("\nNote: Images are generated but not uploaded to S3.")
    print("For full Phase 3 test with S3, use: python test_phase3.py")
    
    return True


if __name__ == "__main__":
    success = test_sdxl_generation()
    sys.exit(0 if success else 1)

