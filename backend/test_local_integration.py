#!/usr/bin/env python3
"""
Local Integration Test - Test the complete pipeline from frontend perspective
This simulates what the frontend does: generate -> poll status -> get video
"""

import sys
import json
import time
import requests
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

API_BASE_URL = "http://localhost:8000"

def test_complete_flow():
    """Test complete video generation flow"""
    print("="*70)
    print("LOCAL INTEGRATION TEST")
    print("="*70)
    print()
    
    # Test 1: Generate video (simulating frontend POST)
    print("1. Generating video...")
    request_data = {
        "title": "Test Ad Video",
        "description": "Quick test ad for sunglasses",
        "prompt": "Create a quick ad for premium sunglasses with modern style, vibrant colors, and bright lighting",
        "reference_assets": []
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/generate",
            json=request_data,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        video_id = result['video_id']
        print(f"   ✅ Video ID: {video_id}")
        print(f"   Status: {result['status']}")
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False
    
    # Test 2: Poll status (simulating frontend polling)
    print("\n2. Polling status...")
    max_polls = 60  # 2 minutes max (60 polls * 2 seconds)
    poll_count = 0
    
    while poll_count < max_polls:
        try:
            response = requests.get(f"{API_BASE_URL}/api/status/{video_id}", timeout=10)
            response.raise_for_status()
            status = response.json()
            
            poll_count += 1
            
            # Print status every 5 polls
            if poll_count % 5 == 0 or status['status'] in ['complete', 'failed']:
                print(f"   Poll {poll_count}: Status={status['status']}, Progress={status['progress']:.1f}%, Phase={status.get('current_phase', 'N/A')}")
            
            # Check for phase outputs
            if status.get('animatic_urls') and len(status['animatic_urls']) > 0:
                print(f"   ✅ Phase 2: {len(status['animatic_urls'])} animatic frames")
            
            if status.get('reference_assets'):
                print(f"   ✅ Phase 3: Reference assets generated")
            
            if status.get('stitched_video_url'):
                print(f"   ✅ Phase 4: Stitched video ready")
            
            # Check completion
            if status['status'] == 'complete':
                print(f"\n   ✅ Video generation complete!")
                print(f"   Final video URL: {status.get('stitched_video_url', 'N/A')[:80]}...")
                break
            
            if status['status'] == 'failed':
                print(f"\n   ❌ Video generation failed: {status.get('error', 'Unknown error')}")
                return False
            
            time.sleep(2)  # Poll every 2 seconds (like frontend)
            
        except Exception as e:
            print(f"   ⚠️  Poll error: {str(e)}")
            time.sleep(2)
    
    if poll_count >= max_polls:
        print(f"\n   ⏱️  Timeout after {max_polls} polls")
        return False
    
    # Test 3: Get video list (simulating frontend "My Projects")
    print("\n3. Fetching video list...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/videos", timeout=10)
        response.raise_for_status()
        videos = response.json()
        print(f"   ✅ Found {videos['total']} videos")
        
        # Check if our video is in the list
        our_video = next((v for v in videos['videos'] if v['video_id'] == video_id), None)
        if our_video:
            print(f"   ✅ Our video found in list")
            print(f"      Title: {our_video['title']}")
            print(f"      Status: {our_video['status']}")
            print(f"      Has video URL: {bool(our_video.get('final_video_url'))}")
        else:
            print(f"   ⚠️  Our video not found in list")
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False
    
    # Test 4: Get individual video (simulating frontend video detail)
    print("\n4. Fetching video details...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/video/{video_id}", timeout=10)
        response.raise_for_status()
        video = response.json()
        print(f"   ✅ Video details retrieved")
        print(f"      Title: {video['title']}")
        print(f"      Status: {video['status']}")
        print(f"      Cost: ${video['cost_usd']:.4f}")
        if video.get('generation_time_seconds'):
            print(f"      Generation time: {video['generation_time_seconds']:.1f}s")
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED!")
    print("="*70)
    print(f"\nVideo ID: {video_id}")
    print(f"Frontend URL: http://localhost:5173")
    print(f"Backend API: http://localhost:8000/docs")
    return True

if __name__ == "__main__":
    success = test_complete_flow()
    sys.exit(0 if success else 1)

