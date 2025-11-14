#!/usr/bin/env python3
"""
Simple test script for Phase 1 - Tests templates without any dependencies
"""

import json
import sys
from pathlib import Path

def test_templates():
    """Test that all template files are valid JSON and have required fields"""
    
    print("=" * 70)
    print("PHASE 1 TEMPLATE VALIDATION TEST")
    print("=" * 70)
    print()
    
    templates_dir = Path("app/phases/phase1_validate/templates")
    template_files = ["product_showcase.json", "lifestyle_ad.json", "announcement.json"]
    
    all_passed = True
    
    for template_file in template_files:
        template_path = templates_dir / template_file
        print(f"📝 Testing: {template_file}")
        
        try:
            # Load JSON
            with open(template_path, 'r') as f:
                template = json.load(f)
            
            # Check required fields
            required_fields = ['name', 'description', 'duration', 'fps', 'resolution', 
                             'beats', 'transitions', 'audio', 'color_grading']
            
            missing = [f for f in required_fields if f not in template]
            if missing:
                print(f"   ❌ Missing fields: {missing}")
                all_passed = False
                continue
            
            # Validate beats
            if not template['beats'] or len(template['beats']) < 3:
                print(f"   ❌ Not enough beats (need at least 3)")
                all_passed = False
                continue
            
            # Calculate total duration
            total_duration = sum(beat['duration'] for beat in template['beats'])
            expected_duration = template['duration']
            
            if abs(total_duration - expected_duration) > 1:
                print(f"   ❌ Duration mismatch: {total_duration}s vs {expected_duration}s")
                all_passed = False
                continue
            
            # Success!
            print(f"   ✅ Valid!")
            print(f"      Name: {template['name']}")
            print(f"      Duration: {template['duration']}s")
            print(f"      Beats: {len(template['beats'])}")
            print(f"      Transitions: {len(template['transitions'])}")
            print(f"      Audio: {template['audio']['music_style']}")
            print()
            
        except FileNotFoundError:
            print(f"   ❌ File not found!")
            all_passed = False
        except json.JSONDecodeError as e:
            print(f"   ❌ Invalid JSON: {e}")
            all_passed = False
        except Exception as e:
            print(f"   ❌ Error: {e}")
            all_passed = False
    
    print("=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(test_templates())

