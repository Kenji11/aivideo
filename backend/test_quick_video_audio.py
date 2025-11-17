#!/usr/bin/env python3
"""
Quick Video + Audio Test
Fast test with a single scenario to validate video and audio generation
"""
import sys
import os
import uuid
import time
import requests
from pathlib import Path

# Load .env if exists
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

API_URL = "http://localhost:8000"

def quick_test():
    """Quick test with one scenario."""
    print("="*80)
    print("🎬 QUICK VIDEO + AUDIO TEST")
    print("="*80)
    print()
    
    # Test with a VERY short prompt to force 2 chunks (10 seconds = 2 chunks of 5s each)
    # Must explicitly request 10 seconds to get 2 chunks
    test_prompt = "Create a 10 second luxury watches advertisement. Show elegant timepieces, sophisticated design, and premium craftsmanship. Keep it short and refined."
    
    print(f"📝 Test Prompt:")
    print(f"   {test_prompt}")
    print()
    print("Expected:")
    print("   Video: Elegant, sophisticated, premium watches")
    print("   Audio: Refined, elegant music matching luxury brand")
    print()
    
    # Create video generation
    print("🚀 Creating video generation...")
    try:
        response = requests.post(
            f"{API_URL}/api/generate",
            json={
                "prompt": test_prompt,
                "title": "Quick Test - Luxury Watches Ad",
                "reference_assets": []
            },
            timeout=10
        )
        response.raise_for_status()
        video_id = response.json().get('video_id')
        print(f"   ✅ Video ID: {video_id}")
    except Exception as e:
        print(f"   ❌ Failed: {str(e)}")
        return False
    
    # Monitor
    print()
    print("⏳ Monitoring generation...")
    start_time = time.time()
    last_phase = None
    
    while time.time() - start_time < 1800:  # 30 min timeout
        try:
            status = requests.get(f"{API_URL}/api/video/{video_id}", timeout=5).json()
            
            current_phase = status.get('current_phase', 'unknown')
            progress = status.get('progress', 0)
            video_status = status.get('status', 'unknown')
            cost = status.get('cost_usd', 0)
            
            if current_phase != last_phase:
                if last_phase:
                    print(f"   ✅ {last_phase} completed")
                if current_phase != 'unknown':
                    print(f"   🚀 {current_phase} ({progress:.1f}%)")
                last_phase = current_phase
            
            if video_status == 'complete':
                print()
                print("="*80)
                print("✅ GENERATION COMPLETE")
                print("="*80)
                
                # Check results
                final_url = status.get('final_video_url') or status.get('refined_url')
                spec = status.get('spec', {})
                audio_spec = spec.get('audio', {})
                phase5 = status.get('phase_outputs', {}).get('phase5_refine', {})
                music_url = phase5.get('output_data', {}).get('music_url')
                
                print(f"   Video ID: {video_id}")
                print(f"   Final Video: {final_url[:60] if final_url else 'N/A'}...")
                print(f"   Music URL: {music_url[:60] if music_url else 'N/A'}...")
                print(f"   Total Cost: ${cost:.4f}")
                print()
                print("   Audio Spec:")
                print(f"      Style: {audio_spec.get('music_style', 'N/A')}")
                print(f"      Tempo: {audio_spec.get('tempo', 'N/A')}")
                print(f"      Mood: {audio_spec.get('mood', 'N/A')}")
                print()
                
                if music_url:
                    print("   ✅ Audio was generated successfully!")
                else:
                    print("   ⚠️  Audio URL not found")
                
                if audio_spec.get('music_style') == 'upbeat_pop':
                    print("   ✅ Audio style matches content (upbeat_pop for sports)")
                else:
                    print(f"   ⚠️  Audio style: {audio_spec.get('music_style')} (expected: upbeat_pop)")
                
                print("="*80)
                return True
                
            elif video_status == 'failed':
                print()
                print("="*80)
                print("❌ GENERATION FAILED")
                print("="*80)
                print(f"   Error: {status.get('error', 'Unknown error')}")
                print("="*80)
                return False
            
            time.sleep(3)
        except Exception as e:
            print(f"   ⚠️  Status check error: {str(e)}")
            time.sleep(3)
    
    print()
    print("⏱️  Timeout after 30 minutes")
    return False

if __name__ == "__main__":
    # Check API
    try:
        requests.get(f"{API_URL}/health", timeout=5)
        print("✅ API is available")
    except:
        print("❌ API is not available. Start with: docker-compose up -d api")
        sys.exit(1)
    
    print()
    success = quick_test()
    sys.exit(0 if success else 1)

