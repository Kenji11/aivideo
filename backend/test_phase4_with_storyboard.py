#!/usr/bin/env python3
"""
Test Phase 4 using existing Phase 2 storyboard images

This script:
1. Finds videos with Phase 2 storyboard images
2. Uses those storyboard images for Phase 4 chunk generation
3. Tests the full Phase 4 pipeline with existing storyboards

Usage:
    python test_phase4_with_storyboard.py
    python test_phase4_with_storyboard.py <video_id>
"""

import sys
import os
import json
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.common.models import VideoGeneration
from app.common.constants import MOCK_USER_ID
from app.services.s3 import s3_client


def find_videos_with_storyboard():
    """Find videos that have Phase 2 storyboard images."""
    
    # Known video IDs from Phase 2 tests (from test output logs)
    known_video_ids = [
        '12f8a684-8aa0-4c82-a2a3-2c302e22b743',  # First test
        '2db7d382-dbee-4a9e-932c-ffa35249b666',  # Second test
    ]
    
    results = []
    
    # Check database first
    db = SessionLocal()
    try:
        # Only select fields that exist (avoid storyboard_images column if it doesn't exist)
        videos = db.query(
            VideoGeneration.id,
            VideoGeneration.created_at,
            VideoGeneration.phase_outputs
        ).filter(
            VideoGeneration.phase_outputs.isnot(None)
        ).order_by(VideoGeneration.created_at.desc()).limit(10).all()
        
        for video in videos:
            video_id, created_at, phase_outputs = video
            phase_outputs = phase_outputs or {}
            phase2_output = phase_outputs.get('phase2_storyboard')
            
            if phase2_output and phase2_output.get('status') == 'success':
                spec = phase2_output.get('output_data', {}).get('spec', {})
                beats = spec.get('beats', [])
                storyboard_count = len([b for b in beats if b.get('image_url')])
                
                results.append({
                    'video_id': video_id,
                    'created_at': str(created_at),
                    'beats': len(beats),
                    'storyboard_images': storyboard_count,
                    'spec': spec,
                    'source': 'database'
                })
    finally:
        db.close()
    
    # Check S3 for known video IDs (from standalone tests)
    for video_id in known_video_ids:
        # Check if storyboard images exist in S3
        user_id = MOCK_USER_ID
        prefix = f"{user_id}/videos/{video_id}/"
        
        try:
            # List files in the video directory
            files = s3_client.list_files(prefix)
            storyboard_files = [f for f in files if 'beat_' in f and f.endswith('.png')]
            
            if storyboard_files:
                # Sort storyboard files by beat number (beat_00.png, beat_01.png, etc.)
                storyboard_files.sort()
                storyboard_count = len(storyboard_files)
                
                # Create S3 URLs for these files
                storyboard_urls = [f"s3://{s3_client.bucket}/{f}" for f in storyboard_files]
                
                results.append({
                    'video_id': video_id,
                    'created_at': 'N/A (from S3)',
                    'beats': storyboard_count,  # Estimate - will need to recreate spec
                    'storyboard_images': storyboard_count,
                    'spec': None,  # Will need to recreate
                    'storyboard_urls': storyboard_urls,  # Store URLs for direct use
                    'source': 's3'
                })
        except Exception as e:
            print(f"   ⚠️  Error checking S3 for {video_id}: {str(e)}")
            pass  # S3 check failed, skip
    
    return results


def main():
    print("=" * 80)
    print("🎬 Phase 4 Test with Existing Storyboard Images")
    print("=" * 80)
    print()
    
    # Find videos with storyboard images
    print("🔍 Searching for videos with Phase 2 storyboard images...")
    videos = find_videos_with_storyboard()
    
    if videos:
        print(f"✅ Found {len(videos)} video(s) with storyboard images in database")
        print()
        
        # Display available videos
        print("📋 Available Videos:")
        for i, video in enumerate(videos):
            print(f"   {i+1}. Video ID: {video['video_id']}")
            print(f"      Created: {video['created_at']}")
            print(f"      Beats: {video['beats']}")
            print(f"      Storyboard Images: {video['storyboard_images']}")
            print()
    
    # Use first video or specified video ID
    if len(sys.argv) > 1:
        video_id = sys.argv[1]
        selected_video = next((v for v in videos if v['video_id'] == video_id), None)
        
        # Check if we have storyboard images in S3 for this video ID
        user_id = MOCK_USER_ID
        prefix = f"{user_id}/videos/{video_id}/"
        s3_storyboard_files = []
        try:
            files = s3_client.list_files(prefix)
            s3_storyboard_files = sorted([f for f in files if 'beat_' in f and f.endswith('.png')])
        except Exception as e:
            pass
        
        if not selected_video and not s3_storyboard_files:
            # If not in database and no S3 files, need to recreate everything
            print(f"⚠️  Video ID {video_id} not found in database or S3")
            print("   Please provide a prompt to recreate Phase 1:")
            print(f"   python {sys.argv[0]} {video_id} \"<prompt>\" <model>")
            return 1
        
        if s3_storyboard_files and not selected_video:
            # Found storyboard images in S3 - use them directly!
            print(f"✅ Found {len(s3_storyboard_files)} storyboard images in S3 for {video_id}")
            print("   Using existing storyboard images (skipping Phase 2)")
            print()
            
            # Get prompt and model from command line
            if len(sys.argv) < 3:
                print("   Please provide a prompt to recreate Phase 1 spec:")
                print(f"   python {sys.argv[0]} {video_id} \"<prompt>\" <model>")
                return 1
            
            prompt = sys.argv[2]
            selected_model = sys.argv[3] if len(sys.argv) > 3 else 'veo_fast'
            print(f"🎥 Using model: {selected_model}")
            print()
            
            # Recreate Phase 1 to get the spec structure
            from app.phases.phase1_validate.task_intelligent import plan_video_intelligent
            result1 = plan_video_intelligent.apply(args=[video_id, prompt, 0.5]).result
            if result1.get('status') != 'success':
                print(f"❌ Failed to recreate Phase 1: {result1.get('error_message')}")
                return 1
            spec = result1['output_data']['spec']
            
            # CRITICAL: Set model in spec
            spec['model'] = selected_model
            print(f"✅ Model '{selected_model}' set in spec")
            
            # Use existing storyboard images from S3 - add them to beats
            beats = spec.get('beats', [])
            storyboard_urls = [f"s3://{s3_client.bucket}/{f}" for f in s3_storyboard_files]
            
            print(f"📸 Adding {len(storyboard_urls)} existing storyboard images to beats:")
            for i, (beat, image_url) in enumerate(zip(beats, storyboard_urls)):
                beat['image_url'] = image_url
                print(f"   Beat {i} ({beat.get('beat_id')}): {image_url[:80]}...")
            
            # Ensure we have enough beats for the images
            if len(beats) < len(storyboard_urls):
                print(f"⚠️  Warning: More storyboard images ({len(storyboard_urls)}) than beats ({len(beats)})")
                print(f"   Using first {len(beats)} images")
            elif len(beats) > len(storyboard_urls):
                print(f"⚠️  Warning: More beats ({len(beats)}) than storyboard images ({len(storyboard_urls)})")
                print(f"   Some beats will not have images")
            
        elif not selected_video:
            # Not in database, no S3 files - need to recreate Phase 1 & 2
            print(f"⚠️  Video ID {video_id} not in database, will recreate Phase 1 & 2...")
            if len(sys.argv) < 3:
                print("   Please provide a prompt to recreate Phase 1:")
                print(f"   python {sys.argv[0]} {video_id} \"<prompt>\" <model>")
                return 1
            prompt = sys.argv[2]
            selected_model = sys.argv[3] if len(sys.argv) > 3 else 'veo_fast'
            print(f"🎥 Using model: {selected_model}")
            print()
            
            # Recreate Phase 1
            from app.phases.phase1_validate.task_intelligent import plan_video_intelligent
            result1 = plan_video_intelligent.apply(args=[video_id, prompt, 0.5]).result
            if result1.get('status') != 'success':
                print(f"❌ Failed to recreate Phase 1: {result1.get('error_message')}")
                return 1
            spec = result1['output_data']['spec']
            
            # CRITICAL: Set model in spec before Phase 2
            spec['model'] = selected_model
            print(f"✅ Model '{selected_model}' set in spec")
            
            # Now run Phase 2 to get storyboard images
            from app.phases.phase2_storyboard.task import _generate_storyboard_impl
            result2 = _generate_storyboard_impl(video_id, spec, MOCK_USER_ID)
            if result2.get('status') != 'success':
                print(f"❌ Failed to generate storyboard: {result2.get('error_message')}")
                return 1
            spec = result2['output_data']['spec']
            
            # CRITICAL: Ensure model is still in spec after Phase 2
            if 'model' not in spec or spec.get('model') != selected_model:
                spec['model'] = selected_model
                print(f"✅ Model '{selected_model}' preserved in spec after Phase 2")
        else:
            # Found in database - use it
            video_id = selected_video['video_id']
            spec = selected_video['spec']
            
            # If spec is None (from S3 source), we need to recreate it
            if spec is None:
                if len(sys.argv) < 3:
                    print("⚠️  Video found in S3 but spec is missing")
                    print("   Please provide a prompt to recreate Phase 1 spec:")
                    print(f"   python {sys.argv[0]} {video_id} \"<prompt>\" <model>")
                    return 1
                prompt = sys.argv[2]
                selected_model = sys.argv[3] if len(sys.argv) > 3 else 'veo_fast'
                print(f"🎥 Using model: {selected_model}")
                print()
                
                # Recreate Phase 1 to get spec structure
                from app.phases.phase1_validate.task_intelligent import plan_video_intelligent
                result1 = plan_video_intelligent.apply(args=[video_id, prompt, 0.5]).result
                if result1.get('status') != 'success':
                    print(f"❌ Failed to recreate Phase 1: {result1.get('error_message')}")
                    return 1
                spec = result1['output_data']['spec']
                spec['model'] = selected_model
                
                # Get storyboard URLs from selected_video if available
                if 'storyboard_urls' in selected_video:
                    storyboard_urls = selected_video['storyboard_urls']
                    beats = spec.get('beats', [])
                    print(f"📸 Adding {len(storyboard_urls)} existing storyboard images to beats:")
                    for i, (beat, image_url) in enumerate(zip(beats, storyboard_urls)):
                        beat['image_url'] = image_url
                        print(f"   Beat {i} ({beat.get('beat_id')}): {image_url[:80]}...")
    else:
        if not videos:
            print("❌ No videos found with storyboard images")
            print("   Please run Phase 2 tests first or provide a video ID:")
            print(f"   python {sys.argv[0]} <video_id> \"<prompt>\" <model>")
            return 1
        selected_video = videos[0]
        print(f"📌 Using first video: {selected_video['video_id']}")
        print()
        video_id = selected_video['video_id']
        spec = selected_video['spec']
        
        # If spec is None (from S3 source), need to recreate
        if spec is None:
            print("⚠️  Video found in S3 but spec is missing")
            print("   Please provide a prompt to recreate Phase 1 spec:")
            print(f"   python {sys.argv[0]} {video_id} \"<prompt>\" <model>")
            return 1
    
    # Ensure spec is valid
    if spec is None:
        print("❌ Spec is None - cannot proceed")
        return 1
    
    beats = spec.get('beats', [])
    
    # Extract storyboard URLs from beats
    storyboard_urls = []
    for beat in beats:
        image_url = beat.get('image_url')
        if image_url:
            storyboard_urls.append(image_url)
    
    print(f"📸 Found {len(storyboard_urls)} storyboard images:")
    for i, url in enumerate(storyboard_urls):
        print(f"   {i+1}. {url[:80]}...")
    print()
    
    # Check if model is specified in spec
    model = spec.get('model')
    if not model:
        # If model not in spec, ask user or use default
        if len(sys.argv) > 3:
            model = sys.argv[3]
        else:
            print("⚠️  No model specified in spec!")
            print("   Please provide model as 3rd argument:")
            print(f"   python {sys.argv[0]} <video_id> \"<prompt>\" <model>")
            print("   Example: python test_phase4_with_storyboard.py <id> \"prompt\" veo_fast")
            return 1
    
    print(f"🎥 Model: {model}")
    print()
    
    # Verify model is set correctly
    if model not in ['veo_fast', 'veo', 'hailuo', 'kling', 'pixverse', 'wan', 'zeroscope', 'animatediff', 'runway', 'seedance', 'hailuo_23', 'sora', 'runway_gen4_turbo', 'wan_25_t2v', 'wan_25_i2v']:
        print(f"⚠️  Warning: Model '{model}' might not be valid. Continuing anyway...")
        print()
    
    # Prepare reference URLs (empty since we're using storyboard images)
    reference_urls = {
        'style_guide_url': None,
        'product_reference_url': None,
        'uploaded_assets': []
    }
    
    # Use storyboard URLs as animatic URLs for Phase 4
    animatic_urls = storyboard_urls
    
    print("=" * 80)
    print("🎬 Phase 4: Chunk Generation")
    print("=" * 80)
    print()
    
    try:
        # Run Phase 4
        print(f"🚀 Starting Phase 4 for video {video_id}...")
        print(f"   - Using {len(animatic_urls)} storyboard images")
        print(f"   - Model: {model}")
        print()
        
        # Import here to avoid circular import
        from app.phases.phase4_chunks.task import generate_chunks
        result4 = generate_chunks.apply(args=[video_id, spec, animatic_urls, reference_urls, MOCK_USER_ID]).result
        
        if isinstance(result4, Exception):
            print(f"❌ Phase 4 failed: {result4}")
            import traceback
            traceback.print_exc()
            return 1
        
        if result4.get('status') != "success":
            print(f"❌ Phase 4 failed: {result4.get('error_message', 'Unknown error')}")
            return 1
        
        # Display results
        output_data = result4.get('output_data', {})
        chunk_urls = output_data.get('chunk_urls', [])
        stitched_url = output_data.get('stitched_video_url')
        
        print(f"✅ Phase 4 Complete!")
        print(f"   - Chunks Generated: {len(chunk_urls)}")
        print(f"   - Cost: ${result4.get('cost_usd', 0):.4f}")
        print(f"   - Duration: {result4.get('duration_seconds', 0):.2f}s")
        print()
        
        if chunk_urls:
            print("📹 Generated Chunks:")
            for i, url in enumerate(chunk_urls):
                print(f"   Chunk {i}: {url[:80]}...")
            print()
        
        if stitched_url:
            print(f"🎬 Stitched Video:")
            print(f"   {stitched_url[:80]}...")
            print()
        
        print("=" * 80)
        print("🎉 SUCCESS! Phase 4 completed using existing storyboard images!")
        print("=" * 80)
        return 0
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

