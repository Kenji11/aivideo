# Phase 2 Tasks - Part B: Task Implementation & Integration

**Owner:** Person handling Phase 2  
**Time Estimate:** 1-2 hours  
**Goal:** Implement Phase 2 Celery task and integrate with pipeline

---

## Task 1: Implement Phase 2 Task

**File:** `backend/app/phases/phase2_animatic/task.py`
```python
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase2_animatic.service import AnimaticGenerationService
import time
from typing import Dict

@celery_app.task(bind=True)
def generate_animatic(self, video_id: str, spec: Dict) -> dict:
    """
    Phase 2: Generate low-fidelity animatic frames.
    
    Args:
        video_id: Unique video ID
        spec: Full video specification from Phase 1
        
    Returns:
        PhaseOutput dict with animatic frame URLs
    """
    start_time = time.time()
    
    try:
        # Initialize service
        service = AnimaticGenerationService()
        
        # Generate animatic frames
        frame_urls = service.generate_frames(video_id, spec)
        
        # Success
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="success",
            output_data={"animatic_urls": frame_urls},
            cost_usd=service.total_cost,
            duration_seconds=time.time() - start_time,
            error_message=None
        )
        
        return output.dict()
        
    except Exception as e:
        # Failure
        output = PhaseOutput(
            video_id=video_id,
            phase="phase2_animatic",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
        
        return output.dict()
```

---

## Task 2: Create Manual Test Script

**File:** `backend/test_phase2.py` (in repo root)
```python
#!/usr/bin/env python3
"""
Manual test script for Phase 2
Requires Phase 1 output (spec)
Run: python test_phase2.py
"""

import sys
sys.path.insert(0, 'app')

from phases.phase2_animatic.service import AnimaticGenerationService
from phases.phase2_animatic.prompts import generate_animatic_prompt
import json

def test_prompt_generation():
    """Test prompt generation for different beat types"""
    
    print("Testing Phase 2: Animatic Prompt Generation\n")
    print("=" * 60)
    
    # Sample beats from different templates
    test_beats = [
        {"name": "hero_shot", "shot_type": "close_up", "action": "product_reveal"},
        {"name": "scene_setter", "shot_type": "wide", "action": "establish_environment"},
        {"name": "attention_grabber", "shot_type": "medium", "action": "dramatic_intro"}
    ]
    
    style = {"aesthetic": "luxury"}
    
    for i, beat in enumerate(test_beats, 1):
        prompt = generate_animatic_prompt(beat, style)
        print(f"\nBeat {i}: {beat['name']}")
        print(f"Action: {beat['action']}")
        print(f"Generated Prompt: {prompt}")
        print("-" * 60)

def test_full_generation():
    """Test full animatic generation (requires valid API keys and spec)"""
    
    print("\n\nTesting Phase 2: Full Animatic Generation\n")
    print("=" * 60)
    
    # Load a spec from Phase 1 (if available)
    try:
        with open('test_spec_1.json', 'r') as f:
            spec = json.load(f)
    except FileNotFoundError:
        print("⚠️  No test spec found. Run test_phase1.py first to generate a spec.")
        return
    
    print(f"Using spec for template: {spec['template']}")
    print(f"Number of beats: {len(spec['beats'])}")
    print(f"\nGenerating animatic frames...\n")
    
    try:
        service = AnimaticGenerationService()
        
        # Use a test video ID
        test_video_id = "test-video-001"
        
        frame_urls = service.generate_frames(test_video_id, spec)
        
        print(f"\n✅ Success!")
        print(f"Generated {len(frame_urls)} frames")
        print(f"Total cost: ${service.total_cost:.4f}")
        print(f"\nFrame URLs:")
        for i, url in enumerate(frame_urls):
            print(f"  {i}: {url}")
        
        # Save result
        result = {
            "video_id": test_video_id,
            "frame_urls": frame_urls,
            "total_frames": len(frame_urls),
            "cost_usd": service.total_cost
        }
        
        with open('test_animatic_result.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\nResult saved to: test_animatic_result.json")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    # Test prompt generation (no API calls)
    test_prompt_generation()
    
    # Uncomment to test full generation (requires API keys)
    # test_full_generation()
```

---

## Task 3: Update Orchestrator Pipeline

**File:** `backend/app/orchestrator/pipeline.py`

Update to include Phase 2:
```python
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic
from app.orchestrator.progress import update_progress, update_cost
import time
from typing import List

@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: List[dict]):
    """
    Main orchestration task.
    Currently implements Phase 1 and Phase 2.
    """
    start_time = time.time()
    total_cost = 0.0
    
    try:
        # Phase 1: Validate Prompt
        update_progress(video_id, "validating", 10)
        result1 = validate_prompt.delay(video_id, prompt, assets).get(timeout=60)
        
        if result1['status'] != "success":
            raise Exception(f"Phase 1 failed: {result1.get('error_message')}")
        
        total_cost += result1['cost_usd']
        update_cost(video_id, "phase1", result1['cost_usd'])
        
        # Phase 2: Generate Animatic
        update_progress(video_id, "generating_animatic", 25)
        result2 = generate_animatic.delay(
            video_id,
            result1['output_data']['spec']
        ).get(timeout=300)
        
        if result2['status'] != "success":
            raise Exception(f"Phase 2 failed: {result2.get('error_message')}")
        
        total_cost += result2['cost_usd']
        update_cost(video_id, "phase2", result2['cost_usd'])
        
        # TODO: Phase 3-6 will be added by other team members
        
        # For now, mark as complete after Phase 2
        update_progress(
            video_id,
            "complete",
            100,
            spec=result1['output_data']['spec'],
            animatic_urls=result2['output_data']['animatic_urls'],
            total_cost=total_cost,
            generation_time=time.time() - start_time
        )
        
        return {
            "video_id": video_id,
            "status": "complete",
            "spec": result1['output_data']['spec'],
            "animatic_urls": result2['output_data']['animatic_urls'],
            "cost_usd": total_cost,
            "generation_time": time.time() - start_time
        }
        
    except Exception as e:
        update_progress(video_id, "failed", None, error=str(e))
        raise
```

---

## Task 4: Update Progress Helper

**File:** `backend/app/orchestrator/progress.py`
```python
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from datetime import datetime
from typing import Optional

def update_progress(
    video_id: str,
    status: str,
    progress: Optional[float],
    **kwargs
):
    """Update video generation progress in database"""
    
    db = SessionLocal()
    
    try:
        video = db.query(VideoGeneration).filter_by(id=video_id).first()
        
        if not video:
            # Create new record
            video = VideoGeneration(
                id=video_id,
                prompt=kwargs.get('prompt', ''),
                status=VideoStatus[status.upper()],
                progress=progress or 0.0
            )
            db.add(video)
        else:
            # Update existing record
            video.status = VideoStatus[status.upper()]
            if progress is not None:
                video.progress = progress
            video.current_phase = kwargs.get('current_phase', f"Phase: {status}")
        
        # Update additional fields from kwargs
        if 'spec' in kwargs:
            video.spec = kwargs['spec']
        if 'animatic_urls' in kwargs:
            video.animatic_urls = kwargs['animatic_urls']
        if 'error' in kwargs:
            video.error_message = kwargs['error']
        if 'total_cost' in kwargs:
            video.cost_usd = kwargs['total_cost']
        if 'generation_time' in kwargs:
            video.generation_time_seconds = kwargs['generation_time']
        
        if status == 'complete':
            video.completed_at = datetime.utcnow()
        
        db.commit()
        
    finally:
        db.close()

def update_cost(video_id: str, phase: str, cost: float):
    """Update cost breakdown for a specific phase"""
    
    db = SessionLocal()
    
    try:
        video = db.query(VideoGeneration).filter_by(id=video_id).first()
        
        if video:
            if not video.cost_breakdown:
                video.cost_breakdown = {}
            
            video.cost_breakdown[phase] = cost
            video.cost_usd = sum(video.cost_breakdown.values())
            
            db.commit()
    
    finally:
        db.close()
```

---

## Task 5: Integration Test

**File:** `backend/app/tests/test_integration/test_phase1_and_2.py`
```python
import pytest
import uuid
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("REPLICATE_API_TOKEN") or not os.getenv("OPENAI_API_KEY"),
    reason="API keys not set"
)
def test_phase1_and_phase2_integration():
    """Test Phase 1 and Phase 2 working together"""
    
    video_id = str(uuid.uuid4())
    prompt = "Create a luxury watch ad with elegant gold aesthetics"
    assets = []
    
    # Phase 1
    print(f"\nTesting Phase 1 for video {video_id}")
    result1 = validate_prompt(video_id, prompt, assets)
    
    assert result1['status'] == 'success'
    assert 'spec' in result1['output_data']
    spec = result1['output_data']['spec']
    print(f"✓ Phase 1 complete. Template: {spec['template']}")
    
    # Phase 2
    print(f"\nTesting Phase 2 for video {video_id}")
    result2 = generate_animatic(video_id, spec)
    
    assert result2['status'] == 'success'
    assert 'animatic_urls' in result2['output_data']
    frame_urls = result2['output_data']['animatic_urls']
    
    print(f"✓ Phase 2 complete. Generated {len(frame_urls)} frames")
    print(f"Total cost: ${result1['cost_usd'] + result2['cost_usd']:.4f}")
    
    # Verify frames
    assert len(frame_urls) == len(spec['beats'])
    for url in frame_urls:
        assert url.startswith('s3://')
```

---

## ✅ Checkpoint

After completing these tasks, you should have:
- ✅ Phase 2 Celery task implemented
- ✅ Manual test script
- ✅ Orchestrator updated to include Phase 2
- ✅ Progress tracking working
- ✅ Integration test written

**Test Phase 1 + Phase 2 Together:**
```bash
# Start services
docker-compose up --build

# In another terminal, test Phase 1 first
docker-compose exec api python test_phase1.py

# Then test Phase 2
docker-compose exec api python test_phase2.py

# Or test full pipeline via API
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a luxury watch ad", "assets": []}'

# You should get back a video_id
# Poll status:
curl http://localhost:8000/api/status/{video_id}
```

**Phase 2 is complete!** Both Phase 1 and Phase 2 are now working together in the pipeline.

---

## Next Steps

Once both people complete their phases:
1. Merge both feature branches into `develop`
2. Test end-to-end pipeline
3. Move to implementing Phase 3-6 (or hand off to additional team members)
4. Deploy to AWS