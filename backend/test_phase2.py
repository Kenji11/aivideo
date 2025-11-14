#!/usr/bin/env python3
"""
Manual test script for Phase 2: Animatic Generation

This script tests:
1. Prompt generation for different beat types
2. Full animatic generation (if test_spec_1.json exists from Phase 1)
"""

import sys
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.phases.phase2_animatic.service import AnimaticGenerationService
from app.phases.phase2_animatic.prompts import generate_animatic_prompt


def test_prompt_generation():
    """Test prompt generation for different beat types"""
    print("\n" + "="*60)
    print("TEST: Prompt Generation")
    print("="*60)
    
    # Define test beats with different action types
    test_beats = [
        {
            "name": "hero_shot",
            "shot_type": "close_up",
            "action": "product_reveal"
        },
        {
            "name": "lifestyle_context",
            "shot_type": "medium",
            "action": "usage_scenario"
        },
        {
            "name": "brand_moment",
            "shot_type": "wide",
            "action": "brand_story"
        }
    ]
    
    # Define style dictionary
    style = {
        "aesthetic": "luxury",
        "color_palette": ["gold", "black", "white"],
        "mood": "elegant",
        "lighting": "dramatic"
    }
    
    # Loop through test beats and generate prompts
    for beat in test_beats:
        prompt = generate_animatic_prompt(beat, style)
        print(f"\nBeat: {beat['name']}")
        print(f"Action: {beat['action']}")
        print(f"Generated Prompt: {prompt}")


def test_full_generation():
    """Test full animatic generation using Phase 1 spec"""
    print("\n" + "="*60)
    print("TEST: Full Animatic Generation")
    print("="*60)
    
    # Try to load test_spec_1.json from Phase 1
    test_spec_path = Path(__file__).parent / "test_spec_1.json"
    
    try:
        with open(test_spec_path, 'r') as f:
            spec = json.load(f)
    except FileNotFoundError:
        print(f"\n⚠️  Warning: {test_spec_path} not found.")
        print("   Run Phase 1 test first to generate test_spec_1.json")
        print("   Skipping full generation test...")
        return
    
    print(f"\n✓ Loaded spec from {test_spec_path}")
    print(f"  Template: {spec.get('template', 'unknown')}")
    print(f"  Beats: {len(spec.get('beats', []))}")
    
    # Initialize service
    service = AnimaticGenerationService()
    
    # Define test video ID
    test_video_id = "test_video_phase2"
    
    try:
        # Generate frames
        frame_urls = service.generate_frames(test_video_id, spec)
        
        print(f"\n✓ Successfully generated {len(frame_urls)} frames")
        print(f"  Total cost: ${service.total_cost:.4f}")
        print(f"\nFrame URLs:")
        for i, url in enumerate(frame_urls):
            print(f"  Frame {i+1}: {url}")
        
        # Save result
        result = {
            "video_id": test_video_id,
            "frame_count": len(frame_urls),
            "frame_urls": frame_urls,
            "cost_usd": service.total_cost,
            "spec_template": spec.get('template', 'unknown')
        }
        
        result_path = Path(__file__).parent / "test_animatic_result.json"
        with open(result_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✓ Results saved to {result_path}")
        
    except Exception as e:
        print(f"\n✗ Error during generation: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Test prompt generation
    test_prompt_generation()
    
    # Test full generation (commented out by default - uncomment to test with API keys)
    # test_full_generation()

