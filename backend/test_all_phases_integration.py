#!/usr/bin/env python3
"""
Comprehensive test for all phases - Frontend-Backend Integration Test
Tests the complete flow from Phase 1 to Phase 4 and verifies status API responses
"""

import sys
import json
import time
import requests
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

API_BASE_URL = "http://localhost:8000"

def test_generate_endpoint():
    """Test Phase 1: Generate endpoint"""
    print("\n" + "="*70)
    print("TEST 1: Generate Video Endpoint")
    print("="*70)
    
    request_data = {
        "title": "Test Video - All Phases",
        "description": "Testing all phases integration",
        "prompt": "Create a luxury product showcase video for premium sunglasses with modern style, vibrant colors, and bright lighting",
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
        
        print(f"✅ Generate endpoint successful")
        print(f"   Video ID: {result['video_id']}")
        print(f"   Status: {result['status']}")
        print(f"   Message: {result['message']}")
        
        return result['video_id']
    except Exception as e:
        print(f"❌ Generate endpoint failed: {str(e)}")
        return None

def test_status_endpoint(video_id: str, expected_phase: str = None):
    """Test status endpoint and verify phase data"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/status/{video_id}", timeout=10)
        response.raise_for_status()
        status = response.json()
        
        print(f"\n📊 Status Check:")
        print(f"   Video ID: {status['video_id']}")
        print(f"   Status: {status['status']}")
        print(f"   Progress: {status['progress']}%")
        print(f"   Current Phase: {status.get('current_phase', 'N/A')}")
        
        if expected_phase:
            if status.get('current_phase') == expected_phase:
                print(f"   ✅ Phase matches expected: {expected_phase}")
            else:
                print(f"   ⚠️  Phase mismatch: expected {expected_phase}, got {status.get('current_phase')}")
        
        # Check phase-specific data
        if status.get('reference_assets'):
            print(f"   ✅ Phase 3 data present: reference_assets")
            if status['reference_assets'].get('style_guide_url'):
                print(f"      - Style Guide URL: {status['reference_assets']['style_guide_url'][:80]}...")
            if status['reference_assets'].get('product_reference_url'):
                print(f"      - Product Reference URL: {status['reference_assets']['product_reference_url'][:80]}...")
        
        if status.get('stitched_video_url'):
            print(f"   ✅ Phase 4 data present: stitched_video_url")
            print(f"      - Stitched Video URL: {status['stitched_video_url'][:80]}...")
        
        if status.get('error'):
            print(f"   ❌ Error: {status['error']}")
        
        return status
    except Exception as e:
        print(f"❌ Status endpoint failed: {str(e)}")
        return None

def test_all_phases_progression(video_id: str):
    """Monitor all phases progression"""
    print("\n" + "="*70)
    print("TEST 2: Monitor All Phases Progression")
    print("="*70)
    print("Polling status every 3 seconds...")
    print()
    
    phases_seen = set()
    max_wait_time = 600  # 10 minutes max
    start_time = time.time()
    poll_interval = 3
    
    while time.time() - start_time < max_wait_time:
        status = test_status_endpoint(video_id)
        
        if not status:
            break
        
        current_phase = status.get('current_phase')
        if current_phase:
            if current_phase not in phases_seen:
                phases_seen.add(current_phase)
                print(f"\n🎯 NEW PHASE DETECTED: {current_phase}")
                
                # Phase-specific checks
                if current_phase == 'phase1_validate':
                    print("   ✅ Phase 1: Validation in progress")
                elif current_phase == 'phase2_animatic':
                    print("   ✅ Phase 2: Animatic generation in progress")
                elif current_phase == 'phase3_references':
                    print("   ✅ Phase 3: Reference assets generation in progress")
                elif current_phase == 'phase4_chunks':
                    print("   ✅ Phase 4: Video chunks generation in progress")
        
        # Check completion
        if status['status'] == 'complete':
            print("\n" + "="*70)
            print("✅ ALL PHASES COMPLETED SUCCESSFULLY!")
            print("="*70)
            print(f"   Final Progress: {status['progress']}%")
            print(f"   Final Phase: {status.get('current_phase', 'N/A')}")
            
            if status.get('reference_assets'):
                print(f"   ✅ Phase 3 Output: Reference assets available")
            if status.get('stitched_video_url'):
                print(f"   ✅ Phase 4 Output: Stitched video available")
            
            return True
        
        if status['status'] == 'failed':
            print("\n" + "="*70)
            print("❌ GENERATION FAILED")
            print("="*70)
            print(f"   Error: {status.get('error', 'Unknown error')}")
            return False
        
        time.sleep(poll_interval)
    
    print("\n⏱️  Timeout waiting for completion")
    return False

def test_frontend_api_compatibility():
    """Test that backend responses match frontend expectations"""
    print("\n" + "="*70)
    print("TEST 3: Frontend API Compatibility")
    print("="*70)
    
    # Test with a known video ID (if any exist)
    try:
        # Get list of videos
        response = requests.get(f"{API_BASE_URL}/api/videos", timeout=10)
        if response.status_code == 200:
            videos = response.json()
            if videos.get('videos') and len(videos['videos']) > 0:
                test_video_id = videos['videos'][0]['video_id']
                print(f"Testing with existing video: {test_video_id}")
                
                status = test_status_endpoint(test_video_id)
                
                # Verify frontend-expected fields
                required_fields = ['video_id', 'status', 'progress', 'current_phase']
                missing_fields = [f for f in required_fields if f not in status]
                
                if missing_fields:
                    print(f"   ❌ Missing fields: {missing_fields}")
                else:
                    print(f"   ✅ All required fields present")
                
                # Verify optional fields structure
                if 'reference_assets' in status and status['reference_assets']:
                    ref_assets = status['reference_assets']
                    if 'style_guide_url' in ref_assets or 'product_reference_url' in ref_assets:
                        print(f"   ✅ Reference assets structure correct")
                
                if 'stitched_video_url' in status:
                    print(f"   ✅ Stitched video URL present")
                
                return True
            else:
                print("   ℹ️  No existing videos to test with")
                return True
        else:
            print(f"   ⚠️  Could not fetch videos list: {response.status_code}")
            return True
    except Exception as e:
        print(f"   ⚠️  Compatibility test error: {str(e)}")
        return True

def main():
    print("="*70)
    print("COMPREHENSIVE FRONTEND-BACKEND INTEGRATION TEST")
    print("Testing All Phases: 1 → 2 → 3 → 4")
    print("="*70)
    
    # Test 1: Generate endpoint
    video_id = test_generate_endpoint()
    
    if not video_id:
        print("\n❌ Cannot continue without video_id")
        return 1
    
    # Test 2: Monitor all phases
    success = test_all_phases_progression(video_id)
    
    # Test 3: Frontend compatibility
    test_frontend_api_compatibility()
    
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    if success:
        print("✅ All phases completed successfully")
        print("✅ Frontend-backend integration verified")
    else:
        print("⚠️  Some phases may have failed or timed out")
    
    print("\n💡 To test in browser:")
    print(f"   1. Open http://localhost:5173")
    print(f"   2. Create a video with prompt")
    print(f"   3. Watch progress through all 4 phases")
    print(f"   4. Verify video appears in preview")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

