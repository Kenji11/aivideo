#!/usr/bin/env python3
"""
CLI script to test Phase 2 Storyboard Generation

Usage:
    python test_phase2_storyboard.py "Coca vs Pepsi advertisement"

This script:
1. Runs Phase 1 (Intelligent Planning) to create beats
2. Runs Phase 2 (Storyboard Generation) to create images
3. Displays the results
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.common.constants import MOCK_USER_ID
from app.phases.phase1_validate.task_intelligent import plan_video_intelligent
from app.phases.phase2_storyboard.task import _generate_storyboard_impl


def main():
    # Get prompt from command line or use default
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
    else:
        prompt = "Coca vs Pepsi advertisement - create a competitive comparison ad showing both brands"
    
    print("=" * 80)
    print("🎬 Phase 2 Storyboard Generation Test")
    print("=" * 80)
    print(f"📝 Prompt: {prompt}")
    print()
    
    # Generate a video ID
    import uuid
    video_id = str(uuid.uuid4())
    print(f"🆔 Video ID: {video_id}")
    print()
    
    try:
        # ============ PHASE 1: INTELLIGENT PLANNING ============
        print("=" * 80)
        print("📋 Phase 1: Intelligent Planning")
        print("=" * 80)
        
        result1 = plan_video_intelligent.apply(args=[video_id, prompt, 0.5]).result
        
        if isinstance(result1, Exception):
            print(f"❌ Phase 1 failed: {result1}")
            return 1
        
        if result1.get('status') != "success":
            print(f"❌ Phase 1 failed: {result1.get('error_message', 'Unknown error')}")
            return 1
        
        spec = result1['output_data']['spec']
        beats = spec.get('beats', [])
        
        print(f"✅ Phase 1 Complete!")
        print(f"   - Duration: {spec.get('duration')}s")
        print(f"   - Beats: {len(beats)}")
        print(f"   - Archetype: {spec.get('template', 'N/A')}")
        print(f"   - Cost: ${result1.get('cost_usd', 0):.4f}")
        print()
        
        # Display beats
        print("📊 Beat Sequence:")
        for i, beat in enumerate(beats):
            print(f"   Beat {i}: {beat.get('beat_id')} ({beat.get('duration')}s) - {beat.get('prompt_template', '')[:60]}...")
        print()
        
        # ============ PHASE 2: STORYBOARD GENERATION ============
        print("=" * 80)
        print("🎨 Phase 2: Storyboard Generation")
        print("=" * 80)
        
        result2 = _generate_storyboard_impl(
            video_id=video_id,
            spec=spec,
            user_id=MOCK_USER_ID
        )
        
        if result2.get('status') != "success":
            print(f"❌ Phase 2 failed: {result2.get('error_message', 'Unknown error')}")
            return 1
        
        storyboard_images = result2['output_data'].get('storyboard_images', [])
        updated_spec = result2['output_data'].get('spec', spec)
        
        print(f"✅ Phase 2 Complete!")
        print(f"   - Storyboard Images: {len(storyboard_images)}")
        print(f"   - Cost: ${result2.get('cost_usd', 0):.4f}")
        print()
        
        # Display storyboard images
        print("🖼️  Storyboard Images:")
        for i, img_info in enumerate(storyboard_images):
            beat_id = img_info.get('beat_id', 'unknown')
            image_url = img_info.get('image_url', 'N/A')
            duration = img_info.get('duration', 0)
            start = img_info.get('start', 0)
            
            print(f"   Image {i+1}: Beat '{beat_id}' ({start}s-{start+duration}s)")
            print(f"      URL: {image_url}")
            print()
        
        # Verify beats have image_url
        print("✅ Verification: Checking if beats have image_url...")
        all_have_images = True
        for i, beat in enumerate(updated_spec.get('beats', [])):
            if 'image_url' in beat:
                print(f"   ✅ Beat {i} ({beat.get('beat_id')}): Has image_url")
            else:
                print(f"   ❌ Beat {i} ({beat.get('beat_id')}): Missing image_url")
                all_have_images = False
        
        if all_have_images:
            print()
            print("=" * 80)
            print("🎉 SUCCESS! All storyboard images generated and linked to beats!")
            print("=" * 80)
            print()
            print("📋 Summary:")
            print(f"   - Video ID: {video_id}")
            print(f"   - Total Beats: {len(beats)}")
            print(f"   - Total Images: {len(storyboard_images)}")
            print(f"   - Total Cost: ${result1.get('cost_usd', 0) + result2.get('cost_usd', 0):.4f}")
            print()
            print("💡 Next Steps:")
            print("   - These storyboard images can now be used in Phase 4 chunk generation")
            print("   - Each beat's image_url will be used as input for video chunk generation")
            return 0
        else:
            print()
            print("⚠️  WARNING: Some beats are missing image_url")
            return 1
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

