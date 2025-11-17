#!/usr/bin/env python3
"""
Test Phase 2 Storyboard Generation

This script tests Phase 2 storyboard generation that:
- Generates one FLUX Dev image per beat
- Uploads images to S3
- Adds image_url to each beat in the spec

Usage:
    python scripts/test_phase2_storyboard.py
    python scripts/test_phase2_storyboard.py phase1_output_b68830e2-a99e-4900-837e-f5849bbaf082.json
    python scripts/test_phase2_storyboard.py --video-id <uuid> --user-id <uuid>
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

from app.phases.phase2_storyboard.task import _generate_storyboard_impl
from app.common.constants import MOCK_USER_ID
from app.services.s3 import s3_client


def find_phase1_output_files():
    """Find all Phase 1 output JSON files in scripts directory."""
    scripts_dir = Path(__file__).parent
    return list(scripts_dir.glob("phase1_output_*.json"))


def load_phase1_spec(file_path: Optional[Path] = None) -> dict:
    """
    Load Phase 1 spec from file or prompt user to select one.
    
    Args:
        file_path: Optional path to Phase 1 output JSON file
        
    Returns:
        Spec dictionary from Phase 1
    """
    scripts_dir = Path(__file__).parent
    
    # If file path provided, use it
    if file_path:
        if not file_path.exists():
            raise FileNotFoundError(f"Phase 1 output file not found: {file_path}")
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
    
    # Find all Phase 1 output files
    phase1_files = find_phase1_output_files()
    
    if not phase1_files:
        raise FileNotFoundError(
            "No Phase 1 output files found. "
            "Run test_phase1_intelligent.py first to generate a spec."
        )
    
    # Prompt user to select a file
    print("📁 Available Phase 1 output files:")
    for i, file_path in enumerate(phase1_files, 1):
        print(f"  {i}. {file_path.name}")
    print()
    
    while True:
        try:
            choice = input(f"Select file (1-{len(phase1_files)}) or press Enter for first: ").strip()
            if not choice:
                choice = "1"
            idx = int(choice) - 1
            if 0 <= idx < len(phase1_files):
                selected_file = phase1_files[idx]
                print(f"✅ Selected: {selected_file.name}")
                with open(selected_file, 'r') as f:
                    return json.load(f)
            else:
                print(f"⚠️  Invalid choice. Enter 1-{len(phase1_files)}")
        except ValueError:
            print("⚠️  Please enter a number")
        except KeyboardInterrupt:
            print("\n❌ Cancelled")
            sys.exit(1)


def test_phase2_storyboard(
    spec: Optional[dict] = None,
    video_id: Optional[str] = None,
    user_id: Optional[str] = None
):
    """
    Test Phase 2 storyboard generation without Celery.
    
    Args:
        spec: Video specification from Phase 1 (if None, will load from file)
        video_id: Video ID (if None, will generate new UUID)
        user_id: User ID (if None, will use MOCK_USER_ID)
    """
    
    print("=" * 80)
    print("🎨 Phase 2 Storyboard Generation Test")
    print("=" * 80)
    print()
    
    # Load spec if not provided
    if spec is None:
        spec = load_phase1_spec()
    
    # Generate or use provided IDs
    if video_id is None:
        # Try to extract from spec if it has video_id, otherwise generate new
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
    
    print("📋 INPUTS")
    print("=" * 80)
    print(f"Video ID: {video_id}")
    print(f"User ID: {user_id}")
    print(f"Template: {spec.get('template', 'N/A')}")
    print(f"Duration: {spec.get('duration', 'N/A')}s")
    print(f"Beats: {len(spec.get('beats', []))}")
    print()
    
    # Display beats
    print("📊 BEATS TO GENERATE")
    print("=" * 80)
    for i, beat in enumerate(spec.get('beats', []), 1):
        print(f"  {i}. [{beat.get('start', 0)}s-{beat.get('start', 0) + beat.get('duration', 0)}s] "
              f"{beat.get('beat_id', 'unknown')} ({beat.get('duration', 0)}s)")
        print(f"     Shot: {beat.get('shot_type', 'N/A')} | Action: {beat.get('action', 'N/A')}")
    print()
    
    try:
        print("🎨 Generating storyboard images...")
        print(f"   Model: FLUX Dev (black-forest-labs/flux-dev)")
        print(f"   Cost per image: $0.025")
        print(f"   Total images: {len(spec.get('beats', []))}")
        print(f"   Estimated cost: ${len(spec.get('beats', [])) * 0.025:.4f}")
        print()
        
        # Call Phase 2 implementation directly (bypasses Celery wrapper)
        result = _generate_storyboard_impl(video_id, spec, user_id)
        
        print("=" * 80)
        print("📊 PHASE 2 OUTPUT")
        print("=" * 80)
        print(f"Status: {result.get('status', 'unknown')}")
        print(f"Phase: {result.get('phase', 'unknown')}")
        print(f"Cost: ${result.get('cost_usd', 0):.4f}")
        print(f"Duration: {result.get('duration_seconds', 0):.2f}s")
        print()
        
        if result.get('status') == 'success':
            output_data = result.get('output_data', {})
            storyboard_images = output_data.get('storyboard_images', [])
            updated_spec = output_data.get('spec', {})
            
            print(f"✅ Generated {len(storyboard_images)} storyboard images:")
            print()
            print("📦 S3 STORAGE PATHS")
            print("=" * 80)
            print(f"S3 Bucket: {s3_client.bucket}")
            print(f"Base Path: {user_id}/videos/{video_id}/")
            print(f"Full S3 Path: s3://{s3_client.bucket}/{user_id}/videos/{video_id}/")
            print()
            
            for i, img_info in enumerate(storyboard_images, 1):
                beat_index = img_info.get('beat_index', '?')
                beat_id = img_info.get('beat_id', 'unknown')
                image_url = img_info.get('image_url', 'N/A')
                
                # Extract S3 key from URL
                s3_key = image_url
                if 's3://' in image_url:
                    # Extract key after bucket name: s3://bucket/key
                    s3_key = image_url.replace(f's3://{s3_client.bucket}/', '')
                elif 'amazonaws.com' in image_url:
                    # Extract key from https URL
                    try:
                        from urllib.parse import urlparse
                        parsed = urlparse(image_url)
                        s3_key = parsed.path.lstrip('/')
                    except:
                        pass
                
                filename = f"beat_{beat_index:02d}.png"
                full_s3_path = f"s3://{s3_client.bucket}/{user_id}/videos/{video_id}/{filename}"
                
                print(f"  {i}. Beat {beat_index}: {beat_id}")
                print(f"     Filename: {filename}")
                print(f"     S3 Key: {s3_key}")
                print(f"     Full S3 Path: {full_s3_path}")
                print(f"     Full URL: {image_url}")
                print(f"     Shot Type: {img_info.get('shot_type', 'N/A')}")
                print(f"     Duration: {img_info.get('duration', 'N/A')}s")
                print()
            
            # Verify image_urls were added to beats
            print("✅ Verifying image_urls in spec beats...")
            all_have_urls = True
            for i, beat in enumerate(updated_spec.get('beats', []), 1):
                if 'image_url' in beat:
                    print(f"  ✓ Beat {i}: {beat.get('beat_id')} has image_url")
                else:
                    print(f"  ✗ Beat {i}: {beat.get('beat_id')} missing image_url")
                    all_have_urls = False
            
            if all_have_urls:
                print("  ✅ All beats have image_urls!")
            print()
            
            # Save updated spec to file
            output_file = Path(__file__).parent / f"phase2_output_{video_id}.json"
            with open(output_file, 'w') as f:
                json.dump({
                    "video_id": video_id,
                    "user_id": user_id,
                    "result": result,
                    "updated_spec": updated_spec
                }, f, indent=2)
            
            print("=" * 80)
            print("✅ Phase 2 Test: SUCCESS!")
            print("=" * 80)
            print(f"Video ID: {video_id}")
            print(f"User ID: {user_id}")
            print(f"S3 Bucket: {s3_client.bucket}")
            print(f"S3 Base Path: {user_id}/videos/{video_id}/")
            print(f"Full S3 Path: s3://{s3_client.bucket}/{user_id}/videos/{video_id}/")
            print(f"Output saved to: {output_file}")
            print(f"Total Images: {len(storyboard_images)}")
            print(f"Total Cost: ${result.get('cost_usd', 0):.4f}")
            print()
            print("🔍 To find images in S3:")
            print(f"   Bucket: {s3_client.bucket}")
            print(f"   Path: {user_id}/videos/{video_id}/")
            print(f"   Files: beat_00.png, beat_01.png, ... beat_{len(storyboard_images)-1:02d}.png")
            print()
            print("📋 Summary:")
            print(f"   - Video ID: {video_id}")
            print(f"   - User ID: {user_id}")
            print(f"   - Images generated: {len(storyboard_images)}")
            print(f"   - All images saved to: s3://{s3_client.bucket}/{user_id}/videos/{video_id}/")
            print("=" * 80)
            
            return 0
        else:
            error_msg = result.get('error_message', 'Unknown error')
            print("=" * 80)
            print("❌ Phase 2 Test: FAILED")
            print("=" * 80)
            print(f"Error: {error_msg}")
            print("=" * 80)
            return 1
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Phase 2 Test: FAILED")
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
    
    # Get video_id and user_id from command line if provided
    video_id = None
    user_id = None
    
    if '--video-id' in sys.argv:
        idx = sys.argv.index('--video-id')
        if idx + 1 < len(sys.argv):
            video_id = sys.argv[idx + 1]
    
    if '--user-id' in sys.argv:
        idx = sys.argv.index('--user-id')
        if idx + 1 < len(sys.argv):
            user_id = sys.argv[idx + 1]
    
    exit_code = test_phase2_storyboard(video_id=video_id, user_id=user_id)
    sys.exit(exit_code)

