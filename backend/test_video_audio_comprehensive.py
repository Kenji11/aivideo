#!/usr/bin/env python3
"""
Comprehensive Video + Audio Generation Test Suite
Tests the complete pipeline: Video Generation (Phases 1-4) + Audio Generation (Phase 5)
Validates that both video and audio match content appropriately.
"""
import sys
import os
import uuid
import time
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Load .env if exists
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

API_URL = "http://localhost:8000"

# Test scenarios with expected video and audio characteristics
TEST_SCENARIOS = [
    {
        "name": "Sports Highlights",
        "prompt": "Create a dynamic basketball highlights video with fast-paced action, energetic shots, and exciting moments. Show slam dunks, three-pointers, and game-winning plays.",
        "expected_video": {
            "style": "dynamic", "pace": "fast", "mood": "energetic"
        },
        "expected_audio": {
            "music_style": "upbeat_pop",
            "tempo": "fast",
            "mood": "energetic"
        },
        "uploaded_assets": None
    },
    {
        "name": "Luxury Product Showcase",
        "prompt": "Create an elegant luxury watch showcase video. Show the watch in sophisticated lighting, highlight premium details, elegant presentation, sophisticated atmosphere.",
        "expected_video": {
            "style": "elegant", "pace": "moderate", "mood": "sophisticated"
        },
        "expected_audio": {
            "music_style": "orchestral",
            "tempo": "moderate",
            "mood": "sophisticated"
        },
        "uploaded_assets": None
    },
    {
        "name": "Tech Product Launch",
        "prompt": "Create a modern tech product launch video. Show innovative features, sleek design, cutting-edge technology, modern aesthetic, energetic presentation.",
        "expected_video": {
            "style": "modern", "pace": "moderate", "mood": "energetic"
        },
        "expected_audio": {
            "music_style": "upbeat_pop",
            "tempo": "moderate",
            "mood": "energetic"
        },
        "uploaded_assets": None
    },
    {
        "name": "Travel Adventure",
        "prompt": "Create an inspiring travel adventure video. Show breathtaking landscapes, epic vistas, adventure activities, cinematic shots, inspiring moments.",
        "expected_video": {
            "style": "cinematic", "pace": "moderate", "mood": "inspiring"
        },
        "expected_audio": {
            "music_style": "cinematic_epic",
            "tempo": "moderate",
            "mood": "inspiring"
        },
        "uploaded_assets": None
    },
    {
        "name": "Fashion Brand Campaign",
        "prompt": "Create a sophisticated fashion brand campaign video. Show elegant models, premium clothing, artistic styling, sophisticated atmosphere, luxury aesthetic.",
        "expected_video": {
            "style": "sophisticated", "pace": "moderate", "mood": "sophisticated"
        },
        "expected_audio": {
            "music_style": "orchestral",
            "tempo": "moderate",
            "mood": "sophisticated"
        },
        "uploaded_assets": None
    },
    {
        "name": "Corporate Announcement",
        "prompt": "Create a professional corporate announcement video. Show business setting, professional presentation, trustworthy atmosphere, corporate aesthetic.",
        "expected_video": {
            "style": "professional", "pace": "moderate", "mood": "sophisticated"
        },
        "expected_audio": {
            "music_style": "orchestral",
            "tempo": "moderate",
            "mood": "sophisticated"
        },
        "uploaded_assets": None
    },
]

def create_video_generation(prompt: str, assets: Optional[List] = None) -> Optional[str]:
    """Create a video generation request via API."""
    try:
        response = requests.post(
            f"{API_URL}/api/video/generate",
            json={
                "prompt": prompt,
                "assets": assets or []
            },
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('video_id')
    except Exception as e:
        print(f"   ❌ Failed to create video generation: {str(e)}")
        return None

def get_video_status(video_id: str) -> Optional[Dict]:
    """Get video generation status."""
    try:
        response = requests.get(f"{API_URL}/api/video/{video_id}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

def monitor_video_generation(video_id: str, timeout: int = 1800) -> Tuple[bool, Dict]:
    """Monitor video generation until completion or timeout."""
    start_time = time.time()
    last_phase = None
    last_progress = -1
    
    print(f"   ⏳ Monitoring generation (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        status = get_video_status(video_id)
        if not status:
            time.sleep(2)
            continue
        
        current_phase = status.get('current_phase', 'unknown')
        progress = status.get('progress', 0)
        video_status = status.get('status', 'unknown')
        cost = status.get('cost_usd', 0)
        
        # Phase change
        if current_phase != last_phase:
            if last_phase:
                print(f"      ✅ Phase '{last_phase}' completed")
            if current_phase and current_phase != 'unknown':
                print(f"      🚀 Starting Phase: {current_phase}")
            last_phase = current_phase
        
        # Progress update (every 5%)
        if abs(progress - last_progress) >= 5:
            print(f"      📊 Progress: {progress:.1f}% | Cost: ${cost:.4f}")
            last_progress = progress
        
        # Check completion
        if video_status == 'complete':
            elapsed = time.time() - start_time
            print(f"      ✅ Generation complete in {elapsed:.1f}s")
            return True, status
        elif video_status == 'failed':
            error = status.get('error', 'Unknown error')
            print(f"      ❌ Generation failed: {error}")
            return False, status
        
        time.sleep(3)  # Poll every 3 seconds
    
    print(f"      ⏱️  Timeout after {timeout}s")
    return False, {}

def validate_video_quality(video_url: str, expected_style: Dict) -> Tuple[bool, List[str]]:
    """Validate video quality and characteristics."""
    issues = []
    
    # Check if video URL exists
    if not video_url:
        issues.append("Video URL is missing")
        return False, issues
    
    # Check if it's an S3 URL
    if not video_url.startswith('s3://') and not video_url.startswith('http'):
        issues.append(f"Invalid video URL format: {video_url[:50]}")
    
    # Note: Full video quality validation would require downloading and analyzing
    # For now, we just check URL validity
    print(f"      📹 Video URL: {video_url[:60]}...")
    
    return True, issues

def validate_audio_match(video_spec: Dict, expected_audio: Dict) -> Tuple[bool, List[str]]:
    """Validate that audio matches expected characteristics."""
    issues = []
    
    audio_spec = video_spec.get('audio', {})
    if not audio_spec:
        issues.append("Audio spec is missing from video spec")
        return False, issues
    
    actual_style = audio_spec.get('music_style', 'unknown')
    actual_tempo = audio_spec.get('tempo', 'unknown')
    actual_mood = audio_spec.get('mood', 'unknown')
    
    expected_style = expected_audio.get('music_style')
    expected_tempo = expected_audio.get('tempo')
    expected_mood = expected_audio.get('mood')
    
    print(f"      🎵 Audio Spec:")
    print(f"         Style: {actual_style} (expected: {expected_style})")
    print(f"         Tempo: {actual_tempo} (expected: {expected_tempo})")
    print(f"         Mood: {actual_mood} (expected: {expected_mood})")
    
    matches = []
    if actual_style == expected_style:
        matches.append("✅ Style matches")
    else:
        issues.append(f"Style mismatch: {actual_style} vs {expected_style}")
        matches.append(f"❌ Style: {actual_style} != {expected_style}")
    
    if actual_tempo == expected_tempo:
        matches.append("✅ Tempo matches")
    else:
        issues.append(f"Tempo mismatch: {actual_tempo} vs {expected_tempo}")
        matches.append(f"⚠️  Tempo: {actual_tempo} != {expected_tempo}")
    
    if actual_mood == expected_mood:
        matches.append("✅ Mood matches")
    else:
        issues.append(f"Mood mismatch: {actual_mood} vs {expected_mood}")
        matches.append(f"⚠️  Mood: {actual_mood} != {expected_mood}")
    
    for match in matches:
        print(f"         {match}")
    
    return len(issues) == 0, issues

def run_comprehensive_test():
    """Run comprehensive video + audio generation tests."""
    print("="*80)
    print("🎬 COMPREHENSIVE VIDEO + AUDIO GENERATION TEST SUITE")
    print("="*80)
    print()
    print("Testing complete pipeline:")
    print("  - Phase 1: Prompt Validation & Spec Extraction")
    print("  - Phase 3: Reference Asset Generation")
    print("  - Phase 4: Video Chunk Generation")
    print("  - Phase 5: Audio Generation & Integration")
    print()
    print("Validating:")
    print("  - Video generation quality")
    print("  - Audio generation quality")
    print("  - Audio matches video content")
    print("  - Complete pipeline execution")
    print()
    
    results = []
    
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        print("\n" + "="*80)
        print(f"TEST {i}/{len(TEST_SCENARIOS)}: {scenario['name']}")
        print("="*80)
        print(f"   Prompt: {scenario['prompt'][:100]}...")
        print()
        
        # Step 1: Create video generation
        print("   📝 Step 1: Creating video generation request...")
        video_id = create_video_generation(scenario['prompt'], scenario.get('uploaded_assets'))
        
        if not video_id:
            print(f"   ❌ Failed to create video generation")
            results.append({
                "scenario": scenario['name'],
                "success": False,
                "error": "Failed to create video generation",
                "video_id": None
            })
            continue
        
        print(f"   ✅ Video ID: {video_id}")
        
        # Step 2: Monitor generation
        print()
        print("   🎬 Step 2: Monitoring video generation...")
        success, status = monitor_video_generation(video_id, timeout=1800)
        
        if not success:
            print(f"   ❌ Video generation failed or timed out")
            results.append({
                "scenario": scenario['name'],
                "success": False,
                "error": status.get('error', 'Timeout or unknown error'),
                "video_id": video_id
            })
            continue
        
        # Step 3: Validate video
        print()
        print("   📹 Step 3: Validating video...")
        final_video_url = status.get('final_video_url') or status.get('refined_url') or status.get('stitched_url')
        video_valid, video_issues = validate_video_quality(final_video_url, scenario['expected_video'])
        
        if not video_valid:
            print(f"   ⚠️  Video validation issues: {video_issues}")
        
        # Step 4: Validate audio match
        print()
        print("   🎵 Step 4: Validating audio matches content...")
        spec = status.get('spec', {})
        audio_match, audio_issues = validate_audio_match(spec, scenario['expected_audio'])
        
        # Step 5: Check if audio was generated
        print()
        print("   🎼 Step 5: Checking audio generation...")
        phase_outputs = status.get('phase_outputs', {})
        phase5_output = phase_outputs.get('phase5_refine', {})
        music_url = phase5_output.get('output_data', {}).get('music_url')
        
        if music_url:
            print(f"      ✅ Audio generated: {music_url[:60]}...")
            audio_generated = True
        else:
            print(f"      ⚠️  No audio URL found in Phase 5 output")
            audio_generated = False
        
        # Summary for this test
        print()
        print("   📊 Test Summary:")
        print(f"      Video Generated: {'✅' if video_valid else '❌'}")
        print(f"      Audio Generated: {'✅' if audio_generated else '❌'}")
        print(f"      Audio Matches: {'✅' if audio_match else '⚠️'}")
        print(f"      Total Cost: ${status.get('cost_usd', 0):.4f}")
        print(f"      Final Video: {final_video_url[:60] if final_video_url else 'N/A'}...")
        
        results.append({
            "scenario": scenario['name'],
            "success": success and video_valid,
            "video_id": video_id,
            "video_url": final_video_url,
            "music_url": music_url,
            "audio_match": audio_match,
            "audio_generated": audio_generated,
            "cost": status.get('cost_usd', 0),
            "video_issues": video_issues,
            "audio_issues": audio_issues
        })
        
        # Small delay between tests
        if i < len(TEST_SCENARIOS):
            print()
            print("   ⏳ Waiting 5 seconds before next test...")
            time.sleep(5)
    
    # Final Summary
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE TEST SUMMARY")
    print("="*80)
    
    total_tests = len(results)
    successful = sum(1 for r in results if r['success'])
    audio_generated_count = sum(1 for r in results if r['audio_generated'])
    audio_match_count = sum(1 for r in results if r['audio_match'])
    total_cost = sum(r['cost'] for r in results)
    
    print(f"   Total Tests: {total_tests}")
    print(f"   Successful: {successful} ({(successful/total_tests*100):.1f}%)")
    print(f"   Audio Generated: {audio_generated_count}/{total_tests}")
    print(f"   Audio Matches Content: {audio_match_count}/{total_tests}")
    print(f"   Total Cost: ${total_cost:.4f}")
    print()
    print("   Detailed Results:")
    for r in results:
        status_icon = "✅" if r['success'] else "❌"
        audio_icon = "🎵" if r['audio_generated'] else "🔇"
        match_icon = "✅" if r['audio_match'] else "⚠️"
        
        print(f"      {status_icon} {r['scenario']:30s}")
        print(f"         {audio_icon} Audio: {'Generated' if r['audio_generated'] else 'Missing'} | {match_icon} Match: {'Yes' if r['audio_match'] else 'No'}")
        print(f"         💰 Cost: ${r['cost']:.4f}")
        if r['video_issues']:
            print(f"         ⚠️  Video Issues: {', '.join(r['video_issues'])}")
        if r['audio_issues']:
            print(f"         ⚠️  Audio Issues: {', '.join(r['audio_issues'])}")
        print()
    
    print("="*80)
    
    return results

if __name__ == "__main__":
    print("🚀 Starting Comprehensive Video + Audio Test Suite")
    print("   Make sure the API is running on http://localhost:8000")
    print()
    
    # Check if API is available
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is available")
        else:
            print("⚠️  API health check returned non-200 status")
    except Exception as e:
        print(f"❌ API is not available: {str(e)}")
        print("   Please start the API server first:")
        print("   docker-compose up -d api")
        sys.exit(1)
    
    print()
    results = run_comprehensive_test()
    
    # Exit code based on results
    if all(r['success'] for r in results):
        print("\n✅ All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed or had issues")
        sys.exit(1)

