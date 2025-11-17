#!/usr/bin/env python3
"""
Comprehensive Audio Generation Test Suite
Tests Phase 5 audio generation with various styles, tempos, and moods
to ensure audio matches video content appropriately.
"""
import sys
import os
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

# Load .env if exists
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.phases.phase5_refine.service import RefinementService
from app.phases.phase5_refine.model_config import get_default_music_model, get_music_model_config

# Test scenarios: (video_type, audio_style, tempo, mood, expected_match)
TEST_SCENARIOS = [
    # Sports/Action Videos
    ("sports_highlights", "upbeat_pop", "fast", "energetic", "high"),
    ("basketball_game", "upbeat_pop", "fast", "energetic", "high"),
    ("extreme_sports", "cinematic_epic", "fast", "inspiring", "high"),
    
    # Product Showcases
    ("luxury_watch", "orchestral", "moderate", "sophisticated", "high"),
    ("tech_product", "upbeat_pop", "moderate", "energetic", "medium"),
    ("fashion_brand", "orchestral", "moderate", "sophisticated", "high"),
    
    # Lifestyle/Commercial
    ("lifestyle_ad", "upbeat_pop", "moderate", "energetic", "high"),
    ("travel_video", "cinematic_epic", "moderate", "inspiring", "high"),
    ("food_commercial", "upbeat_pop", "moderate", "energetic", "medium"),
    
    # Corporate/Announcement
    ("corporate_announcement", "orchestral", "moderate", "sophisticated", "high"),
    ("product_launch", "cinematic_epic", "moderate", "inspiring", "high"),
    ("brand_story", "orchestral", "slow", "sophisticated", "high"),
    
    # Edge cases
    ("abstract_art", "orchestral", "slow", "sophisticated", "medium"),
    ("gaming_content", "upbeat_pop", "fast", "energetic", "high"),
]

# Video content to audio style mapping (for intelligent matching)
CONTENT_TO_AUDIO_MAP = {
    # Sports & Action
    "sport": {"music_style": "upbeat_pop", "tempo": "fast", "mood": "energetic"},
    "basketball": {"music_style": "upbeat_pop", "tempo": "fast", "mood": "energetic"},
    "football": {"music_style": "upbeat_pop", "tempo": "fast", "mood": "energetic"},
    "action": {"music_style": "cinematic_epic", "tempo": "fast", "mood": "inspiring"},
    "extreme": {"music_style": "cinematic_epic", "tempo": "fast", "mood": "inspiring"},
    
    # Luxury & Premium
    "luxury": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "premium": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "elegant": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "sophisticated": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    
    # Tech & Modern
    "tech": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    "modern": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    "innovation": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    
    # Lifestyle & Travel
    "lifestyle": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    "travel": {"music_style": "cinematic_epic", "tempo": "moderate", "mood": "inspiring"},
    "adventure": {"music_style": "cinematic_epic", "tempo": "moderate", "mood": "inspiring"},
    
    # Corporate & Professional
    "corporate": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "professional": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "announcement": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
}

def detect_audio_style_from_content(video_title: str, video_description: str = "") -> Dict[str, str]:
    """
    Intelligently detect appropriate audio style from video content.
    
    Args:
        video_title: Title of the video
        video_description: Optional description
        
    Returns:
        Dictionary with music_style, tempo, mood
    """
    content = (video_title + " " + video_description).lower()
    
    # Check for keywords and return matching audio config
    for keyword, audio_config in CONTENT_TO_AUDIO_MAP.items():
        if keyword in content:
            return audio_config.copy()
    
    # Default fallback
    return {
        "music_style": "orchestral",
        "tempo": "moderate",
        "mood": "sophisticated"
    }

def test_audio_generation(
    video_id: str,
    stitched_url: str,
    audio_config: Dict[str, str],
    test_name: str
) -> Tuple[bool, str, float]:
    """
    Test audio generation with specific configuration.
    
    Returns:
        (success, music_url, cost)
    """
    spec = {
        'duration': 30,
        'audio': audio_config
    }
    
    print(f"\n{'='*80}")
    print(f"🎵 Test: {test_name}")
    print(f"{'='*80}")
    print(f"   Audio Config: {audio_config}")
    print(f"   Video: {stitched_url[:60]}...")
    print()
    
    try:
        service = RefinementService()
        refined_url, music_url = service.refine_all(video_id, stitched_url, spec)
        
        if music_url:
            print(f"   ✅ SUCCESS")
            print(f"   Music URL: {music_url[:60]}...")
            print(f"   Cost: ${service.total_cost:.4f}")
            return True, music_url, service.total_cost
        else:
            print(f"   ⚠️  Completed but no music URL")
            return False, None, service.total_cost
            
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        return False, None, 0.0

def run_comprehensive_test(stitched_video_url: str):
    """
    Run comprehensive audio generation tests.
    """
    print("="*80)
    print("🎵 COMPREHENSIVE AUDIO GENERATION TEST SUITE")
    print("="*80)
    print()
    print("Testing various audio styles, tempos, and moods")
    print("to ensure audio matches video content appropriately.")
    print()
    
    # Get model info
    model_config = get_default_music_model()
    print(f"📊 Music Model: {model_config['name']}")
    print(f"   Description: {model_config.get('description', 'N/A')}")
    print(f"   Max Duration: {model_config['max_duration']}s")
    print(f"   Cost per Generation: ${model_config['cost_per_generation']:.4f}")
    print()
    
    results = []
    
    # Test 1: Default orchestral (current default)
    print("\n" + "="*80)
    print("TEST 1: Default Orchestral (Current Behavior)")
    print("="*80)
    video_id = str(uuid.uuid4())
    default_config = {
        "music_style": "orchestral",
        "tempo": "moderate",
        "mood": "sophisticated"
    }
    success, music_url, cost = test_audio_generation(
        video_id, stitched_video_url, default_config, "Default Orchestral"
    )
    results.append(("Default Orchestral", success, cost))
    
    # Test 2: Upbeat Pop (for sports/action)
    print("\n" + "="*80)
    print("TEST 2: Upbeat Pop (Sports/Action Content)")
    print("="*80)
    video_id = str(uuid.uuid4())
    upbeat_config = {
        "music_style": "upbeat_pop",
        "tempo": "fast",
        "mood": "energetic"
    }
    success, music_url, cost = test_audio_generation(
        video_id, stitched_video_url, upbeat_config, "Upbeat Pop"
    )
    results.append(("Upbeat Pop", success, cost))
    
    # Test 3: Cinematic Epic (for dramatic content)
    print("\n" + "="*80)
    print("TEST 3: Cinematic Epic (Dramatic Content)")
    print("="*80)
    video_id = str(uuid.uuid4())
    cinematic_config = {
        "music_style": "cinematic_epic",
        "tempo": "moderate",
        "mood": "inspiring"
    }
    success, music_url, cost = test_audio_generation(
        video_id, stitched_video_url, cinematic_config, "Cinematic Epic"
    )
    results.append(("Cinematic Epic", success, cost))
    
    # Test 4: Intelligent Content Detection
    print("\n" + "="*80)
    print("TEST 4: Intelligent Content-Based Audio Selection")
    print("="*80)
    test_videos = [
        ("Nike Basketball Highlights", "sports"),
        ("Luxury Watch Showcase", "luxury"),
        ("Tech Product Launch", "tech"),
        ("Travel Adventure Video", "travel"),
    ]
    
    for video_title, expected_type in test_videos:
        video_id = str(uuid.uuid4())
        detected_config = detect_audio_style_from_content(video_title)
        print(f"\n   Video: '{video_title}'")
        print(f"   Detected Type: {expected_type}")
        print(f"   Auto-Selected Audio: {detected_config}")
        
        success, music_url, cost = test_audio_generation(
            video_id, stitched_video_url, detected_config, f"Auto: {video_title}"
        )
        results.append((f"Auto: {video_title}", success, cost))
    
    # Summary
    print("\n" + "="*80)
    print("📊 TEST SUMMARY")
    print("="*80)
    total_tests = len(results)
    successful = sum(1 for _, success, _ in results if success)
    total_cost = sum(cost for _, _, cost in results)
    
    print(f"   Total Tests: {total_tests}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {total_tests - successful}")
    print(f"   Success Rate: {(successful/total_tests*100):.1f}%")
    print(f"   Total Cost: ${total_cost:.4f}")
    print()
    print("   Detailed Results:")
    for test_name, success, cost in results:
        status = "✅" if success else "❌"
        print(f"      {status} {test_name:30s} - ${cost:.4f}")
    print("="*80)
    
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_audio_generation_comprehensive.py <stitched_video_url>")
        print()
        print("Example:")
        print("  python test_audio_generation_comprehensive.py s3://bucket/videos/abc123/stitched.mp4")
        print()
        print("Or get from database:")
        print("  # Query for latest stitched URL")
        sys.exit(1)
    
    stitched_url = sys.argv[1]
    run_comprehensive_test(stitched_url)

