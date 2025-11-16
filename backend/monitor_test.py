#!/usr/bin/env python3
"""
Real-time monitoring script for video generation testing.
Shows detailed progress including multiple image distribution.
"""
import requests
import time
import sys
from datetime import datetime

API_URL = "http://localhost:8000"

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_phase_status(phase, status, progress, cost, elapsed, details=""):
    """Print phase status with emoji"""
    phase_emojis = {
        'phase1_validate': '🔍',
        'phase3_references': '📸',
        'phase4_chunks': '🎬',
        'phase5_refine': '✨',
        'validating': '🔍',
        'using_uploaded_assets': '📸',
        'generating_references': '📸',
        'generating_chunks': '🎬',
        'refining': '✨',
    }
    
    emoji = phase_emojis.get(phase, '⏳')
    phase_name = phase.replace('phase', '').replace('_', ' ').title()
    
    print(f"   {emoji} [{elapsed:>7.1f}s] {status:12s} | {phase_name:20s} | {progress:5.1f}% | ${cost:7.4f}")
    if details:
        print(f"      └─ {details}")

def monitor_video(video_id):
    """Monitor video generation in real-time"""
    print_header(f"🎬 Monitoring Video Generation")
    print(f"   Video ID: {video_id}")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    start_time = time.time()
    last_progress = -1
    last_phase = ""
    last_cost = -1
    last_status = ""
    chunk_count = 0
    
    print("   ⏳ Waiting for generation to start...")
    print()
    
    max_wait = 1800  # 30 minutes
    poll_interval = 2  # Poll every 2 seconds
    
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
            
            # Print on any change
            if (status != last_status or phase != last_phase or 
                abs(progress - last_progress) >= 1 or abs(cost - last_cost) >= 0.001):
                
                details = ""
                if phase == 'phase4_chunks' or 'chunks' in phase.lower():
                    # Try to extract chunk info from status message
                    status_msg = video.get('status_message', '')
                    if 'chunk' in status_msg.lower():
                        details = status_msg
                
                print_phase_status(phase, status, progress, cost, elapsed, details)
                last_status = status
                last_phase = phase
                last_progress = progress
                last_cost = cost
            
            # Check completion
            if status == 'complete':
                print()
                print_header("✅ GENERATION COMPLETE!")
                print(f"   Final Cost: ${cost:.4f}")
                print(f"   Total Time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
                
                final_url = video.get('final_video_url') or video.get('stitched_video_url')
                if final_url:
                    print(f"   Video URL: {final_url[:100]}...")
                
                # Show reference assets if available
                reference_assets = video.get('reference_assets', [])
                if reference_assets:
                    print(f"   Uploaded Images Used: {len(reference_assets)}")
                
                return True
                
            elif status == 'failed':
                print()
                print_header("❌ GENERATION FAILED")
                error = video.get('error_message', 'Unknown error')
                print(f"   Error: {error}")
                print(f"   Cost Before Failure: ${cost:.4f}")
                print(f"   Time Before Failure: {elapsed:.1f}s")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"   ⚠️  Connection error: {e}")
            time.sleep(poll_interval)
            continue
        
        time.sleep(poll_interval)
    
    print()
    print_header("⏱️  TIMEOUT")
    print(f"   Generation still in progress after {max_wait/60:.1f} minutes")
    print(f"   Current: {status} | {phase} | {progress:.1f}% | ${cost:.4f}")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 monitor_test.py <video_id>")
        print()
        print("Example:")
        print("  python3 monitor_test.py 1790f6ff-a260-4d5c-a6f8-c5e21ef67269")
        sys.exit(1)
    
    video_id = sys.argv[1]
    monitor_video(video_id)

