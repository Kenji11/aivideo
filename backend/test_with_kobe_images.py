#!/usr/bin/env python3
"""
Test video generation with uploaded Kobe Bryant images
"""
import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:8000"

def upload_image(image_path):
    """Upload an image and return asset ID"""
    with open(image_path, 'rb') as f:
        files = {'files': (image_path, f, 'image/jpeg')}
        response = requests.post(f"{API_URL}/api/upload", files=files)
        response.raise_for_status()
        result = response.json()
        if result.get('assets'):
            return result['assets'][0]['asset_id']
    return None

def generate_with_references(prompt, reference_asset_ids):
    """Generate video with reference images"""
    response = requests.post(
        f"{API_URL}/api/generate",
        json={
            "title": "Nike Kobe Bryant - Black Mamba Legacy",
            "description": "Epic tribute ad with Kobe images as reference",
            "prompt": prompt,
            "reference_assets": reference_asset_ids  # List of asset IDs
        },
        timeout=10
    )
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    print("="*70)
    print("📸 TEST: Video Generation with Kobe Bryant Reference Images")
    print("="*70)
    print()
    print("To use this:")
    print("1. Upload Kobe Bryant images using: POST /api/upload")
    print("2. Get asset IDs from the response")
    print("3. Pass asset IDs in reference_assets when generating video")
    print()
    print("Example:")
    print('  reference_assets = ["asset-id-1", "asset-id-2"]')
    print()
    print("The system will:")
    print("  ✅ Use your uploaded Kobe images as primary reference")
    print("  ✅ Generate video based on those images")
    print("  ✅ Create 6 chunks for 30-second video")
    print()
