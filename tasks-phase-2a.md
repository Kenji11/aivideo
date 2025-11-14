# Phase 2 Tasks - Part A: Animatic Prompts & Service Setup

**Owner:** Person handling Phase 2  
**Time Estimate:** 1-2 hours  
**Goal:** Set up animatic generation infrastructure

---

## Task 1: Create Phase 2 Schemas

**File:** `backend/app/phases/phase2_animatic/schemas.py`
```python
from pydantic import BaseModel
from typing import List, Dict

class AnimaticFrameSpec(BaseModel):
    """Specification for a single animatic frame"""
    frame_num: int
    beat_name: str
    shot_type: str
    action: str
    prompt: str

class AnimaticGenerationRequest(BaseModel):
    """Request to generate animatic"""
    video_id: str
    beats: List[Dict]
    style: Dict

class AnimaticGenerationResult(BaseModel):
    """Result of animatic generation"""
    video_id: str
    frame_urls: List[str]
    total_frames: int
    cost_usd: float
```

---

## Task 2: Implement Prompt Generation Utility

**File:** `backend/app/phases/phase2_animatic/prompts.py`
```python
from typing import Dict

def generate_animatic_prompt(beat: Dict, style: Dict) -> str:
    """
    Generate a simple, structural prompt for animatic frame.
    
    Animatic frames should be:
    - Low detail (sketch-like)
    - Focus on composition and structure
    - Black and white or minimal color
    - Fast to generate
    
    Args:
        beat: Beat specification from template
        style: Style specification from Phase 1
        
    Returns:
        Prompt string for SDXL
    """
    
    # Base style for animatic (always simple)
    base_style = "simple line drawing, minimal detail, sketch style, black and white"
    
    # Shot type
    shot = beat.get('shot_type', 'medium')
    
    # Action (simplified)
    action = beat.get('action', 'scene')
    action_simplified = _simplify_action(action)
    
    # Compose prompt
    prompt = f"{action_simplified}, {shot} shot, {base_style}"
    
    return prompt

def _simplify_action(action: str) -> str:
    """Simplify action description for animatic"""
    
    # Map complex actions to simple animatic descriptions
    action_map = {
        "product_reveal": "object in center of frame",
        "feature_highlight": "close-up of object details",
        "usage_scenario": "person holding object",
        "brand_story": "object in environment",
        "final_impression": "object with logo",
        "establish_environment": "wide shot of location",
        "introduce_character": "person standing",
        "use_product": "person interacting with object",
        "show_benefit": "person happy gesture",
        "product_branding": "object with text",
        "dramatic_intro": "bold geometric shapes",
        "show_message": "text centered",
        "visual_emphasis": "object prominent",
        "final_message": "logo and text"
    }
    
    return action_map.get(action, "simple scene composition")

def create_negative_prompt() -> str:
    """Standard negative prompt for animatic generation"""
    return (
        "detailed, photorealistic, complex, colorful, high quality, "
        "rendered, painted, artistic, elaborate, ornate, decorative"
    )
```

---

## Task 3: Implement Animatic Generation Service

**File:** `backend/app/phases/phase2_animatic/service.py`
```python
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.phases.phase2_animatic.prompts import generate_animatic_prompt, create_negative_prompt
from app.common.constants import COST_SDXL_IMAGE, S3_ANIMATIC_PREFIX
from typing import List, Dict
import tempfile
import requests

class AnimaticGenerationService:
    """Service for generating low-fidelity animatic frames"""
    
    def __init__(self):
        self.replicate = replicate_client
        self.s3 = s3_client
        self.total_cost = 0.0
    
    def generate_frames(self, video_id: str, spec: Dict) -> List[str]:
        """
        Generate animatic frames for all beats.
        
        Args:
            video_id: Unique video ID
            spec: Full video specification from Phase 1
            
        Returns:
            List of S3 URLs for generated frames
        """
        
        beats = spec['beats']
        style = spec.get('style', {})
        
        frame_urls = []
        
        print(f"Generating {len(beats)} animatic frames for video {video_id}")
        
        for i, beat in enumerate(beats):
            print(f"Generating frame {i+1}/{len(beats)}: {beat['name']}")
            
            # Generate prompt
            prompt = generate_animatic_prompt(beat, style)
            negative_prompt = create_negative_prompt()
            
            # Generate frame with SDXL
            frame_url = self._generate_single_frame(
                video_id=video_id,
                frame_num=i,
                prompt=prompt,
                negative_prompt=negative_prompt
            )
            
            frame_urls.append(frame_url)
            self.total_cost += COST_SDXL_IMAGE
        
        print(f"✅ Generated {len(frame_urls)} animatic frames")
        print(f"Total cost: ${self.total_cost:.4f}")
        
        return frame_urls
    
    def _generate_single_frame(
        self,
        video_id: str,
        frame_num: int,
        prompt: str,
        negative_prompt: str
    ) -> str:
        """Generate a single animatic frame"""
        
        try:
            # Call Replicate SDXL
            output = self.replicate.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "width": 512,  # Low res for speed
                    "height": 512,
                    "num_inference_steps": 20,  # Fast generation
                    "guidance_scale": 7.0,
                    "num_outputs": 1
                }
            )
            
            # Download image from Replicate URL
            image_url = output[0]
            image_data = requests.get(image_url).content
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
                tmp.write(image_data)
                tmp_path = tmp.name
            
            # Upload to S3
            s3_key = f"videos/{video_id}/{S3_ANIMATIC_PREFIX}/frame_{frame_num:02d}.png"
            s3_url = self.s3.upload_file(tmp_path, s3_key)
            
            print(f"  ✓ Frame {frame_num} uploaded: {s3_url}")
            
            return s3_url
            
        except Exception as e:
            raise Exception(f"Failed to generate frame {frame_num}: {str(e)}")
```

---

## Task 4: Create Unit Tests

**File:** `backend/app/tests/test_phase2/test_prompts.py`
```python
import pytest
from app.phases.phase2_animatic.prompts import (
    generate_animatic_prompt,
    create_negative_prompt,
    _simplify_action
)

def test_simplify_action():
    """Test action simplification"""
    assert _simplify_action("product_reveal") == "object in center of frame"
    assert _simplify_action("introduce_character") == "person standing"
    assert _simplify_action("unknown_action") == "simple scene composition"

def test_create_negative_prompt():
    """Test negative prompt generation"""
    neg = create_negative_prompt()
    assert "detailed" in neg
    assert "photorealistic" in neg
    assert "complex" in neg

def test_generate_animatic_prompt():
    """Test animatic prompt generation"""
    beat = {
        "name": "hero_shot",
        "shot_type": "close_up",
        "action": "product_reveal"
    }
    style = {
        "aesthetic": "luxury"
    }
    
    prompt = generate_animatic_prompt(beat, style)
    
    assert "object in center of frame" in prompt
    assert "close_up shot" in prompt
    assert "simple line drawing" in prompt
    assert "sketch style" in prompt
```

---

## ✅ Checkpoint

After completing these tasks, you should have:
- ✅ Phase 2 schemas defined
- ✅ Prompt generation utility working
- ✅ Animatic service skeleton implemented
- ✅ Unit tests for prompts

**Test prompts:**
```python
# In Python shell
from app.phases.phase2_animatic.prompts import generate_animatic_prompt

beat = {"shot_type": "close_up", "action": "product_reveal"}
style = {"aesthetic": "luxury"}

print(generate_animatic_prompt(beat, style))
# Should output: "object in center of frame, close_up shot, simple line drawing, minimal detail, sketch style, black and white"
```

**Next:** Move to `tasks-phase-2b.md`