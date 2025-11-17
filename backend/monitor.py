#!/usr/bin/env python3
"""
Enhanced Live Monitor for Video Generation
Shows real-time progress, phases, storyboard images, chunk processing, and costs
"""
import requests
import time
import sys
import os
from datetime import datetime
from typing import Optional, Dict

API_URL = os.getenv("API_URL", "http://localhost:8000")

def clear_screen():
    """Clear terminal screen"""
    os.system('clear' if os.name != 'nt' else 'cls')

def format_time(seconds):
    """Format seconds to MM:SS"""
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def get_status(video_id: str) -> Optional[Dict]:
    """Get current video status"""
    try:
        response = requests.get(f"{API_URL}/api/status/{video_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            print(f"  ❌ Video ID not found: {video_id}")
            return None
        else:
            print(f"  ❌ API Error: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        print(f"  ❌ Cannot connect to API at {API_URL}")
        return None
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return None

def print_header(title: str):
    """Print formatted header"""
    print("=" * 100)
    print(f"  {title}")
    print("=" * 100)

def print_phase_info(phase: str, progress: float, cost: float, elapsed: float):
    """Print phase information"""
    progress_bar = "█" * int(progress / 2) + "░" * (50 - int(progress / 2))
    phase_name = phase.replace('phase', '').replace('_', ' ').title() if phase else "Starting"
    print(f"  [{format_time(elapsed)}] {phase_name:25s} | {progress:5.1f}% | ${cost:7.4f} | {progress_bar}")

def print_chunk_progress(current_chunk: int, total_chunks: int):
    """Print chunk processing progress"""
    chunk_bar = "█" * current_chunk + "░" * (total_chunks - current_chunk)
    print(f"  📹 Chunk Progress: [{chunk_bar}] {current_chunk + 1}/{total_chunks} chunks")

def print_storyboard_images(animatic_urls: list):
    """Print storyboard images info"""
    if animatic_urls:
        print(f"  📸 Storyboard Images: {len(animatic_urls)} generated")
        for i, url in enumerate(animatic_urls[:5]):  # Show first 5
            print(f"      Beat {i + 1}: {url[:80]}...")
        if len(animatic_urls) > 5:
            print(f"      ... and {len(animatic_urls) - 5} more")

def monitor_video(video_id: str):
    """Monitor video generation in real-time"""
    clear_screen()
    print_header(f"🎬 Enhanced Video Generation Monitor")
    print(f"  Video ID: {video_id}")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  API: {API_URL}")
    print()
    
    start_time = time.time()
    last_phase = None
    last_progress = -1
    last_cost = -1
    last_status = None
    seen_storyboards = False
    seen_chunks = False
    phase_start_time = {}
    
    # Test API connection first
    print("  🔍 Testing API connection...")
    try:
        health_check = requests.get(f"{API_URL}/health", timeout=3)
        if health_check.status_code == 200:
            print("  ✅ API is running")
        else:
            print(f"  ⚠️  API returned status {health_check.status_code}")
    except Exception as e:
        print(f"  ❌ Cannot connect to API: {str(e)}")
        print(f"  Make sure the API is running at {API_URL}")
        sys.exit(1)
    
    print()
    print("  ⏳ Waiting for generation to start...")
    print()
    
    try:
        iteration = 0
        while True:
            iteration += 1
            status = get_status(video_id)
            
            if not status:
                if iteration == 1:
                    print("  ❌ Could not fetch status for video ID:", video_id)
                    print("  💡 Make sure:")
                    print("     - The video ID is correct")
                    print("     - The video generation has been started")
                    print("     - The API is running and accessible")
                    print()
                    print("  🔍 Checking if video exists in database...")
                    # Try to get video details
                    try:
                        video_response = requests.get(f"{API_URL}/api/video/{video_id}", timeout=5)
                        if video_response.status_code == 404:
                            print(f"  ❌ Video ID '{video_id}' not found in database.")
                            print("  💡 Try running without arguments to monitor the latest video:")
                            print("     python monitor.py")
                            sys.exit(1)
                        elif video_response.status_code == 200:
                            video_data = video_response.json()
                            print(f"  ✅ Video found: {video_data.get('title', 'Untitled')}")
                            print(f"     Status: {video_data.get('status', 'unknown')}")
                            print("     Waiting for status updates...")
                            print()
                    except Exception as e:
                        print(f"  ⚠️  Could not verify video: {str(e)}")
                
                # Show progress indicator
                if iteration % 5 == 0:
                    print(f"  ⏳ Still waiting... (attempt {iteration})")
                
                time.sleep(2)
                continue
            
            current_phase = status.get('current_phase')
            progress = status.get('progress', 0)
            video_status = status.get('status', 'unknown')
            cost = status.get('cost_usd', 0)
            error = status.get('error')
            elapsed = time.time() - start_time
            
            # Phase change detection
            if current_phase != last_phase:
                if last_phase:
                    phase_duration = elapsed - phase_start_time.get(last_phase, start_time)
                    print(f"\n  ✅ Phase '{last_phase}' completed in {format_time(phase_duration)}")
                    print()
                
                if current_phase and current_phase != 'unknown':
                    print(f"  🚀 Starting Phase: {current_phase}")
                    print("-" * 100)
                    phase_start_time[current_phase] = elapsed
                
                last_phase = current_phase
            
            # Progress update
            if abs(progress - last_progress) >= 0.5 or abs(cost - last_cost) >= 0.0001:
                print_phase_info(current_phase or 'processing', progress, cost, elapsed)
                last_progress = progress
                last_cost = cost
            
            # Storyboard images (Phase 2)
            animatic_urls = status.get('animatic_urls')
            if animatic_urls and not seen_storyboards:
                print()
                print("  🎨 Storyboard Images Generated!")
                print_storyboard_images(animatic_urls)
                print()
                seen_storyboards = True
            
            # Chunk processing (Phase 4)
            current_chunk_index = status.get('current_chunk_index')
            total_chunks = status.get('total_chunks')
            if current_phase == 'phase4_chunks' and current_chunk_index is not None and total_chunks:
                if not seen_chunks:
                    print()
                    print("  🎬 Phase 4: Chunk Generation Started")
                    seen_chunks = True
                print_chunk_progress(current_chunk_index, total_chunks)
            
            # Reference assets (Phase 3)
            reference_assets = status.get('reference_assets')
            if reference_assets:
                print()
                print("  🖼️  Reference Assets Generated:")
                if reference_assets.get('style_guide_url'):
                    print(f"      Style Guide: {reference_assets['style_guide_url'][:80]}...")
                if reference_assets.get('product_reference_url'):
                    print(f"      Product Reference: {reference_assets['product_reference_url'][:80]}...")
                if reference_assets.get('uploaded_assets'):
                    print(f"      Uploaded Assets: {len(reference_assets['uploaded_assets'])} images")
                print()
            
            # Stitched video (Phase 4 complete)
            stitched_url = status.get('stitched_video_url')
            if stitched_url:
                print()
                print(f"  🎥 Stitched Video Ready: {stitched_url[:80]}...")
                print()
            
            # Final video (Phase 5 complete or Veo model)
            final_url = status.get('final_video_url')
            if final_url and video_status == 'complete':
                print()
                print("=" * 100)
                print("  ✅ VIDEO GENERATION COMPLETE!")
                print("=" * 100)
                print(f"  Final Video URL: {final_url[:80]}...")
                print(f"  Total Cost: ${cost:.4f}")
                print(f"  Total Time: {format_time(elapsed)}")
                print()
                break
            
            # Error handling
            if video_status == 'failed':
                print()
                print("=" * 100)
                print("  ❌ VIDEO GENERATION FAILED")
                print("=" * 100)
                if error:
                    print(f"  Error: {error}")
                print(f"  Time: {format_time(elapsed)}")
                print(f"  Cost: ${cost:.4f}")
                print()
                break
            
            # Status change
            if video_status != last_status:
                if video_status == 'complete':
                    print()
                    print("  ✅ Status: Complete")
                elif video_status == 'failed':
                    print()
                    print("  ❌ Status: Failed")
                last_status = video_status
            
            # Print a heartbeat every 30 seconds if nothing is changing
            if iteration % 15 == 0 and progress == last_progress:
                print(f"  💓 Still processing... ({format_time(elapsed)})")
            
            time.sleep(2)  # Poll every 2 seconds
            
    except KeyboardInterrupt:
        print()
        print()
        print("  ⏸️  Monitoring stopped by user")
        print(f"  Final Status: {video_status}")
        print(f"  Progress: {progress:.1f}%")
        print(f"  Cost: ${cost:.4f}")
        print(f"  Time: {format_time(elapsed)}")
        print()

def get_latest_video_id() -> Optional[str]:
    """Get the latest video ID from the API"""
    try:
        response = requests.get(f"{API_URL}/api/videos", timeout=5)
        if response.status_code == 200:
            data = response.json()
            videos = data.get('videos', [])
            if videos:
                # Get the most recent video that's processing or pending
                for video in videos:
                    status = video.get('status', '')
                    if status in ['pending', 'processing']:
                        return video.get('video_id')
                # If no processing videos, return the most recent one
                if videos:
                    return videos[0].get('video_id')
        return None
    except Exception as e:
        print(f"  ⚠️  Could not fetch latest video: {str(e)}")
        return None

def main():
    """Main entry point"""
    video_id = None
    
    if len(sys.argv) < 2:
        print("Usage: python monitor.py [video_id]")
        print()
        print("If no video_id is provided, will monitor the latest video.")
        print()
        print("Examples:")
        print("  python monitor.py                    # Monitor latest video")
        print("  python monitor.py <video_id>         # Monitor specific video")
        print()
        
        # Try to get latest video
        print("  🔍 Looking for latest video...")
        video_id = get_latest_video_id()
        
        if not video_id:
            print("  ❌ No videos found. Please provide a video_id or start a video generation first.")
            sys.exit(1)
        
        print(f"  ✅ Found latest video: {video_id}")
        print()
    else:
        video_id = sys.argv[1]
    
    monitor_video(video_id)

if __name__ == "__main__":
    main()

