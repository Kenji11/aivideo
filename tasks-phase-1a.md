# Phase 1 Tasks - Part A: Template System

**Owner:** Person handling Phase 1  
**Goal:** Create template system and validation service

---

## PR #5: Template JSON Files

### Task 5.1: Create Templates Directory
```bash
mkdir -p backend/app/phases/phase1_validate/templates
```

- [ ] Create `templates/` directory in phase1_validate

### Task 5.2: Create product_showcase.json

**File:** `backend/app/phases/phase1_validate/templates/product_showcase.json`

- [ ] Create file `product_showcase.json`
- [ ] Add name and description fields
- [ ] Add default duration, fps, resolution
- [ ] Add beat #1: hero_shot (0-3s, close_up, product_reveal)
- [ ] Add beat #2: detail_showcase (3-8s, macro, feature_highlight)
- [ ] Add beat #3: lifestyle_context (8-15s, medium, usage_scenario)
- [ ] Add beat #4: brand_moment (15-25s, wide, brand_story)
- [ ] Add beat #5: call_to_action (25-30s, close_up, final_impression)
- [ ] Add transitions array (fade, cut, fade, cut)
- [ ] Add audio configuration (orchestral, moderate, sophisticated)
- [ ] Add color_grading configuration (cinematic_warm.cube)

### Task 5.3: Create lifestyle_ad.json

**File:** `backend/app/phases/phase1_validate/templates/lifestyle_ad.json`

- [ ] Create file `lifestyle_ad.json`
- [ ] Add name and description fields
- [ ] Add default duration, fps, resolution
- [ ] Add beat #1: scene_setter (0-4s, wide, establish_environment)
- [ ] Add beat #2: person_intro (4-9s, medium, introduce_character)
- [ ] Add beat #3: product_interaction (9-17s, close_up, use_product)
- [ ] Add beat #4: benefit_showcase (17-25s, medium, show_benefit)
- [ ] Add beat #5: final_shot (25-30s, close_up, product_branding)
- [ ] Add transitions array (cut, cut, fade, cut)
- [ ] Add audio configuration (upbeat pop, fast, energetic)
- [ ] Add color_grading configuration (modern_vibrant.cube)

### Task 5.4: Create announcement.json

**File:** `backend/app/phases/phase1_validate/templates/announcement.json`

- [ ] Create file `announcement.json`
- [ ] Add name and description fields
- [ ] Add default duration, fps, resolution
- [ ] Add beat #1: attention_grabber (0-5s, wide, dramatic_intro)
- [ ] Add beat #2: message_reveal (5-15s, medium, show_message)
- [ ] Add beat #3: supporting_visual (15-25s, close_up, visual_emphasis)
- [ ] Add beat #4: call_to_action (25-30s, wide, final_message)
- [ ] Add transitions array (fade, fade, cut)
- [ ] Add audio configuration (cinematic epic, moderate, inspiring)
- [ ] Add color_grading configuration (elegant_muted.cube)

### Task 5.5: Create Template Loader Utility

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

- [ ] Import json and Path
- [ ] Define TEMPLATES_DIR constant
- [ ] Implement `load_template()` function
- [ ] Add error handling for missing templates
- [ ] Implement `list_templates()` function
- [ ] Implement `validate_template_choice()` function

---

## PR #6: Phase 1 Schemas

### Task 6.1: Create Phase 1 Schemas

**File:** `backend/app/phases/phase1_validate/schemas.py`
```python
from pydantic import BaseModel
from typing import Dict, List, Optional

class StyleSpec(BaseModel):
    """Visual style specification"""
    aesthetic: str
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
    type: str
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

- [ ] Import BaseModel from pydantic
- [ ] Create StyleSpec model (aesthetic, color_palette, mood, lighting)
- [ ] Create ProductSpec model (name, category)
- [ ] Create AudioSpec model (music_style, tempo, mood)
- [ ] Create BeatSpec model (name, start, duration, shot_type, action, prompt_template, camera_movement)
- [ ] Create TransitionSpec model (type, duration)
- [ ] Create VideoSpec model with all sub-models and uploaded_assets

---

## ✅ PR #5 & #6 Checklist

Before merging:
- [ ] All 3 template JSON files created and valid
- [ ] Template loader utility works
- [ ] All Phase 1 schemas defined
- [ ] Can import and use schemas without errors

**Test Commands:**
```python
# In Python shell
from app.phases.phase1_validate.templates import load_template, list_templates

print(list_templates())
template = load_template('product_showcase')
print(template['name'])
```

**Next:** Move to `tasks-phase-1b.md`