from typing import Dict
import time
import traceback
import json
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase2_animatic.service import AnimaticGenerationService


@celery_app.task(bind=True)
def generate_animatic(self, video_id: str, spec: Dict) -> Dict:
    """
    Generate animatic frames for a video specification.
    
    Args:
        video_id: Unique identifier for the video
        spec: Dictionary containing 'beats' and 'style' keys
        
    Returns:
        Dictionary representation of PhaseOutput with status, output_data, cost, etc.
    """
    start_time = time.time()
    
    # Log phase start
    template_name = spec.get('template', 'unknown')
    beats_count = len(spec.get('beats', []))
    duration = spec.get('duration', 'unknown')
    style_aesthetic = spec.get('style', {}).get('aesthetic', 'unknown')
    color_palette = spec.get('style', {}).get('color_palette', [])
    
    print(f"🚀 Phase 2 (Animatic) starting for video {video_id}")
    print(f"   Input:")
    print(f"   - Template: {template_name}")
    print(f"   - Beats: {beats_count}")
    print(f"   - Duration: {duration}s")
    print(f"   - Style: {style_aesthetic}")
    if color_palette:
        print(f"   - Color palette: {', '.join(color_palette[:5])}{'...' if len(color_palette) > 5 else ''}")
    
    # Log full spec (formatted)
    print(f"   - Full spec:")
    spec_json = json.dumps(spec, indent=2)
    for line in spec_json.split('\n'):
        print(f"     {line}")
    
    try:
        # Initialize service
        service = AnimaticGenerationService()
        
        # Generate frames
        frame_urls = service.generate_frames(video_id, spec)
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        # Create success output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="success",
            output_data={"animatic_urls": frame_urls},
            cost_usd=service.total_cost,
            duration_seconds=duration_seconds,
            error_message=None
        )
        
        # Log successful phase completion
        print(f"✅ Phase 2 (Animatic) completed successfully for video {video_id}")
        print(f"   Output:")
        print(f"   - Generated frames: {len(frame_urls)}")
        print(f"   - Frame URLs: {len(frame_urls)} S3 URLs")
        if frame_urls:
            print(f"   - First frame: {frame_urls[0][:80]}...")
        print(f"   - Total cost: ${service.total_cost:.4f}")
        print(f"   - Duration: {duration_seconds:.2f}s")
        print(f"   - Average time per frame: {duration_seconds / len(frame_urls):.2f}s" if frame_urls else "")
        
        return output.dict()
        
    except Exception as e:
        # Calculate duration even on error
        duration_seconds = time.time() - start_time
        
        # Log error details
        print(f"❌ Phase 2 (Animatic) failed for video {video_id}")
        print(f"   Error: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Duration before failure: {duration_seconds:.2f}s")
        print(f"   Traceback:")
        for line in traceback.format_exc().split('\n'):
            if line.strip():
                print(f"   {line}")
        
        # Create error output
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        )
        
        return output.dict()
