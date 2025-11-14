# Phase 1 Tasks - Part A: Template System

**Owner:** Person handling Phase 1  
**Time Estimate:** 1-2 hours  
**Goal:** Create template system and validation service

---

## Task 1: Create Template JSON Files

### 1.1 Create directory
```bash
mkdir -p backend/app/phases/phase1_validate/templates
```

### 1.2 Create product_showcase.json

**File:** `backend/app/phases/phase1_validate/templates/product_showcase.json`
```json
{
  "name": "product_showcase",
  "description": "Highlights product features and details",
  "default_duration": 30,
  "fps": 30,
  "resolution": "1080p",
  
  "beats": [
    {
      "name": "hero_shot",
      "start": 0,
      "duration": 3,
      "shot_type": "close_up",
      "action": "product_reveal",
      "prompt_template": "{product} on {background}, {style} aesthetic, dramatic reveal",
      "camera_movement": "slow_zoom_in"
    },
    {
      "name": "detail_showcase",
      "start": 3,
      "duration": 5,
      "shot_type": "macro",
      "action": "feature_highlight",
      "prompt_template": "extreme close-up of {product} details, {style} lighting",
      "camera_movement": "pan_across"
    },
    {
      "name": "lifestyle_context",
      "start": 8,
      "duration": 7,
      "shot_type": "medium",
      "action": "usage_scenario",
      "prompt_template": "person using {product} in {setting}, {style} aesthetic",
      "camera_movement": "static"
    },
    {
      "name": "brand_moment",
      "start": 15,
      "duration": 10,
      "shot_type": "wide",
      "action": "brand_story",
      "prompt_template": "{product} in elegant setting, {style} aesthetic, cinematic",
      "camera_movement": "slow_dolly"
    },
    {
      "name": "call_to_action",
      "start": 25,
      "duration": 5,
      "shot_type": "close_up",
      "action": "final_impression",
      "prompt_template": "{product} with brand logo, {style} aesthetic",
      "camera_movement": "static"
    }
  ],
  
  "transitions": [
    {"type": "fade", "duration": 0.5},
    {"type": "cut"},
    {"type": "fade", "duration": 0.5},
    {"type": "cut"}
  ],
  
  "audio": {
    "music_style": "elegant orchestral",
    "tempo": "moderate",
    "mood": "sophisticated"
  },
  
  "color_grading": {
    "lut": "cinematic_warm.cube",
    "contrast": 1.1,
    "saturation": 1.05
  }
}
```

### 1.3 Create lifestyle_ad.json

**File:** `backend/app/phases/phase1_validate/templates/lifestyle_ad.json`
```json
{
  "name": "lifestyle_ad",
  "description": "Shows product in real-world context",
  "default_duration": 30,
  "fps": 30,
  "resolution": "1080p",
  
  "beats": [
    {
      "name": "scene_setter",
      "start": 0,
      "duration": 4,
      "shot_type": "wide",
      "action": "establish_environment",
      "prompt_template": "{setting} with natural lighting, vibrant {style}",
      "camera_movement": "slow_pan"
    },
    {
      "name": "person_intro",
      "start": 4,
      "duration": 5,
      "shot_type": "medium",
      "action": "introduce_character",
      "prompt_template": "person in {setting}, happy and energetic, {style} aesthetic",
      "camera_movement": "follow"
    },
    {
      "name": "product_interaction",
      "start": 9,
      "duration": 8,
      "shot_type": "close_up",
      "action": "use_product",
      "prompt_template": "person using {product}, natural interaction, {style}",
      "camera_movement": "dynamic"
    },
    {
      "name": "benefit_showcase",
      "start": 17,
      "duration": 8,
      "shot_type": "medium",
      "action": "show_benefit",
      "prompt_template": "person enjoying {product} benefit, smile, {style} lighting",
      "camera_movement": "static"
    },
    {
      "name": "final_shot",
      "start": 25,
      "duration": 5,
      "shot_type": "close_up",
      "action": "product_branding",
      "prompt_template": "{product} with logo, clean background, {style}",
      "camera_movement": "static"
    }
  ],
  
  "transitions": [
    {"type": "cut"},
    {"type": "cut"},
    {"type": "fade", "duration": 0.3},
    {"type": "cut"}
  ],
  
  "audio": {
    "music_style": "upbeat pop",
    "tempo": "fast",
    "mood": "energetic"
  },
  
  "color_grading": {
    "lut": "modern_vibrant.cube",
    "contrast": 1.15,
    "saturation": 1.2
  }
}
```

### 1.4 Create announcement.json

**File:** `backend/app/phases/phase1_validate/templates/announcement.json`
```json
{
  "name": "announcement",
  "description": "Brand message or campaign announcement",
  "default_duration": 30,
  "fps": 30,
  "resolution": "1080p",
  
  "beats": [
    {
      "name": "attention_grabber",
      "start": 0,
      "duration": 5,
      "shot_type": "wide",
      "action": "dramatic_intro",
      "prompt_template": "bold graphic design, {style} colors, dramatic lighting",
      "camera_movement": "zoom_in"
    },
    {
      "name": "message_reveal",
      "start": 5,
      "duration": 10,
      "shot_type": "medium",
      "action": "show_message",
      "prompt_template": "text overlay, clean design, {style} aesthetic",
      "camera_movement": "static"
    },
    {
      "name": "supporting_visual",
      "start": 15,
      "duration": 10,
      "shot_type": "close_up",
      "action": "visual_emphasis",
      "prompt_template": "{product} or brand visual, bold {style}",
      "camera_movement": "slow_push"
    },
    {
      "name": "call_to_action",
      "start": 25,
      "duration": 5,
      "shot_type": "wide",
      "action": "final_message",
      "prompt_template": "brand logo and CTA, clean minimal {style}",
      "camera_movement": "static"
    }
  ],
  
  "transitions": [
    {"type": "fade", "duration": 0.5},
    {"type": "fade", "duration": 0.5},
    {"type": "cut"}
  ],
  
  "audio": {
    "music_style": "cinematic epic",
    "tempo": "moderate",
    "mood": "inspiring"
  },
  
  "color_grading": {
    "lut": "elegant_muted.cube",
    "contrast": 1.2,
    "saturation": 0.95
  }
}
```

---

## Task 2: Create Template Loader Utility

**File:** `backend/app/phases/phase1_validate/templates/__init__.py`
```python
import json
from pathlib import Path
from typing import Dict

TEMPLATES_DIR = Path(__file__).parent

def load_template(template_name: str) -> Dict:
    """Load template JSON file"""
    template_path = TEMPLATES_DIR / f"{template_name}.json"
    
    if not template_path.exists():
        raise ValueError(f"Template '{template_name}' not found")
    
    with open(template_path, 'r') as f:
        return json.load(f)

def list_templates() -> list:
    """List available templates"""
    return [
        "product_showcase",
        "lifestyle_ad",
        "announcement"
    ]

def validate_template_choice(template_name: str) -> bool:
    """Check if template exists"""
    return template_name in list_templates()
```

---

## Task 3: Create Phase 1 Schemas

**File:** `backend/app/phases/phase1_validate/schemas.py`
```python
from pydantic import BaseModel
from typing import Dict, List, Optional

class StyleSpec(BaseModel):
    """Visual style specification"""
    aesthetic: str  # e.g., "luxury", "modern", "minimalist"
    color_palette: List[str]
    mood: str
    lighting: str

class ProductSpec(BaseModel):
    """Product information"""
    name: str
    category: str

class AudioSpec(BaseModel):
    """Audio preferences"""
    music_style: str
    tempo: str
    mood: str

class BeatSpec(BaseModel):
    """Single beat/scene specification"""
    name: str
    start: float
    duration: float
    shot_type: str
    action: str
    prompt_template: str
    camera_movement: str

class TransitionSpec(BaseModel):
    """Transition specification"""
    type: str  # "cut", "fade", etc.
    duration: Optional[float] = None

class VideoSpec(BaseModel):
    """Complete video specification"""
    template: str
    duration: int
    resolution: str
    fps: int
    style: StyleSpec
    product: ProductSpec
    beats: List[BeatSpec]
    transitions: List[TransitionSpec]
    audio: AudioSpec
    uploaded_assets: List[Dict] = []
```

---

## ✅ Checkpoint

After completing these tasks, you should have:
- ✅ 3 template JSON files created
- ✅ Template loader utility
- ✅ Phase 1 schemas defined

**Test:**
```python
# In Python shell or test file
from app.phases.phase1_validate.templates import load_template, list_templates

print(list_templates())
# Should print: ['product_showcase', 'lifestyle_ad', 'announcement']

template = load_template('product_showcase')
print(template['name'])
# Should print: product_showcase
```

**Next:** Move to `tasks-phase-1b.md`