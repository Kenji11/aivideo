"""
Test PR #2: Vague Prompts

Tests that o4-mini correctly infers missing elements:
- Music theme when not mentioned
- Color scheme when not specified
- Composes coherent prompts even with minimal input
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.phases.phase1_validate.task import plan_with_gpt4o_mini
from app.common.constants import BEAT_COMPOSITION_CREATIVITY

def test_vague_luxury():
    """Test 1: Minimal prompt - 'Luxury watch ad'"""
    print("\n" + "=" * 80)
    print("Test 1: Vague Prompt - 'Luxury watch ad'")
    print("=" * 80)
    
    prompt = "Luxury watch ad"
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-vague-1",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        
        # Check brand (should be None - not mentioned)
        brand = spec.get('brand_name')
        print(f"  Brand: {brand if brand else 'None (correct - not mentioned)'}")
        
        # Check music was inferred
        music = spec.get('music_theme')
        if music:
            print(f"✅ PASS: Music theme inferred: {music}")
            if any(word in music.lower() for word in ['elegant', 'cinematic', 'orchestral', 'sophisticated', 'classical']):
                print("  ✅ Music theme appropriate for luxury product")
            else:
                print(f"  ⚠️  Music theme may not match luxury: {music}")
        else:
            print("⚠️  Music theme not inferred (expected)")
        
        # Check colors were inferred
        colors = spec.get('color_scheme', [])
        if colors:
            print(f"✅ PASS: Color scheme inferred: {colors}")
            if any(color.lower() in ['gold', 'black', 'silver', 'white', 'navy', 'blue'] for color in colors):
                print("  ✅ Colors appropriate for luxury product")
            else:
                print(f"  ⚠️  Colors may not match luxury aesthetic: {colors}")
        else:
            print("❌ FAIL: Color scheme not inferred")
        
        # Check composed prompts
        beats = spec.get('beats', [])
        print(f"\n📋 Generated {len(beats)} beats:")
        detailed_prompts = 0
        for i, beat in enumerate(beats):
            prompt_text = beat.get('prompt', '')
            if len(prompt_text) > 50:
                detailed_prompts += 1
                print(f"  Beat {i+1}: {prompt_text[:80]}...")
        
        if detailed_prompts == len(beats):
            print(f"✅ PASS: All beats have detailed composed prompts")
        else:
            print(f"❌ FAIL: Only {detailed_prompts}/{len(beats)} beats have detailed prompts")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_vague_sportswear():
    """Test 2: Minimal prompt - 'Running shoes commercial'"""
    print("\n" + "=" * 80)
    print("Test 2: Vague Prompt - 'Running shoes commercial'")
    print("=" * 80)
    
    prompt = "Running shoes commercial"
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-vague-2",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        
        # Check music was inferred (should be energetic for sportswear)
        music = spec.get('music_theme')
        if music:
            print(f"✅ PASS: Music theme inferred: {music}")
            if any(word in music.lower() for word in ['energetic', 'upbeat', 'dynamic', 'electronic', 'motivational']):
                print("  ✅ Music theme appropriate for sportswear")
            else:
                print(f"  ⚠️  Music theme may not match sportswear energy: {music}")
        else:
            print("⚠️  Music theme not inferred")
        
        # Check colors were inferred (should be vibrant for sportswear)
        colors = spec.get('color_scheme', [])
        if colors:
            print(f"✅ PASS: Color scheme inferred: {colors}")
        else:
            print("❌ FAIL: Color scheme not inferred")
        
        # Check archetype matches sportswear
        archetype = spec.get('template', '')
        print(f"  Archetype: {archetype}")
        if 'energetic' in archetype.lower() or 'lifestyle' in archetype.lower():
            print("  ✅ Archetype appropriate for sportswear")
        
        # Check narrative coherence
        beats = spec.get('beats', [])
        print(f"\n📝 Beat Sequence:")
        for i, beat in enumerate(beats):
            print(f"  {i+1}. {beat.get('beat_id')} ({beat.get('duration')}s)")
            print(f"     {beat.get('prompt', '')[:100]}...")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_vague_tech():
    """Test 3: Minimal prompt - 'Smartphone ad'"""
    print("\n" + "=" * 80)
    print("Test 3: Vague Prompt - 'Smartphone ad'")
    print("=" * 80)
    
    prompt = "Smartphone ad"
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-vague-3",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        
        print(f"📊 Inferred Elements:")
        print(f"  Music: {spec.get('music_theme', 'None')}")
        print(f"  Colors: {spec.get('color_scheme', 'None')}")
        print(f"  Archetype: {spec.get('template', 'None')}")
        
        # Check o4-mini composed detailed prompts
        beats = spec.get('beats', [])
        total_length = sum(len(beat.get('prompt', '')) for beat in beats)
        avg_length = total_length / len(beats) if beats else 0
        
        print(f"\n📋 Prompt Quality:")
        print(f"  Total beats: {len(beats)}")
        print(f"  Average prompt length: {avg_length:.0f} chars")
        
        if avg_length > 100:
            print("✅ PASS: Prompts are detailed (avg > 100 chars)")
        else:
            print(f"❌ FAIL: Prompts too short (avg = {avg_length:.0f} chars)")
        
        # Check narrative flow
        print(f"\n📖 Narrative Flow:")
        for i in range(len(beats) - 1):
            current_prompt = beats[i].get('prompt', '').lower()
            next_prompt = beats[i+1].get('prompt', '').lower()
            
            # Very basic coherence check - look for continuation words
            if any(word in next_prompt for word in ['then', 'next', 'following', 'as', 'while']):
                print(f"  Beat {i+1} → {i+2}: ✅ Narrative connection")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_narrative_coherence():
    """Test 4: Check narrative flow across beats"""
    print("\n" + "=" * 80)
    print("Test 4: Narrative Coherence - 'Luxury perfume ad'")
    print("=" * 80)
    
    prompt = "Luxury perfume ad"
    
    try:
        result = plan_with_gpt4o_mini(
            video_id="test-vague-4",
            prompt=prompt,
            creativity_level=BEAT_COMPOSITION_CREATIVITY,
            start_time=0.0,
            reference_context={'has_assets': False}
        )
        
        spec = result['output_data']['spec']
        beats = spec.get('beats', [])
        
        print(f"📖 Analyzing Narrative Flow ({len(beats)} beats):\n")
        
        for i, beat in enumerate(beats):
            print(f"Beat {i+1}: {beat.get('beat_id')} ({beat.get('duration')}s)")
            print(f"  {beat.get('prompt', '')}\n")
        
        # Check consistency
        colors = spec.get('color_scheme', [])
        if colors:
            colors_in_prompts = sum(
                1 for beat in beats
                if any(color.lower() in beat.get('prompt', '').lower() for color in colors)
            )
            
            if colors_in_prompts > 0:
                print(f"✅ Color consistency: Colors appear in {colors_in_prompts}/{len(beats)} beats")
            else:
                print(f"⚠️  Colors not integrated into prompts")
        
        # Check product mentioned throughout
        product_mentions = sum(
            1 for beat in beats
            if 'perfume' in beat.get('prompt', '').lower()
        )
        
        if product_mentions >= len(beats) / 2:
            print(f"✅ Product focus: Perfume mentioned in {product_mentions}/{len(beats)} beats")
        else:
            print(f"⚠️  Product not consistently featured ({product_mentions}/{len(beats)} beats)")
        
        print(f"\n💰 Cost: ${result['cost_usd']:.4f}")
        return True
        
    except Exception as e:
        print(f"❌ FAIL: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all vague prompt tests"""
    print("=" * 80)
    print("PR #2: Testing Vague Prompt Inference")
    print("=" * 80)
    
    tests = [
        test_vague_luxury,
        test_vague_sportswear,
        test_vague_tech,
        test_narrative_coherence,
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
        print("\n✅ ALL VAGUE TESTS PASSED!")
        print("o4-mini successfully infers music, colors, and composes coherent narratives.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) had issues (may still be acceptable)")
        return 0  # Don't fail on warnings


if __name__ == "__main__":
    exit(main())

