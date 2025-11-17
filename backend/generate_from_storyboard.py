#!/usr/bin/env python3
"""
Generate a new video using existing storyboard images from another video

Usage:
    python generate_from_storyboard.py <source_video_id> <model> [prompt]
    
Example:
    python generate_from_storyboard.py 75229522-3578-4762-92af-d126c2bfaacc veo_fast "Earbud product"
"""
import sys
import uuid
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.common.constants import MOCK_USER_ID
from app.services.s3 import s3_client


def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_from_storyboard.py <source_video_id> <model> [prompt]")
        print()
        print("Example:")
        print("  python generate_from_storyboard.py 75229522-3578-4762-92af-d126c2bfaacc veo_fast")
        sys.exit(1)
    
    source_video_id = sys.argv[1]
    model = sys.argv[2]
    prompt = sys.argv[3] if len(sys.argv) > 3 else "Video from existing storyboard"
    
    print("=" * 80)
    print("🎬 Generate Video from Existing Storyboard")
    print("=" * 80)
    print()
    print(f"Source Video ID: {source_video_id}")
    print(f"Model: {model}")
    print(f"Prompt: {prompt}")
    print()
    
    # Get storyboard images from source video
    user_id = MOCK_USER_ID
    prefix = f"{user_id}/videos/{source_video_id}/"
    
    print(f"🔍 Looking for storyboard images in S3...")
    try:
        files = s3_client.list_files(prefix)
        storyboard_files = sorted([f for f in files if 'beat_' in f and f.endswith('.png')])
        
        if not storyboard_files:
            print(f"❌ No storyboard images found for video {source_video_id}")
            print(f"   Checked prefix: {prefix}")
            sys.exit(1)
        
        print(f"✅ Found {len(storyboard_files)} storyboard images:")
        storyboard_urls = []
        for f in storyboard_files:
            url = f"s3://{s3_client.bucket}/{f}"
            storyboard_urls.append(url)
            print(f"   - {f}")
        print()
    except Exception as e:
        print(f"❌ Error finding storyboard images: {str(e)}")
        sys.exit(1)
    
    # Get spec from source video or create a basic one
    db = SessionLocal()
    try:
        source_video = db.query(VideoGeneration).filter(VideoGeneration.id == source_video_id).first()
        if source_video and source_video.phase_outputs:
            phase2 = source_video.phase_outputs.get('phase2_storyboard', {})
            if phase2:
                spec = phase2.get('output_data', {}).get('spec', {})
                if spec:
                    print("✅ Found spec from source video")
                    # Update model in spec
                    spec['model'] = model
                    # Ensure beats have image_urls
                    beats = spec.get('beats', [])
                    for i, beat in enumerate(beats):
                        if i < len(storyboard_urls):
                            beat['image_url'] = storyboard_urls[i]
                else:
                    print("⚠️  No spec found, creating basic spec...")
                    spec = create_basic_spec(prompt, model, storyboard_urls)
            else:
                print("⚠️  No Phase 2 output found, creating basic spec...")
                spec = create_basic_spec(prompt, model, storyboard_urls)
        else:
            print("⚠️  Source video not found in database, creating basic spec...")
            spec = create_basic_spec(prompt, model, storyboard_urls)
    finally:
        db.close()
    
    # Create new video record
    new_video_id = str(uuid.uuid4())
    print(f"📹 Creating new video: {new_video_id}")
    print()
    
    db = SessionLocal()
    try:
        new_video = VideoGeneration(
            id=new_video_id,
            user_id=MOCK_USER_ID,
            title=prompt[:50],
            prompt=prompt,
            status=VideoStatus.QUEUED,
            progress=0.0,
            spec=spec
        )
        db.add(new_video)
        db.commit()
        print(f"✅ Video record created")
    finally:
        db.close()
    
    # Prepare for Phase 4
    animatic_urls = storyboard_urls
    reference_urls = {
        'uploaded_assets': [],
        'style_guide_url': None,
        'product_reference_url': None
    }
    
    print()
    print("=" * 80)
    print("🚀 Starting Phase 4: Chunk Generation")
    print("=" * 80)
    print(f"   Video ID: {new_video_id}")
    print(f"   Storyboard Images: {len(animatic_urls)}")
    print(f"   Model: {model}")
    print()
    
    # Update the video record with spec and storyboard images BEFORE running pipeline
    print("📝 Setting up video with existing storyboard images...")
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == new_video_id).first()
        if video:
            # Ensure spec has storyboard URLs in beats
            beats = spec.get('beats', [])
            for i, beat in enumerate(beats):
                if i < len(storyboard_urls):
                    beat['image_url'] = storyboard_urls[i]
            spec['beats'] = beats
            spec['model'] = model
            
            # Store spec and Phase 2 output (so pipeline thinks Phase 2 is done)
            video.spec = spec
            if video.phase_outputs is None:
                video.phase_outputs = {}
            video.phase_outputs['phase2_storyboard'] = {
                'status': 'success',
                'output_data': {
                    'spec': spec
                },
                'cost_usd': 0.0,
                'duration_seconds': 0.0
            }
            
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(video, 'phase_outputs')
            flag_modified(video, 'spec')
            db.commit()
            print(f"✅ Video configured with existing storyboard images")
    finally:
        db.close()
    
    # Now run the pipeline - it will skip Phase 1, 2, 3 and go to Phase 4
    print()
    print("🚀 Starting pipeline (will skip to Phase 4)...")
    print()
    
    try:
        # Import pipeline here to avoid circular import
        from app.orchestrator.pipeline import run_pipeline
        
        # Run pipeline - it will detect Phase 2 is already done and go to Phase 4
        result = run_pipeline.apply(args=[new_video_id, prompt, [], model]).result
        
        if isinstance(result, Exception):
            raise result
        
        print("=" * 80)
        print("✅ Video Generation Complete!")
        print("=" * 80)
        print(f"   Video ID: {new_video_id}")
        if 'stitched_video_url' in result:
            print(f"   Final Video: {result.get('stitched_video_url', 'N/A')}")
        print(f"   Cost: ${result.get('cost_usd', 0):.4f}")
        print()
        print(f"📹 Monitor with: python monitor.py {new_video_id}")
        print()
        
    except Exception as e:
        print(f"❌ Pipeline error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def create_basic_spec(prompt: str, model: str, storyboard_urls: list) -> dict:
    """Create a basic spec structure from prompt and storyboard URLs"""
    beats = []
    current_time = 0.0
    for i, url in enumerate(storyboard_urls):
        beat = {
            'beat_id': f'beat_{i:02d}',
            'start': current_time,
            'duration': 5,  # Default 5 seconds per beat
            'image_url': url,  # Direct link to storyboard image
            'prompt': prompt,
            'prompt_template': prompt,  # For compatibility
            'camera_movement': 'static',
            'shot_type': 'medium',
            'action': 'showcase'
        }
        beats.append(beat)
        current_time += 5  # Increment start time for next beat
    
    total_duration = len(beats) * 5
    
    return {
        'model': model,
        'duration': total_duration,  # Use 'duration' not 'total_duration'
        'beats': beats,
        'style': {
            'aesthetic': 'modern',
            'color_palette': ['#000000', '#ffffff'],
            'mood': 'professional',
            'lighting': 'bright'
        },
        'product': {
            'name': 'Product',
            'category': 'general'
        }
    }

if __name__ == "__main__":
    main()

