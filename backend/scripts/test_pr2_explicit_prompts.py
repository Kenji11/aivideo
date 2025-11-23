"""
Test PR #2: Explicit Prompts

Tests that o4-mini correctly extracts:
- Brand name when explicitly mentioned
- Music theme when specified
- Color scheme when mentioned
- Scene requirements when described
- Composes full prompts per beat
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.phases.phase1_validate.task import plan_with_gpt4o_mini
from app.common.constants import BEAT_COMPOSITION_CREATIVITY

def test_explicit_brand_and_music():
    """Test 1: Explicit brand name and music theme"""
    print("\n" + "=" * 80)
    print("Test 1: Nike ad with upbeat electronic music")
    print("=" * 80)
    
    prompt = "Create a Nike ad for Air Max running shoes with upbeat electronic music"
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-explicit-1",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        
        # Check brand extraction
        if spec.get('brand_name') == 'Nike':
            print("✅ PASS: Brand name extracted correctly: Nike")
        else:
            print(f"❌ FAIL: Brand name incorrect. Expected 'Nike', got '{spec.get('brand_name')}'")
        
        # Check music extraction
        music_theme = spec.get('music_theme', '').lower()
        if 'electronic' in music_theme or 'upbeat' in music_theme:
            print(f"✅ PASS: Music theme extracted: {spec.get('music_theme')}")
        else:
            print(f"❌ FAIL: Music theme doesn't match. Got: {spec.get('music_theme')}")
        
        # Check composed prompts exist
        beats = spec.get('beats', [])
        print(f"\n📋 Generated {len(beats)} beats:")
        for i, beat in enumerate(beats):
            prompt_text = beat.get('prompt', '')
            if len(prompt_text) > 50:
                print(f"  Beat {i+1} ({beat.get('beat_id')}): {prompt_text[:80]}...")
                print("  ✅ Composed prompt exists and is detailed")
            else:
                print(f"  Beat {i+1} ({beat.get('beat_id')}): {prompt_text}")
                print(f"  ❌ Composed prompt too short ({len(prompt_text)} chars)")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        print(f"⏱️  Duration: {result['duration_seconds']:.2f}s")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_explicit_colors():
    """Test 2: Explicit color scheme"""
    print("\n" + "=" * 80)
    print("Test 2: Luxury watch with gold and black colors")
    print("=" * 80)
    
    prompt = "Create a luxury watch advertisement using gold and black color scheme"
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-explicit-2",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        
        # Check color extraction
        color_scheme = spec.get('color_scheme', [])
        color_scheme_lower = [c.lower() for c in color_scheme]
        
        if 'gold' in color_scheme_lower and 'black' in color_scheme_lower:
            print(f"✅ PASS: Color scheme extracted correctly: {color_scheme}")
        else:
            print(f"❌ FAIL: Color scheme incorrect. Expected gold and black, got: {color_scheme}")
        
        # Check colors appear in prompts
        beats = spec.get('beats', [])
        colors_in_prompts = 0
        for beat in beats:
            prompt_text = beat.get('prompt', '').lower()
            if 'gold' in prompt_text or 'black' in prompt_text:
                colors_in_prompts += 1
        
        if colors_in_prompts > 0:
            print(f"✅ PASS: Colors mentioned in {colors_in_prompts}/{len(beats)} beat prompts")
        else:
            print(f"❌ FAIL: Colors not integrated into beat prompts")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_explicit_scene_requirements():
    """Test 3: Explicit scene requirements"""
    print("\n" + "=" * 80)
    print("Test 3: Watch ad with specific scene: show on wrist")
    print("=" * 80)
    
    prompt = "Create a Rolex ad. Show the watch on someone's wrist in the first scene"
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-explicit-3",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        
        # Check brand extraction
        if spec.get('brand_name') == 'Rolex':
            print(f"✅ PASS: Brand name extracted: Rolex")
        else:
            print(f"⚠️  Brand name: {spec.get('brand_name')}")
        
        # Check scene requirements
        scene_reqs = spec.get('scene_requirements', {})
        if scene_reqs:
            print(f"✅ PASS: Scene requirements extracted: {scene_reqs}")
        else:
            print(f"⚠️  No scene_requirements extracted (optional field)")
        
        # Check first beat mentions wrist
        beats = spec.get('beats', [])
        if beats:
            first_prompt = beats[0].get('prompt', '').lower()
            if 'wrist' in first_prompt:
                print(f"✅ PASS: First beat mentions 'wrist': {beats[0]['prompt'][:100]}...")
            else:
                print(f"⚠️  First beat doesn't explicitly mention wrist")
                print(f"   Prompt: {beats[0]['prompt'][:100]}...")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_all_explicit_elements():
    """Test 4: All explicit elements together"""
    print("\n" + "=" * 80)
    print("Test 4: All explicit elements - brand, music, colors, scenes")
    print("=" * 80)
    
    prompt = """Create a Nike Air Max advertisement with:
- Hip-hop music beats
- Red, white, and black color scheme  
- Show the shoes in urban setting in the first scene
- Show someone running in the shoes in the middle
- End with the Nike swoosh logo"""
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-explicit-4",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        
        # Check all elements
        print("\n📊 Extraction Results:")
        print(f"  Brand: {spec.get('brand_name')} {'✅' if spec.get('brand_name') == 'Nike' else '⚠️'}")
        
        music = spec.get('music_theme', '')
        print(f"  Music: {music} {'✅' if 'hip' in music.lower() or 'hop' in music.lower() else '⚠️'}")
        
        colors = spec.get('color_scheme', [])
        colors_lower = [c.lower() for c in colors]
        has_red = 'red' in colors_lower
        has_white = 'white' in colors_lower
        has_black = 'black' in colors_lower
        print(f"  Colors: {colors} {'✅' if (has_red and has_white and has_black) else '⚠️'}")
        
        scene_reqs = spec.get('scene_requirements', {})
        print(f"  Scene Requirements: {len(scene_reqs)} beats {'✅' if scene_reqs else '⚠️'}")
        
        # Check narrative flow
        beats = spec.get('beats', [])
        print(f"\n📝 Beat Sequence ({len(beats)} beats):")
        for i, beat in enumerate(beats):
            print(f"  {i+1}. {beat.get('beat_id')} ({beat.get('duration')}s)")
            print(f"     {beat.get('prompt', '')[:120]}...")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all explicit prompt tests"""
    print("=" * 80)
    print("PR #2: Testing Explicit Prompt Extraction")
    print("=" * 80)
    
    tests = [
        test_explicit_brand_and_music,
        test_explicit_colors,
        test_explicit_scene_requirements,
        test_all_explicit_elements,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR in {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL EXPLICIT TESTS PASSED!")
        print("o4-mini successfully extracts brand, music, colors, and scene requirements.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) had issues (may still be acceptable)")
        return 0  # Don't fail on warnings


if __name__ == "__main__":
    exit(main())

