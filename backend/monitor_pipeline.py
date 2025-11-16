#!/usr/bin/env python3
"""
Real-time Pipeline Monitoring Script
Monitors video generation pipeline execution with detailed phase tracking
"""
import sys
import time
import requests
from datetime import datetime
from typing import Optional, Dict

API_URL = "http://localhost:8000"

def format_time(seconds: float) -> str:
    """Format seconds as MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def get_video_status(video_id: str) -> Optional[Dict]:
    """Get current video status from API"""
    try:
        response = requests.get(f"{API_URL}/api/video/{video_id}", timeout=5)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_phase_info(phase: str, status: str, progress: float, cost: float, elapsed: float):
    """Print formatted phase information"""
    progress_bar = "█" * int(progress / 2) + "░" * (50 - int(progress / 2))
    print(f"[{format_time(elapsed)}] {phase:25s} | {progress:5.1f}% | ${cost:7.4f} | {progress_bar}")

def monitor_pipeline(video_id: str):
    """Monitor video generation pipeline in real-time"""
    print_header(f"🎬 Pipeline Monitor - Video ID: {video_id}")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   API: {API_URL}")
    print()
    
    start_time = time.time()
    last_phase = None
    last_progress = -1
    last_cost = -1
    last_status = None
    phase_start_time = {}
    
    print("⏳ Waiting for pipeline to start...")
    print()
    
    try:
        while True:
            video = get_video_status(video_id)
            
            if not video:
                print("❌ Could not fetch status. Is the API running?")
                time.sleep(2)
                continue
            
            current_phase = video.get('current_phase', 'unknown')
            progress = video.get('progress', 0)
            status = video.get('status', 'unknown')
            cost = video.get('cost_usd', 0)
            error = video.get('error')
            elapsed = time.time() - start_time
            
            # Phase change detection
            if current_phase != last_phase:
                if last_phase:
                    phase_duration = elapsed - phase_start_time.get(last_phase, start_time)
                    print(f"\n✅ Phase '{last_phase}' completed in {format_time(phase_duration)}")
                
                if current_phase and current_phase != 'unknown':
                    print(f"\n🚀 Starting Phase: {current_phase}")
                    print("-" * 80)
                    phase_start_time[current_phase] = elapsed
                
                last_phase = current_phase
            
            # Progress update
            if abs(progress - last_progress) >= 0.5 or abs(cost - last_cost) >= 0.0001:
                print_phase_info(current_phase or 'processing', status, progress, cost, elapsed)
                last_progress = progress
                last_cost = cost
            
            # Status change
            if status != last_status:
                if status == 'complete':
                    print("\n")
                    print_header("✅ VIDEO GENERATION COMPLETE!")
                    print(f"   Video ID: {video_id}")
                    print(f"   Total Time: {format_time(elapsed)}")
                    print(f"   Total Cost: ${cost:.4f}")
                    
                    final_url = video.get('final_video_url')
                    if final_url:
                        print(f"   Video URL: {final_url}")
                    
                    # Show phase breakdown
                    print("\n   Phase Breakdown:")
                    if current_phase:
                        phase_duration = elapsed - phase_start_time.get(current_phase, start_time)
                        print(f"      - {current_phase}: {format_time(phase_duration)}")
                    
                    break
                
                elif status == 'failed':
                    print("\n")
                    print_header("❌ VIDEO GENERATION FAILED")
                    print(f"   Video ID: {video_id}")
                    print(f"   Failed at: {format_time(elapsed)}")
                    print(f"   Cost before failure: ${cost:.4f}")
                    if error:
                        print(f"   Error: {error}")
                    if current_phase:
                        print(f"   Failed in phase: {current_phase}")
                    break
                
                last_status = status
            
            time.sleep(1)  # Poll every second
            
    except KeyboardInterrupt:
        print("\n\n⏸️  Monitoring stopped by user")
        print(f"   Video ID: {video_id}")
        print(f"   Last Status: {status}")
        print(f"   Last Progress: {progress:.1f}%")
        print(f"   Elapsed Time: {format_time(elapsed)}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Monitoring error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python monitor_pipeline.py <video_id>")
        print("\nExample:")
        print("  python monitor_pipeline.py 123e4567-e89b-12d3-a456-426614174000")
        sys.exit(1)
    
    video_id = sys.argv[1]
    monitor_pipeline(video_id)

