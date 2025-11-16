#!/usr/bin/env python3
"""
Live monitoring script for video generation
Shows real-time progress, phase, and cost updates
"""
import requests
import time
import sys
from datetime import datetime

API_URL = "http://localhost:8000"

def format_time(seconds):
    """Format seconds to MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def get_status(video_id):
    """Get current video status"""
    try:
        response = requests.get(f"{API_URL}/api/status/{video_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        return None

def monitor_video(video_id):
    """Monitor video generation in real-time"""
    print("=" * 80)
    print(f"🎬 Monitoring Video Generation: {video_id}")
    print("=" * 80)
    print()
    
    start_time = time.time()
    last_phase = None
    last_progress = -1
    
    try:
        while True:
            status = get_status(video_id)
            
            if not status:
                print("❌ Could not fetch status. Is the API running?")
                time.sleep(2)
                continue
            
            current_phase = status.get('current_phase', 'unknown')
            progress = status.get('progress', 0)
            video_status = status.get('status', 'unknown')
            cost = status.get('cost_usd', 0)
            error = status.get('error')
            
            elapsed = time.time() - start_time
            
            # Phase change detection
            if current_phase != last_phase:
                print()
                print(f"📊 Phase Changed: {last_phase or 'Starting'} → {current_phase}")
                print("-" * 80)
                last_phase = current_phase
            
            # Progress update
            if progress != last_progress:
                progress_bar = "█" * int(progress / 2) + "░" * (50 - int(progress / 2))
                
                print(f"\r[{format_time(elapsed)}] {current_phase:20s} | {progress:5.1f}% | ${cost:6.4f} | {progress_bar}", end="", flush=True)
                last_progress = progress
            
            # Status updates
            if video_status == 'complete':
                print("\n")
                print("=" * 80)
                print("✅ VIDEO GENERATION COMPLETE!")
                print("=" * 80)
                print(f"   Video ID: {video_id}")
                print(f"   Total Time: {format_time(elapsed)}")
                print(f"   Total Cost: ${cost:.4f}")
                if status.get('final_video_url'):
                    print(f"   Video URL: {status.get('final_video_url')}")
                break
            
            elif video_status == 'failed':
                print("\n")
                print("=" * 80)
                print("❌ VIDEO GENERATION FAILED")
                print("=" * 80)
                if error:
                    print(f"   Error: {error}")
                break
            
            time.sleep(2)  # Poll every 2 seconds
            
    except KeyboardInterrupt:
        print("\n\n⏸️  Monitoring stopped by user")
        print(f"   Video ID: {video_id}")
        print(f"   Last Status: {video_status}")
        print(f"   Last Progress: {progress:.1f}%")
        sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 monitor_live.py <video_id>")
        print("\nTo get the latest video ID, check the database or frontend.")
        sys.exit(1)
    
    video_id = sys.argv[1]
    monitor_video(video_id)

