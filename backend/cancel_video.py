#!/usr/bin/env python3
"""
Cancel a running video generation task
"""
import sys
import os
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.orchestrator.celery_app import celery_app
from app.orchestrator.progress import update_progress

def cancel_video_generation(video_id: str):
    """Cancel a running video generation"""
    db = SessionLocal()
    try:
        # Get video record
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        if not video:
            print(f"❌ Video ID '{video_id}' not found in database")
            return False
        
        print(f"📹 Found video: {video.title}")
        print(f"   Status: {video.status.value}")
        print(f"   Current Phase: {video.current_phase}")
        print()
        
        # Check if it's already complete or failed
        if video.status in [VideoStatus.COMPLETE, VideoStatus.FAILED]:
            print(f"⚠️  Video is already {video.status.value}, nothing to cancel")
            return False
        
        # Revoke all active Celery tasks for this video
        # We need to inspect active tasks and find ones related to this video_id
        print("🔍 Looking for active Celery tasks...")
        
        # Get active tasks from Celery
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        revoked_count = 0
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    task_id = task.get('id')
                    task_name = task.get('name', '')
                    task_args = task.get('args', [])
                    
                    # Check if this task is related to our video_id
                    if video_id in str(task_args):
                        print(f"   Found task: {task_name} (ID: {task_id})")
                        try:
                            celery_app.control.revoke(task_id, terminate=True)
                            print(f"   ✅ Revoked task {task_id}")
                            revoked_count += 1
                        except Exception as e:
                            print(f"   ⚠️  Could not revoke task {task_id}: {str(e)}")
        else:
            print("   No active tasks found")
        
        # Update database status
        print()
        print("📝 Updating database status...")
        video.status = VideoStatus.FAILED
        video.error_message = "Cancelled by user"
        video.current_phase = None
        
        # Update progress
        update_progress(
            video_id=video_id,
            status='failed',
            progress=video.progress,
            error="Cancelled by user"
        )
        
        db.commit()
        print(f"✅ Video status updated to 'failed' with cancellation message")
        print()
        print(f"📊 Summary:")
        print(f"   - Video ID: {video_id}")
        print(f"   - Tasks revoked: {revoked_count}")
        print(f"   - Status: {video.status.value}")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error cancelling video: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python cancel_video.py <video_id>")
        print()
        print("Example:")
        print("  python cancel_video.py ada8297d-2249-4318-962b-237ed88e28b3")
        sys.exit(1)
    
    video_id = sys.argv[1]
    success = cancel_video_generation(video_id)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

