#!/usr/bin/env python3
"""
Test Nike Kobe Bryant / Black Mamba ad generation
"""
import requests
import json
import time
from datetime import datetime

API_URL = "http://localhost:8000"

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_status(video_id, status, phase, progress, cost, elapsed):
    """Print formatted status line"""
    phase_emoji = {
        'phase1_validate': '🔍',
        'phase3_references': '📸',
        'phase4_chunks': '🎬',
        'phase5_refine': '✨',
    }.get(phase, '⏳')
    
    print(f"   {phase_emoji} [{elapsed:>6.1f}s] {status:15s} | Phase: {phase:20s} | Progress: {progress:5.1f}% | Cost: ${cost:6.4f}")

def monitor_video_generation(video_id, prompt_title):
    """Monitor a video generation from start to finish"""
    print_header(f"🎬 Monitoring: {prompt_title}")
    print(f"   Video ID: {video_id}")
    print()
    
    start_time = time.time()
    last_progress = -1
    last_phase = ""
    last_cost = -1
    last_status = ""
    
    max_wait = 1800  # 30 minutes max
    poll_interval = 3  # Poll every 3 seconds
    
    print("   ⏳ Waiting for generation to start...")
    
    for i in range(max_wait // poll_interval):
        try:
            response = requests.get(f"{API_URL}/api/video/{video_id}", timeout=5)
            response.raise_for_status()
            video = response.json()
            
            status = video.get('status', 'unknown')
            phase = video.get('current_phase', '')
            progress = video.get('progress', 0)
            cost = video.get('cost_usd', 0)
            elapsed = time.time() - start_time
            
            # Print when status, phase, progress, or cost changes
            if (status != last_status or phase != last_phase or 
                abs(progress - last_progress) >= 2 or abs(cost - last_cost) >= 0.01):
                
                print_status(video_id, status, phase, progress, cost, elapsed)
                last_status = status
                last_phase = phase
                last_progress = progress
                last_cost = cost
            
            # Check completion
            if status == 'complete':
                print()
                print("   ✅ GENERATION COMPLETE!")
                print(f"   Final Cost: ${cost:.4f}")
                final_url = video.get('final_video_url') or video.get('stitched_url')
                if final_url:
                    print(f"   Video URL: {final_url[:80]}...")
                gen_time = video.get('generation_time_seconds', elapsed)
                print(f"   Generation Time: {gen_time:.1f}s ({gen_time/60:.1f} minutes)")
                
                # Show cost breakdown
                cost_breakdown = video.get('cost_breakdown', {})
                if cost_breakdown:
                    print()
                    print("   Cost Breakdown:")
                    for phase_name, phase_cost in cost_breakdown.items():
                        print(f"     - {phase_name}: ${phase_cost:.4f}")
                
                return True
                
            elif status == 'failed':
                print()
                print("   ❌ GENERATION FAILED")
                error = video.get('error_message', 'Unknown error')
                print(f"   Error: {error}")
                print(f"   Cost Before Failure: ${cost:.4f}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Error polling: {e}")
            time.sleep(poll_interval)
            continue
        
        time.sleep(poll_interval)
    
    print()
    print("   ⏱️  TIMEOUT - Generation still in progress")
    print(f"   Current Status: {status} | Phase: {phase} | Cost: ${cost:.4f}")
    return False

def test_kobe_ad():
    """Test Nike Kobe Bryant / Black Mamba ad generation"""
    print_header("🚀 Starting: Nike Kobe Bryant / Black Mamba Ad")
    
    # Create a compelling ad prompt
    prompt = (
        "Create a powerful and inspiring lifestyle advertisement video for Nike featuring "
        "Kobe Bryant's legacy and the Black Mamba spirit. Show the numbers 8 and 24 prominently, "
        "representing his iconic jersey numbers. Include dynamic basketball action, intense training scenes, "
        "and moments of triumph. Use dramatic lighting with purple and gold color accents. "
        "The mood should be epic, motivational, and legendary. Show athletic excellence, determination, "
        "and the Mamba Mentality - relentless pursuit of greatness."
    )
    
    try:
        # Create video generation request
        response = requests.post(
            f"{API_URL}/api/generate",
            json={
                "title": "Nike Kobe Bryant - Black Mamba Legacy",
                "description": "Epic tribute ad featuring Kobe's numbers 8 and 24, Black Mamba spirit, and Mamba Mentality",
                "prompt": prompt,
                "reference_assets": []
            },
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        video_id = result.get('video_id')
        if not video_id:
            print("   ❌ No video_id returned")
            return False
        
        print(f"   ✅ Request created: {video_id}")
        print(f"   Prompt: {prompt[:100]}...")
        print()
        
        # Monitor generation
        success = monitor_video_generation(video_id, "Nike Kobe Bryant - Black Mamba Legacy")
        
        return success
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print_header("🎥 NIKE KOBE BRYANT / BLACK MAMBA AD TEST")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   API: {API_URL}")
    print(f"   Pipeline: Phase 1 → Phase 3 → Phase 4 → Phase 5")
    print(f"   Expected: 6 chunks for 30-second video")
    print()
    
    success = test_kobe_ad()
    
    print()
    print_header("📊 TEST SUMMARY")
    if success:
        print("   ✅ Test completed successfully!")
        print("   🎬 Video should show Kobe's legacy, numbers 8 & 24, Black Mamba spirit")
    else:
        print("   ❌ Test failed or timed out")
    print()
