# Phase 1 Tasks - Part B: Implementation

**Owner:** Person handling Phase 1  
**Time Estimate:** 2-3 hours  
**Goal:** Implement prompt validation service and task

---

## Task 1: Implement Validation Service

**File:** `backend/app/phases/phase1_validate/service.py`
```python
from app.services.openai import openai_client
from app.phases.phase1_validate.templates import load_template, validate_template_choice
from app.phases.phase1_validate.schemas import VideoSpec, StyleSpec, ProductSpec, AudioSpec, BeatSpec, TransitionSpec
from app.common.exceptions import ValidationException
import json
from typing import Dict, List

class PromptValidationService:
    """Service for validating and extracting structured specs from prompts"""
    
    def __init__(self):
        self.openai = openai_client
    
    def validate_and_extract(self, prompt: str, assets: List[dict]) -> Dict:
        """
        Extract structured specification from natural language prompt.
        
        Args:
            prompt: User's natural language prompt
            assets: List of uploaded assets
            
        Returns:
            Complete video specification dict
        """
        # Step 1: Extract basic intent from prompt
        extracted = self._extract_intent(prompt)
        
        # Step 2: Load and merge with template
        template_name = extracted.get('template', 'product_showcase')
        
        if not validate_template_choice(template_name):
            template_name = 'product_showcase'  # Fallback
        
        template = load_template(template_name)
        
        # Step 3: Merge extracted data with template
        full_spec = self._merge_with_template(extracted, template)
        
        # Step 4: Add uploaded assets
        full_spec['uploaded_assets'] = assets
        
        # Step 5: Validate final spec
        self._validate_spec(full_spec)
        
        return full_spec
    
    def _extract_intent(self, prompt: str) -> Dict:
        """Use GPT-4 to extract structured intent from prompt"""
        
        system_prompt = """You are a video production assistant. Extract structured specifications from user prompts.

Available templates:
- product_showcase: Focus on product features and details (luxury items, tech gadgets, high-end products)
- lifestyle_ad: Show product in real-world context (everyday products, consumer goods)
- announcement: Brand message or campaign announcement (new launches, company news)

Analyze the user's prompt and return JSON with:
{
    "template": "product_showcase",
    "style": {
        "aesthetic": "luxury" | "modern" | "minimalist" | "vibrant" | "elegant",
        "color_palette": ["gold", "black", "white"],
        "mood": "elegant" | "energetic" | "professional" | "casual",
        "lighting": "dramatic" | "natural" | "studio" | "soft"
    },
    "product": {
        "name": "luxury watch",
        "category": "accessories" | "electronics" | "fashion" | "food" | "other"
    },
    "audio": {
        "music_style": "orchestral" | "pop" | "electronic" | "acoustic",
        "tempo": "slow" | "moderate" | "fast",
        "mood": "sophisticated" | "energetic" | "inspiring" | "calm"
    }
}

IMPORTANT: Return ONLY valid JSON, no other text."""

        try:
            response = self.openai.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            extracted = json.loads(response.choices[0].message.content)
            return extracted
            
        except Exception as e:
            raise ValidationException(f"Failed to extract intent: {str(e)}")
    
    def _merge_with_template(self, extracted: Dict, template: Dict) -> Dict:
        """Merge extracted data with template structure"""
        
        # Start with template as base
        spec = template.copy()
        
        # Update with extracted values
        spec['template'] = extracted.get('template', template['name'])
        
        # Merge style
        if 'style' in extracted:
            spec['style'] = extracted['style']
        
        # Merge product
        if 'product' in extracted:
            spec['product'] = extracted['product']
        
        # Merge audio
        if 'audio' in extracted:
            spec['audio'].update(extracted['audio'])
        
        # Enrich beat prompts with extracted data
        for beat in spec['beats']:
            beat['prompt_template'] = beat['prompt_template'].format(
                product=spec.get('product', {}).get('name', 'product'),
                background='elegant background',
                style=spec.get('style', {}).get('aesthetic', 'modern'),
                setting='modern setting'
            )
        
        return spec
    
    def _validate_spec(self, spec: Dict):
        """Validate final specification"""
        
        required_fields = ['template', 'duration', 'fps', 'resolution', 'beats', 'transitions']
        
        for field in required_fields:
            if field not in spec:
                raise ValidationException(f"Missing required field: {field}")
        
        # Validate beats
        if not spec['beats']:
            raise ValidationException("Spec must have at least one beat")
        
        # Validate total duration matches beats
        total_duration = sum(beat['duration'] for beat in spec['beats'])
        if abs(total_duration - spec['duration']) > 1:  # Allow 1s tolerance
            raise ValidationException(f"Beat durations ({total_duration}s) don't match total duration ({spec['duration']}s)")
```

---

## Task 2: Implement Phase 1 Task

**File:** `backend/app/phases/phase1_validate/task.py`
```python
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase1_validate.service import PromptValidationService
from app.common.constants import COST_GPT4_TURBO
import time
from typing import List

@celery_app.task(bind=True)
def validate_prompt(self, video_id: str, prompt: str, assets: List[dict]) -> dict:
    """
    Phase 1: Validate prompt and extract structured specification.
    
    Args:
        video_id: Unique video ID
        prompt: User's natural language prompt
        assets: List of uploaded assets
        
    Returns:
        PhaseOutput dict with extracted spec
    """
    start_time = time.time()
    
    try:
        # Initialize service
        service = PromptValidationService()
        
        # Extract and validate spec
        spec = service.validate_and_extract(prompt, assets)
        
        # Success
        output = PhaseOutput(
            video_id=video_id,
            phase="phase1_validate",
            status="success",
            output_data={"spec": spec},
            cost_usd=COST_GPT4_TURBO,
            duration_seconds=time.time() - start_time,
            error_message=None
        )
        
        return output.dict()
        
    except Exception as e:
        # Failure
        output = PhaseOutput(
            video_id=video_id,
            phase="phase1_validate",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        )
        
        return output.dict()
```

---

## Task 3: Create Unit Tests

**File:** `backend/app/tests/test_phase1/test_validation.py`
```python
import pytest
from app.phases.phase1_validate.service import PromptValidationService
from app.phases.phase1_validate.templates import load_template, list_templates
from app.common.exceptions import ValidationException

def test_list_templates():
    """Test template listing"""
    templates = list_templates()
    assert len(templates) == 3
    assert "product_showcase" in templates
    assert "lifestyle_ad" in templates
    assert "announcement" in templates

def test_load_template():
    """Test template loading"""
    template = load_template("product_showcase")
    assert template['name'] == "product_showcase"
    assert template['duration'] == 30
    assert len(template['beats']) == 5

def test_load_invalid_template():
    """Test loading invalid template raises error"""
    with pytest.raises(ValueError):
        load_template("nonexistent")

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not set"
)
def test_validate_prompt():
    """Test prompt validation with real API call"""
    service = PromptValidationService()
    
    prompt = "Create a luxury watch ad with gold aesthetics"
    spec = service.validate_and_extract(prompt, [])
    
    assert spec['template'] in ['product_showcase', 'lifestyle_ad', 'announcement']
    assert 'style' in spec
    assert 'product' in spec
    assert 'beats' in spec
    assert len(spec['beats']) > 0

def test_validate_spec_missing_fields():
    """Test spec validation catches missing fields"""
    service = PromptValidationService()
    
    invalid_spec = {"template": "product_showcase"}
    
    with pytest.raises(ValidationException):
        service._validate_spec(invalid_spec)
```

---

## Task 4: Manual Testing Script

**File:** `backend/test_phase1.py` (in repo root, not in app/)
```python
#!/usr/bin/env python3
"""
Manual test script for Phase 1
Run: python test_phase1.py
"""

import sys
sys.path.insert(0, 'app')

from phases.phase1_validate.service import PromptValidationService
import json

def test_validation():
    """Test prompt validation"""
    
    service = PromptValidationService()
    
    test_prompts = [
        "Create a sleek ad for luxury watches with gold aesthetics",
        "Make an energetic video for sports shoes showing people running",
        "Announce our new product launch with bold graphics"
    ]
    
    print("Testing Phase 1: Prompt Validation\n")
    print("=" * 60)
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\nTest {i}: {prompt}")
        print("-" * 60)
        
        try:
            spec = service.validate_and_extract(prompt, [])
            
            print(f"✅ Success!")
            print(f"Template: {spec['template']}")
            print(f"Style: {spec['style']['aesthetic']}")
            print(f"Product: {spec['product']['name']}")
            print(f"Beats: {len(spec['beats'])} scenes")
            print(f"Audio: {spec['audio']['music_style']}")
            
            # Save full spec to file
            filename = f"test_spec_{i}.json"
            with open(filename, 'w') as f:
                json.dump(spec, f, indent=2)
            print(f"Full spec saved to: {filename}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_validation()
```

---

## Task 5: Update Orchestrator to Use Phase 1

**File:** `backend/app/orchestrator/pipeline.py`
```python
from app.orchestrator.celery_app import celery_app
from app.phases.phase1_validate.task import validate_prompt
from app.orchestrator.progress import update_progress, update_cost
import time
from typing import List

@celery_app.task
def run_pipeline(video_id: str, prompt: str, assets: List[dict]):
    """
    Main orchestration task - will eventually chain all 6 phases.
    Currently only Phase 1 is implemented.
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
        
        # TODO: Phase 2-6 will be added by other team members
        
        # For now, mark as complete after Phase 1
        update_progress(
            video_id,
            "complete",
            100,
            spec=result1['output_data']['spec'],
            total_cost=total_cost,
            generation_time=time.time() - start_time
        )
        
        return {
            "video_id": video_id,
            "status": "complete",
            "spec": result1['output_data']['spec'],
            "cost_usd": total_cost
        }
        
    except Exception as e:
        update_progress(video_id, "failed", None, error=str(e))
        raise
```

---

## ✅ Checkpoint

After completing these tasks, you should have:
- ✅ Validation service implemented
- ✅ Phase 1 Celery task working
- ✅ Unit tests written
- ✅ Manual test script ready

**Test Phase 1:**
```bash
# Start services
docker-compose up

# In another terminal, run manual test
docker-compose exec api python test_phase1.py

# Should see:
# ✅ Success for all 3 test prompts
# JSON files created with full specs
```

**Phase 1 is complete!** The other person can now work on Phase 2 independently.