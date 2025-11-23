"""
Test script for PR #1: Phase 1 Schema Extensions

Tests that the new schema fields work correctly:
- brand_name (optional)
- music_theme (optional)
- color_scheme (optional)
- scene_requirements (optional)
- composed_prompt (required in BeatInfo)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.phases.phase1_validate.schemas import (
    VideoPlanning,
    BeatInfo,
    IntentAnalysis,
    ProductInfo,
    StyleSpec,
    ReferenceAssetMapping
)
from pydantic import ValidationError


def test_beat_info_with_composed_prompt():
    """Test 1: BeatInfo requires composed_prompt"""
    print("\n=== Test 1: BeatInfo with composed_prompt ===")
    
    try:
        beat = BeatInfo(
            beat_id="hero_shot",
            duration=5,
            composed_prompt="Close-up shot of luxury watch with dramatic golden lighting. "
                          "Slow dolly movement emphasizes premium craftsmanship and elegant design. "
                          "Cinematic depth of field creates sophisticated mood."
        )
        print("✅ PASS: BeatInfo created successfully with composed_prompt")
        print(f"   Beat ID: {beat.beat_id}")
        print(f"   Duration: {beat.duration}s")
        print(f"   Composed Prompt: {beat.composed_prompt[:80]}...")
    except ValidationError as e:
        print(f"❌ FAIL: {e}")
        return False
    
    return True


def test_beat_info_missing_composed_prompt():
    """Test 2: BeatInfo fails without composed_prompt"""
    print("\n=== Test 2: BeatInfo without composed_prompt (should fail) ===")
    
    try:
        beat = BeatInfo(
            beat_id="hero_shot",
            duration=5
            # Missing composed_prompt - should fail
        )
        print("❌ FAIL: BeatInfo should require composed_prompt but didn't")
        return False
    except ValidationError as e:
        print("✅ PASS: BeatInfo correctly requires composed_prompt")
        print(f"   Validation error (expected): {e.errors()[0]['msg']}")
    
    return True


def test_video_planning_with_all_new_fields():
    """Test 3: VideoPlanning with all new optional fields"""
    print("\n=== Test 3: VideoPlanning with all new fields ===")
    
    try:
        planning = VideoPlanning(
            intent_analysis=IntentAnalysis(
                product=ProductInfo(name="Rolex Submariner", category="luxury"),
                duration=30,
                style_keywords=["elegant", "cinematic", "premium"],
                mood="elegant",
                key_message="Showcase timeless luxury and craftsmanship"
            ),
            brand_name="Rolex",
            music_theme="cinematic orchestral",
            color_scheme=["gold", "black", "deep blue"],
            scene_requirements={
                "hero_shot": "show watch on wrist with suit",
                "call_to_action": "include Rolex crown logo prominently"
            },
            selected_archetype="luxury_showcase",
            archetype_reasoning="Luxury showcase matches premium product and elegant mood",
            beat_sequence=[
                BeatInfo(
                    beat_id="hero_shot",
                    duration=5,
                    composed_prompt="Cinematic close-up of Rolex Submariner on gentleman's wrist. "
                                  "Golden hour lighting accentuates polished metal and deep blue dial. "
                                  "Slow dolly in creates dramatic reveal of premium craftsmanship."
                ),
                BeatInfo(
                    beat_id="detail_showcase",
                    duration=5,
                    composed_prompt="Extreme macro shot highlighting intricate mechanical details. "
                                  "Black and gold color palette emphasizes luxury. "
                                  "Camera pans across watch face revealing precision engineering."
                ),
                BeatInfo(
                    beat_id="call_to_action",
                    duration=5,
                    composed_prompt="Final shot with Rolex crown logo prominent in frame. "
                                  "Watch positioned elegantly on black surface with gold accents. "
                                  "Static hold creates memorable brand impression."
                )
            ],
            beat_selection_reasoning="Selected beats create narrative from reveal to detail to brand moment",
            style=StyleSpec(
                aesthetic="Elegant cinematic luxury with dramatic lighting",
                color_palette=["gold", "black", "deep blue", "white"],
                mood="elegant",
                lighting="Golden hour natural light with dramatic shadows"
            )
        )
        
        print("✅ PASS: VideoPlanning created with all new fields")
        print(f"   Brand Name: {planning.brand_name}")
        print(f"   Music Theme: {planning.music_theme}")
        print(f"   Color Scheme: {planning.color_scheme}")
        print(f"   Scene Requirements: {planning.scene_requirements}")
        print(f"   Beats: {len(planning.beat_sequence)}")
        for i, beat in enumerate(planning.beat_sequence):
            print(f"     Beat {i+1}: {beat.beat_id} ({beat.duration}s)")
            print(f"       Prompt: {beat.composed_prompt[:60]}...")
    except ValidationError as e:
        print(f"❌ FAIL: {e}")
        return False
    
    return True


def test_video_planning_without_optional_fields():
    """Test 4: VideoPlanning without new optional fields (backward compatibility)"""
    print("\n=== Test 4: VideoPlanning without optional fields ===")
    
    try:
        planning = VideoPlanning(
            intent_analysis=IntentAnalysis(
                product=ProductInfo(name="Running Shoes", category="sportswear"),
                duration=15,
                style_keywords=["energetic", "dynamic"],
                mood="energetic",
                key_message="Showcase performance and speed"
            ),
            # brand_name=None (not provided)
            # music_theme=None (not provided)
            # color_scheme=None (not provided)
            # scene_requirements=None (not provided)
            selected_archetype="energetic_lifestyle",
            archetype_reasoning="Energetic lifestyle matches sportswear and dynamic mood",
            beat_sequence=[
                BeatInfo(
                    beat_id="dynamic_intro",
                    duration=5,
                    composed_prompt="High-energy shot of athlete sprinting in running shoes."
                ),
                BeatInfo(
                    beat_id="product_in_motion",
                    duration=5,
                    composed_prompt="Tracking shot following shoes in action during run."
                ),
                BeatInfo(
                    beat_id="call_to_action",
                    duration=5,
                    composed_prompt="Final shot of shoes with energetic background."
                )
            ],
            beat_selection_reasoning="Selected high-energy beats for sportswear narrative",
            style=StyleSpec(
                aesthetic="Dynamic and energetic",
                color_palette=["red", "black", "white"],
                mood="energetic",
                lighting="Bright natural daylight"
            )
        )
        
        print("✅ PASS: VideoPlanning works without optional fields (backward compatible)")
        print(f"   Brand Name: {planning.brand_name} (None is OK)")
        print(f"   Music Theme: {planning.music_theme} (None is OK)")
        print(f"   Color Scheme: {planning.color_scheme} (None is OK)")
        print(f"   Scene Requirements: {planning.scene_requirements} (None is OK)")
    except ValidationError as e:
        print(f"❌ FAIL: {e}")
        return False
    
    return True


def test_video_planning_partial_optional_fields():
    """Test 5: VideoPlanning with some optional fields"""
    print("\n=== Test 5: VideoPlanning with partial optional fields ===")
    
    try:
        planning = VideoPlanning(
            intent_analysis=IntentAnalysis(
                product=ProductInfo(name="Nike Air Max", category="sportswear"),
                duration=15,
                style_keywords=["energetic", "urban"],
                mood="energetic",
                key_message="Just Do It"
            ),
            brand_name="Nike",  # Has brand
            music_theme="hip-hop beats",  # Has music
            # color_scheme=None (not provided)
            # scene_requirements=None (not provided)
            selected_archetype="energetic_lifestyle",
            archetype_reasoning="Matches Nike's energetic brand identity",
            beat_sequence=[
                BeatInfo(
                    beat_id="dynamic_intro",
                    duration=5,
                    composed_prompt="Nike Air Max in urban setting with graffiti background."
                ),
                BeatInfo(
                    beat_id="action_montage",
                    duration=5,
                    composed_prompt="Fast-paced montage of shoes in action to hip-hop beats."
                ),
                BeatInfo(
                    beat_id="call_to_action",
                    duration=5,
                    composed_prompt="Final frame with Nike swoosh and 'Just Do It' message."
                )
            ],
            beat_selection_reasoning="High-energy beats match hip-hop music theme",
            style=StyleSpec(
                aesthetic="Urban energetic",
                color_palette=["red", "white", "black"],
                mood="energetic",
                lighting="Urban street lighting"
            )
        )
        
        print("✅ PASS: VideoPlanning works with partial optional fields")
        print(f"   Brand Name: {planning.brand_name}")
        print(f"   Music Theme: {planning.music_theme}")
        print(f"   Color Scheme: {planning.color_scheme} (None is OK)")
        print(f"   Scene Requirements: {planning.scene_requirements} (None is OK)")
    except ValidationError as e:
        print(f"❌ FAIL: {e}")
        return False
    
    return True


def test_serialization_deserialization():
    """Test 6: Serialize and deserialize VideoPlanning"""
    print("\n=== Test 6: Serialization and Deserialization ===")
    
    try:
        # Create planning
        original_planning = VideoPlanning(
            intent_analysis=IntentAnalysis(
                product=ProductInfo(name="Test Product", category="tech"),
                duration=15,
                style_keywords=["modern"],
                mood="minimalist",
                key_message="Test message"
            ),
            brand_name="TestBrand",
            music_theme="ambient electronic",
            color_scheme=["white", "gray", "blue"],
            scene_requirements={"hero_shot": "show product on desk"},
            selected_archetype="minimalist_reveal",
            archetype_reasoning="Test reasoning",
            beat_sequence=[
                BeatInfo(
                    beat_id="hero_shot",
                    duration=5,
                    composed_prompt="Test composed prompt for hero shot."
                ),
                BeatInfo(
                    beat_id="call_to_action",
                    duration=5,
                    composed_prompt="Test composed prompt for call to action."
                )
            ],
            beat_selection_reasoning="Test beat reasoning",
            style=StyleSpec(
                aesthetic="Minimalist modern",
                color_palette=["white", "gray", "blue"],
                mood="minimalist",
                lighting="Soft diffused"
            )
        )
        
        # Serialize to dict
        planning_dict = original_planning.model_dump()
        print(f"✅ Serialized to dict: {len(planning_dict)} keys")
        
        # Deserialize back
        restored_planning = VideoPlanning(**planning_dict)
        print(f"✅ Deserialized from dict")
        
        # Verify fields match
        assert restored_planning.brand_name == original_planning.brand_name
        assert restored_planning.music_theme == original_planning.music_theme
        assert restored_planning.color_scheme == original_planning.color_scheme
        assert restored_planning.scene_requirements == original_planning.scene_requirements
        assert len(restored_planning.beat_sequence) == len(original_planning.beat_sequence)
        assert restored_planning.beat_sequence[0].composed_prompt == original_planning.beat_sequence[0].composed_prompt
        
        print("✅ PASS: All fields match after serialization/deserialization")
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False
    
    return True


def main():
    """Run all tests"""
    print("=" * 80)
    print("Testing PR #1: Phase 1 Schema Extensions")
    print("=" * 80)
    
    tests = [
        test_beat_info_with_composed_prompt,
        test_beat_info_missing_composed_prompt,
        test_video_planning_with_all_new_fields,
        test_video_planning_without_optional_fields,
        test_video_planning_partial_optional_fields,
        test_serialization_deserialization,
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
        print("\n✅ ALL TESTS PASSED! Schema extensions are working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == "__main__":
    exit(main())

