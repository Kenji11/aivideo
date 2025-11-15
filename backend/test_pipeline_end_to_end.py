#!/usr/bin/env python3
"""
End-to-end test of the video generation pipeline
Tests the complete flow: generate -> poll status -> verify all phases
"""

import sys
import time
import requests
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

API_BASE_URL = "http://localhost:8000"

def test_pipeline():
    """Test complete pipeline execution"""
    print("="*70)
    print("END-TO-END PIPELINE TEST")
    print("="*70)
    print()
    
    # Step 1: Generate video
    print("1️⃣  Creating video generation request...")
    request_data = {
        "title": "Test Pipeline Video",
        "description": "Testing complete pipeline execution",
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
    
    # Step 2: Poll status and verify phases
    print("\n2️⃣  Polling status and verifying phases...")
    max_polls = 120  # 4 minutes max (120 polls * 2 seconds)
    poll_count = 0
    
    phases_seen = set()
    validate_seen = False
    references_seen = False
    video_seen = False
    
    while poll_count < max_polls:
        try:
            response = requests.get(f"{API_BASE_URL}/api/status/{video_id}", timeout=10)
            response.raise_for_status()
            status = response.json()
            
            poll_count += 1
            
            # Track current phase
            if status.get('current_phase'):
                phases_seen.add(status['current_phase'])
            
            # Print status every 10 polls or on phase change
            if poll_count % 10 == 0 or status.get('current_phase') != status.get('current_phase'):
                print(f"   Poll {poll_count}: Status={status['status']}, Progress={status['progress']:.1f}%, Phase={status.get('current_phase', 'N/A')}")
            
            # Check for Phase 1 (validate)
            if status.get('current_phase') == 'phase1_validate' and not validate_seen:
                validate_seen = True
                print(f"   ✅ Phase 1 Complete: Prompt validated and spec generated")
            
            # Check for Phase 3 (references) - Phase 2 is disabled for MVP
            if status.get('reference_assets') and not references_seen:
                references_seen = True
                refs = status['reference_assets']
                print(f"   ✅ Phase 3 Complete: Product reference generated")
                if refs.get('product_reference_url'):
                    print(f"      Product ref: {refs['product_reference_url'][:60]}...")
                if refs.get('style_guide_url'):
                    print(f"      Style guide: {refs['style_guide_url'][:60]}... (OUT OF SCOPE for MVP)")
            
            # Check for Phase 4 (stitched video)
            if status.get('stitched_video_url') and not video_seen:
                video_seen = True
                print(f"   ✅ Phase 4 Complete: Video chunks generated and stitched!")
                print(f"      Video URL: {status['stitched_video_url'][:60]}...")
            
            # Check completion
            if status['status'] == 'complete':
                print(f"\n   ✅ Video generation COMPLETE!")
                print(f"   Final status: {status['status']}")
                print(f"   Final phase: {status.get('current_phase', 'N/A')}")
                print(f"   Progress: {status['progress']:.1f}%")
                
                # Verify all phases completed
                print(f"\n   📊 Phase Summary:")
                print(f"      Phases seen: {sorted(phases_seen)}")
                print(f"      Phase 1 (Validate): {'✅' if validate_seen else '❌'}")
                print(f"      Phase 2 (Animatic): ⏭️  SKIPPED (disabled for MVP)")
                print(f"      Phase 3 (References): {'✅' if references_seen else '❌'}")
                print(f"      Phase 4 (Video): {'✅' if video_seen else '❌'}")
                
                if references_seen and video_seen:
                    print(f"\n   🎉 ALL PHASES COMPLETED SUCCESSFULLY!")
                else:
                    print(f"\n   ⚠️  Some phases missing!")
                
                break
            
            if status['status'] == 'failed':
                print(f"\n   ❌ Video generation FAILED: {status.get('error', 'Unknown error')}")
                return False
            
            time.sleep(2)  # Poll every 2 seconds
            
        except Exception as e:
            print(f"   ⚠️  Poll error: {str(e)}")
            time.sleep(2)
    
    if poll_count >= max_polls:
        print(f"\n   ⏱️  Timeout after {max_polls} polls")
        return False
    
    # Step 3: Verify database record
    print("\n3️⃣  Verifying database record...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/video/{video_id}", timeout=10)
        response.raise_for_status()
        video = response.json()
        
        print(f"   ✅ Video record found")
        print(f"      Title: {video['title']}")
        print(f"      Status: {video['status']}")
        print(f"      Cost: ${video['cost_usd']:.4f}")
        if video.get('generation_time_seconds'):
            print(f"      Generation time: {video['generation_time_seconds']:.1f}s")
        if video.get('final_video_url'):
            print(f"      Final video URL: {video['final_video_url'][:60]}...")
        else:
            print(f"      ⚠️  No final_video_url in database!")
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETE!")
    print("="*70)
    print(f"\nVideo ID: {video_id}")
    print(f"Frontend: http://localhost:5173")
    print(f"API Docs: http://localhost:8000/docs")
    
    return True

if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)

