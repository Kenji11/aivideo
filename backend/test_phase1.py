#!/usr/bin/env python3
"""
Manual test script for Phase 1 validation service.
Tests prompt validation with different types of video requests.
"""

import sys
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.phases.phase1_validate.service import PromptValidationService


def test_validation():
    """Test the validation service with various prompts"""
    
    # Initialize service
    service = PromptValidationService()
    
    # Test prompts
    test_prompts = [
        {
            "name": "Luxury Watch Commercial",
            "prompt": "Create a cinematic luxury watch commercial. Show the watch in dramatic lighting with elegant close-ups. Use sophisticated orchestral music. The watch is called 'Chronos Elite' and it's a premium timepiece."
        },
        {
            "name": "Sports Shoes Ad",
            "prompt": "Make an energetic lifestyle ad for 'AeroRun Pro' running shoes. Show someone jogging in a beautiful park, wearing the shoes. Use upbeat music and vibrant colors. Focus on the comfort and performance."
        },
        {
            "name": "Product Launch Announcement",
            "prompt": "Create a dramatic announcement video for the launch of 'TechWave Pro' smartphone. Use cinematic visuals with epic music. Show the phone from multiple angles with emphasis on its sleek design."
        }
    ]
    
    print("=" * 70)
    print("PHASE 1 VALIDATION TEST")
    print("=" * 70)
    print()
    
    for i, test in enumerate(test_prompts, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {test['name']}")
        print(f"{'='*70}")
        print(f"Prompt: {test['prompt']}")
        print()
        
        try:
            # Validate and extract
            spec = service.validate_and_extract(test['prompt'], assets=[])
            
            # Print results
            print(f"✅ SUCCESS!")
            print(f"Template: {spec.get('template', 'N/A')}")
            print(f"Product: {spec.get('product', {}).get('name', 'N/A')}")
            print(f"Duration: {spec.get('duration', 'N/A')}s")
            print(f"Number of beats: {len(spec.get('beats', []))}")
            print(f"Style aesthetic: {spec.get('style', {}).get('aesthetic', 'N/A')}")
            print(f"Audio mood: {spec.get('audio', {}).get('mood', 'N/A')}")
            
            # Save spec to file
            output_file = f"test_spec_{i}.json"
            with open(output_file, 'w') as f:
                json.dump(spec, f, indent=2)
            print(f"\n💾 Saved spec to: {output_file}")
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_validation()

