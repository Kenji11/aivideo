#!/usr/bin/env python3
"""
Test Phase 4 Storyboard Chunk Generation

This script tests Phase 4 chunk generation with storyboard logic that:
- Uses storyboard images at beat boundaries
- Uses last-frame continuation only when beats span multiple chunks
- Generates independent chunks for beats that only need one chunk

Usage:
    python scripts/test_phase4_storyboard.py
    python scripts/test_phase4_storyboard.py phase2_output_55610cec-c66b-458b-a1e4-01c5eca72827.json
    python scripts/test_phase4_storyboard.py --video-id <uuid> --user-id <uuid> --model hailuo
"""

import sys
import os
import json
import uuid
from pathlib import Path
from typing import Optional

# Load .env if exists
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}")
    print("   Make sure environment variables are set")

# Override database URL for local testing (connects to Docker Compose postgres on localhost)
os.environ['DATABASE_URL'] = 'postgresql://dev:devpass@localhost:5434/videogen'

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.phases.phase4_chunks_storyboard.service import ChunkGenerationService
from app.phases.phase4_chunks_storyboard.stitcher import VideoStitcher
from app.common.constants import MOCK_USER_ID
from app.services.s3 import s3_client


def find_phase2_output_files():
    """Find all Phase 2 output JSON files in scripts directory."""
    scripts_dir = Path(__file__).parent
    return list(scripts_dir.glob("phase2_output_*.json"))


def load_phase2_output(file_path: Optional[Path] = None) -> dict:
    """
    Load Phase 2 output from file or prompt user to select one.
    
    Args:
        file_path: Optional path to Phase 2 output JSON file
        
    Returns:
        Dictionary with video_id, user_id, result, and updated_spec
    """
    scripts_dir = Path(__file__).parent
    
    # If file path provided, use it
    if file_path:
        if not file_path.exists():
            raise FileNotFoundError(f"Phase 2 output file not found: {file_path}")
        with open(file_path, 'r') as f:
            return json.load(f)
    
    # Check command line arguments
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        file_path = scripts_dir / sys.argv[1]
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    # Find all Phase 2 output files
    phase2_files = find_phase2_output_files()
    
    if not phase2_files:
        raise FileNotFoundError(
            "No Phase 2 output files found. "
            "Run test_phase2_storyboard.py first to generate storyboard images."
        )
    
    # Prompt user to select a file
    print("📁 Available Phase 2 output files:")
    for i, file_path in enumerate(phase2_files, 1):
        print(f"  {i}. {file_path.name}")
    print()
    
    while True:
        try:
            choice = input(f"Select file (1-{len(phase2_files)}) or press Enter for first: ").strip()
            if not choice:
                choice = "1"
            idx = int(choice) - 1
            if 0 <= idx < len(phase2_files):
                selected_file = phase2_files[idx]
                print(f"✅ Selected: {selected_file.name}")
                with open(selected_file, 'r') as f:
                    return json.load(f)
            else:
                print(f"⚠️  Invalid choice. Enter 1-{len(phase2_files)}")
        except ValueError:
            print("⚠️  Please enter a number")
        except KeyboardInterrupt:
            print("\n❌ Cancelled")
            sys.exit(1)


def test_phase4_storyboard(
    spec: Optional[dict] = None,
    video_id: Optional[str] = None,
    user_id: Optional[str] = None,
    model: Optional[str] = None
):
    """
    Test Phase 4 storyboard chunk generation without Celery.
    
    Args:
        spec: Video specification from Phase 2 (with storyboard images in beats)
        video_id: Video ID (if None, will extract from Phase 2 output or generate new)
        user_id: User ID (if None, will extract from Phase 2 output or use MOCK_USER_ID)
        model: Video generation model (default: 'hailuo')
    """
    
    print("=" * 80)
    print("🎬 Phase 4 Storyboard Chunk Generation Test")
    print("=" * 80)
    print()
    
    # Load Phase 2 output if spec not provided
    if spec is None:
        phase2_output = load_phase2_output()
        spec = phase2_output.get('updated_spec') or phase2_output.get('result', {}).get('output_data', {}).get('spec')
        if video_id is None:
            video_id = phase2_output.get('video_id')
        if user_id is None:
            user_id = phase2_output.get('user_id')
    
    # Generate or use provided IDs
    if video_id is None:
        video_id = str(uuid.uuid4())
    
    if user_id is None:
        # Check command line for --user-id
        if '--user-id' in sys.argv:
            idx = sys.argv.index('--user-id')
            if idx + 1 < len(sys.argv):
                user_id = sys.argv[idx + 1]
            else:
                user_id = MOCK_USER_ID
        else:
            user_id = MOCK_USER_ID
    
    # Check command line for --video-id
    if '--video-id' in sys.argv:
        idx = sys.argv.index('--video-id')
        if idx + 1 < len(sys.argv):
            video_id = sys.argv[idx + 1]
    
    # Get model from command line or use default
    if model is None:
        if '--model' in sys.argv:
            idx = sys.argv.index('--model')
            if idx + 1 < len(sys.argv):
                model = sys.argv[idx + 1]
            else:
                model = 'hailuo'
        else:
            model = 'hailuo'
    
    # Add model to spec
    spec['model'] = model
    
    # Check for storyboard images
    beats = spec.get('beats', [])
    storyboard_images_count = sum(1 for beat in beats if beat.get('image_url'))
    
    if storyboard_images_count == 0:
        print("⚠️  WARNING: No storyboard images found in spec!")
        print("   Phase 4 storyboard logic requires storyboard images from Phase 2.")
        print("   This test will likely fail.")
        print()
    
    # Create reference URLs (Phase 3 is optional for storyboard mode)
    reference_urls = {
        'style_guide_url': None,
        'product_reference_url': None,
        'uploaded_assets': []
    }
    
    # Empty animatic URLs (not used in storyboard mode)
    animatic_urls = []
    
    print("📋 INPUTS")
    print("=" * 80)
    print(f"Video ID: {video_id}")
    print(f"User ID: {user_id}")
    print(f"Model: {model}")
    print(f"Duration: {spec.get('duration', 'N/A')}s")
    print(f"Beats: {len(beats)}")
    print(f"Storyboard Images: {storyboard_images_count}/{len(beats)}")
    print()
    
    # Display beat-to-chunk mapping info
    print("📊 BEAT-TO-CHUNK MAPPING")
    print("=" * 80)
    from app.phases.phase4_chunks_storyboard.model_config import get_default_model, get_model_config
    try:
        model_config = get_model_config(model)
    except Exception:
        model_config = get_default_model()
        model = model_config.get('name', 'hailuo')
    
    actual_chunk_duration = model_config.get('actual_chunk_duration', 5.0)
    duration = spec.get('duration', 30)
    import math
    chunk_count = math.ceil(duration / actual_chunk_duration)
    
    print(f"Model: {model_config.get('name', 'unknown')}")
    print(f"Actual Chunk Duration: {actual_chunk_duration}s")
    print(f"Video Duration: {duration}s")
    print(f"Calculated Chunks: {chunk_count}")
    print()
    
    # Calculate beat-to-chunk mapping
    from app.phases.phase4_chunks_storyboard.chunk_generator import calculate_beat_to_chunk_mapping
    beat_to_chunk_map = calculate_beat_to_chunk_mapping(beats, actual_chunk_duration)
    
    print("Beat Boundaries → Chunks:")
    for chunk_idx, beat_idx in sorted(beat_to_chunk_map.items()):
        beat = beats[beat_idx] if beat_idx < len(beats) else None
        beat_id = beat.get('beat_id', f'beat_{beat_idx}') if beat else 'unknown'
        print(f"  Chunk {chunk_idx} starts Beat {beat_idx} ({beat_id})")
    print()
    
    try:
        print("🎬 Generating video chunks...")
        print(f"   Model: {model_config.get('name', 'unknown')} ({model_config.get('replicate_model', 'unknown')})")
        print(f"   Cost per chunk: ${model_config.get('cost_per_generation', 0):.4f}")
        print(f"   Estimated chunks: {chunk_count}")
        print(f"   Estimated cost: ${chunk_count * model_config.get('cost_per_generation', 0):.4f}")
        print()
        
        # Initialize services
        chunk_service = ChunkGenerationService()
        stitcher = VideoStitcher()
        
        # Generate chunks
        print("🔨 Generating chunks with storyboard logic...")
        chunk_results = chunk_service.generate_all_chunks(
            video_id=video_id,
            spec=spec,
            animatic_urls=animatic_urls,
            reference_urls=reference_urls,
            user_id=user_id
        )
        
        chunk_urls = chunk_results['chunk_urls']
        total_cost = chunk_results['total_cost']
        
        print()
        print("=" * 80)
        print("📊 CHUNK GENERATION RESULTS")
        print("=" * 80)
        print(f"Total Chunks Generated: {len(chunk_urls)}/{chunk_count}")
        print(f"Total Cost: ${total_cost:.4f}")
        print()
        
        print("📦 CHUNK S3 PATHS")
        print("=" * 80)
        print(f"S3 Bucket: {s3_client.bucket}")
        print(f"Base Path: {user_id}/videos/{video_id}/")
        print()
        
        for i, chunk_url in enumerate(chunk_urls):
            if chunk_url:
                # Extract S3 key
                s3_key = chunk_url
                if 's3://' in chunk_url:
                    s3_key = chunk_url.replace(f's3://{s3_client.bucket}/', '')
                elif 'amazonaws.com' in chunk_url:
                    from urllib.parse import urlparse
                    parsed = urlparse(chunk_url)
                    s3_key = parsed.path.lstrip('/')
                
                print(f"  Chunk {i}: {chunk_url[:80]}...")
                print(f"    S3 Key: {s3_key}")
            else:
                print(f"  Chunk {i}: ❌ Failed")
        print()
        
        # Stitch chunks together
        print("🔗 Stitching chunks together...")
        transitions = spec.get('transitions', [])
        stitched_video_url = stitcher.stitch_with_transitions(
            video_id=video_id,
            chunk_urls=chunk_urls,
            transitions=transitions,
            user_id=user_id
        )
        
        print()
        print("=" * 80)
        print("✅ Phase 4 Storyboard Test: SUCCESS!")
        print("=" * 80)
        print(f"Video ID: {video_id}")
        print(f"User ID: {user_id}")
        print(f"Model: {model}")
        print(f"Chunks Generated: {len(chunk_urls)}")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"Stitched Video: {stitched_video_url}")
        print(f"S3 Bucket: {s3_client.bucket}")
        print(f"S3 Base Path: {user_id}/videos/{video_id}/")
        print()
        
        # Save output to file
        output_file = Path(__file__).parent / f"phase4_storyboard_output_{video_id}.json"
        with open(output_file, 'w') as f:
            json.dump({
                "video_id": video_id,
                "user_id": user_id,
                "model": model,
                "chunk_count": len(chunk_urls),
                "total_cost": total_cost,
                "chunk_urls": chunk_urls,
                "stitched_video_url": stitched_video_url,
                "beat_to_chunk_map": beat_to_chunk_map
            }, f, indent=2)
        
        print(f"Output saved to: {output_file}")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Phase 4 Storyboard Test: FAILED")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print()
        print("Full Traceback:")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return 1


if __name__ == "__main__":
    # Parse arguments
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    # Get video_id, user_id, and model from command line if provided
    video_id = None
    user_id = None
    model = None
    
    if '--video-id' in sys.argv:
        idx = sys.argv.index('--video-id')
        if idx + 1 < len(sys.argv):
            video_id = sys.argv[idx + 1]
    
    if '--user-id' in sys.argv:
        idx = sys.argv.index('--user-id')
        if idx + 1 < len(sys.argv):
            user_id = sys.argv[idx + 1]
    
    if '--model' in sys.argv:
        idx = sys.argv.index('--model')
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]
    
    exit_code = test_phase4_storyboard(video_id=video_id, user_id=user_id, model=model)
    sys.exit(exit_code)

