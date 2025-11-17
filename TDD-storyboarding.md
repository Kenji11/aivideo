# Technical Design Document (TDD): Intelligent Beat-Based Video Generation

**Version:** 2.0  
**Date:** January 2025  
**Status:** Design Phase  
**Authors:** Video Generation Team

---

## **Table of Contents**

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Beat Library Specification](#3-beat-library-specification)
4. [Template Archetypes](#4-template-archetypes)
5. [Phase 1: Intelligent Planning](#5-phase-1-intelligent-planning)
6. [Phase 2: Storyboard Generation](#6-phase-2-storyboard-generation)
7. [Phase 3: Chunk Generation](#7-phase-3-chunk-generation)
8. [Phase 4: Stitching](#8-phase-4-stitching)
9. [Phase 5: Music Generation](#9-phase-5-music-generation)
10. [Data Models](#10-data-models)
11. [Cost Analysis](#11-cost-analysis)
12. [Testing Strategy](#12-testing-strategy)
13. [Implementation Roadmap](#13-implementation-roadmap)

---

## **1. Executive Summary**

### **1.1 Problem Statement**

Current video generation pipeline suffers from:
- ❌ Narrative drift after chunk 0 (temporal continuity ≠ story coherence)
- ❌ Video models only accept image inputs (no text prompts)
- ❌ Single reference image for entire video (insufficient guidance)
- ❌ Beat specifications ignored during generation
- ❌ Variable chunk durations causing timing issues

### **1.2 Solution Overview**

**New Architecture:**
```
User Prompt → LLM Creative Director → Custom Beat Sequence → Storyboard Images → Video Chunks → Final Video
```

**Key Innovations:**
1. ✅ **Beat Library:** 15 reusable shot types with predefined durations (5s, 10s, 15s only)
2. ✅ **Template Archetypes:** 5 high-level video structures to guide LLM
3. ✅ **Single LLM Agent:** GPT-4 selects archetype AND composes beats in one call
4. ✅ **1:1 Mapping:** Each beat = N chunks = N storyboard images
5. ✅ **Storyboard Anchoring:** One reference image per beat prevents drift

### **1.3 Success Criteria**

- [ ] Videos maintain narrative coherence across all chunks
- [ ] Beat durations align perfectly with chunk boundaries (5s increments)
- [ ] LLM successfully composes appropriate beat sequences for different prompts
- [ ] Storyboard images accurately represent intended shots
- [ ] Total video duration matches user request (±0s tolerance)
- [ ] Cost per video: <$0.50 for 30s video

---

## **2. System Architecture**

### **2.1 Pipeline Overview**

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│  "Create a 15-second ad for Nike sneakers, energetic urban"    │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE 1: INTELLIGENT PLANNING (LLM Agent)           │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Single GPT-4 call:                                  │       │
│  │  1. Analyze intent                                   │       │
│  │  2. Select archetype from library                    │       │
│  │  3. Compose beat sequence from beat library          │       │
│  │  4. Build style specification                        │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                   │
│  Output: Spec with beats [5s, 5s, 5s] = 15s                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 2: STORYBOARD GENERATION                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Beat 1       │  │ Beat 2       │  │ Beat 3       │          │
│  │ → SDXL       │  │ → SDXL       │  │ → SDXL       │          │
│  │ → Image 1    │  │ → Image 2    │  │ → Image 3    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  Output: 3 storyboard images @ 1280x720 (1 per beat)           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PHASE 3: CHUNK GENERATION                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Image 1      │  │ Image 2      │  │ Image 3      │          │
│  │ → Hailuo     │  │ → Hailuo     │  │ → Hailuo     │          │
│  │ → Chunk 1    │  │ → Chunk 2    │  │ → Chunk 3    │          │
│  │   (5s video) │  │   (5s video) │  │   (5s video) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  Output: 3 video chunks @ 1280x720, 30fps                       │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 4: STITCHING (FFmpeg)                   │
│         Chunk 1 + Chunk 2 + Chunk 3 = 15s Final Video           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PHASE 5: MUSIC GENERATION                       │
│       GPT-4 analyzes video → MusicGen → FFmpeg merge            │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
              FINAL VIDEO WITH MUSIC
```

### **2.2 Data Flow**

| Phase | Input | Output | Typical Duration |
|-------|-------|--------|------------------|
| Phase 1 | User prompt | Spec with beats | ~5-10s |
| Phase 2 | Spec | Storyboard images | ~20-30s (3 images) |
| Phase 3 | Storyboard | Video chunks | ~150s (3×50s each) |
| Phase 4 | Chunks | Stitched video | ~5s |
| Phase 5 | Video | Final with music | ~60s |
| **Total** | - | - | **~4-5 min** |

### **2.3 Technology Stack**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Phase 1 LLM** | GPT-4 Turbo | Beat composition & planning |
| **Phase 2 Image Gen** | SDXL | Storyboard generation |
| **Phase 3 Video Gen** | Hailuo 2.3 Fast (default) | Video chunk generation |
| **Phase 3 Video Gen** | Wan 2.5 I2V (alternate) | Backup video model |
| **Phase 5 Music Gen** | Meta MusicGen | Background music |
| **Video Processing** | FFmpeg | Stitching, frame extraction |
| **Storage** | AWS S3 | Asset storage |
| **Database** | PostgreSQL | Video metadata |
| **Task Queue** | Celery + Redis | Async processing |

---

## **3. Beat Library Specification**

### **3.1 Beat Structure**

Each beat in the library has:

```python
{
    "beat_id": str,              # Unique identifier (e.g., "hero_shot")
    "duration": int,             # 5, 10, or 15 seconds ONLY
    "shot_type": str,            # Visual framing (e.g., "close_up", "wide")
    "action": str,               # What happens (e.g., "product_reveal")
    "prompt_template": str,      # Template for SDXL image generation
    "camera_movement": str,      # Camera motion type (e.g., "dolly_in")
    "typical_position": str,     # "opening", "middle", or "closing"
    "compatible_products": list, # Which product types work well
    "energy_level": str,         # "low", "medium", "high"
}
```

### **3.2 Complete Beat Library (15 Beats)**

#### **Opening Beats (5)**

```python
OPENING_BEATS = {
    "hero_shot": {
        "beat_id": "hero_shot",
        "duration": 5,
        "shot_type": "close_up",
        "action": "product_reveal",
        "prompt_template": "Cinematic close-up of {product_name}, dramatic lighting, professional product photography, {style_aesthetic}, premium quality",
        "camera_movement": "slow_dolly_in",
        "typical_position": "opening",
        "compatible_products": ["all"],
        "energy_level": "medium",
    },
    
    "ambient_lifestyle": {
        "beat_id": "ambient_lifestyle",
        "duration": 5,
        "shot_type": "wide",
        "action": "establish_environment",
        "prompt_template": "Wide establishing shot of {setting}, {style_aesthetic}, atmospheric, cinematic composition",
        "camera_movement": "slow_pan",
        "typical_position": "opening",
        "compatible_products": ["lifestyle", "sportswear", "fashion"],
        "energy_level": "low",
    },
    
    "teaser_reveal": {
        "beat_id": "teaser_reveal",
        "duration": 5,
        "shot_type": "extreme_close_up",
        "action": "mysterious_preview",
        "prompt_template": "Extreme close-up of {product_name} detail, mysterious lighting, {style_aesthetic}, intriguing reveal",
        "camera_movement": "push_in",
        "typical_position": "opening",
        "compatible_products": ["luxury", "tech", "fashion"],
        "energy_level": "low",
    },
    
    "dynamic_intro": {
        "beat_id": "dynamic_intro",
        "duration": 5,
        "shot_type": "dynamic",
        "action": "energetic_opening",
        "prompt_template": "Dynamic shot of {product_name} in action, high energy, {style_aesthetic}, explosive beginning",
        "camera_movement": "whip_pan",
        "typical_position": "opening",
        "compatible_products": ["sportswear", "tech", "automotive"],
        "energy_level": "high",
    },
    
    "atmospheric_setup": {
        "beat_id": "atmospheric_setup",
        "duration": 5,
        "shot_type": "wide",
        "action": "mood_establishment",
        "prompt_template": "Atmospheric wide shot, {style_aesthetic} mood, cinematic lighting, setting the tone",
        "camera_movement": "crane_down",
        "typical_position": "opening",
        "compatible_products": ["all"],
        "energy_level": "low",
    },
}
```

#### **Middle Beats - Product Focus (5)**

```python
MIDDLE_PRODUCT_BEATS = {
    "detail_showcase": {
        "beat_id": "detail_showcase",
        "duration": 5,
        "shot_type": "macro",
        "action": "feature_highlight",
        "prompt_template": "Extreme macro shot highlighting details of {product_name}, {style_aesthetic}, premium craftsmanship, high resolution",
        "camera_movement": "pan_across",
        "typical_position": "middle",
        "compatible_products": ["luxury", "tech", "jewelry"],
        "energy_level": "low",
    },
    
    "product_in_motion": {
        "beat_id": "product_in_motion",
        "duration": 5,
        "shot_type": "tracking",
        "action": "dynamic_product",
        "prompt_template": "{product_name} in motion, dynamic movement, {style_aesthetic}, energetic showcase",
        "camera_movement": "tracking_shot",
        "typical_position": "middle",
        "compatible_products": ["sportswear", "automotive", "tech"],
        "energy_level": "high",
    },
    
    "usage_scenario": {
        "beat_id": "usage_scenario",
        "duration": 10,
        "shot_type": "medium",
        "action": "person_using_product",
        "prompt_template": "Person using {product_name} naturally, {style_aesthetic}, authentic interaction, real-world context",
        "camera_movement": "handheld_follow",
        "typical_position": "middle",
        "compatible_products": ["all"],
        "energy_level": "medium",
    },
    
    "lifestyle_context": {
        "beat_id": "lifestyle_context",
        "duration": 10,
        "shot_type": "medium",
        "action": "aspirational_lifestyle",
        "prompt_template": "{product_name} in aspirational lifestyle setting, {style_aesthetic}, emotional connection, premium environment",
        "camera_movement": "slow_orbit",
        "typical_position": "middle",
        "compatible_products": ["luxury", "fashion", "lifestyle"],
        "energy_level": "medium",
    },
    
    "feature_highlight_sequence": {
        "beat_id": "feature_highlight_sequence",
        "duration": 10,
        "shot_type": "medium_close_up",
        "action": "multiple_features",
        "prompt_template": "Showcasing key features of {product_name}, {style_aesthetic}, clear product benefits, informative",
        "camera_movement": "slow_push_in",
        "typical_position": "middle",
        "compatible_products": ["tech", "automotive", "appliances"],
        "energy_level": "medium",
    },
}
```

#### **Middle Beats - Dynamic (3)**

```python
MIDDLE_DYNAMIC_BEATS = {
    "action_montage": {
        "beat_id": "action_montage",
        "duration": 5,
        "shot_type": "dynamic_multi",
        "action": "fast_energy",
        "prompt_template": "Dynamic montage style with {product_name}, fast-paced energy, {style_aesthetic}, exciting visuals",
        "camera_movement": "fast_cuts",
        "typical_position": "middle",
        "compatible_products": ["sportswear", "energy_drinks", "tech"],
        "energy_level": "high",
    },
    
    "benefit_showcase": {
        "beat_id": "benefit_showcase",
        "duration": 5,
        "shot_type": "medium",
        "action": "demonstrate_benefit",
        "prompt_template": "Demonstrating the benefit of {product_name}, {style_aesthetic}, clear value proposition, problem-solution",
        "camera_movement": "static",
        "typical_position": "middle",
        "compatible_products": ["all"],
        "energy_level": "medium",
    },
    
    "transformation_moment": {
        "beat_id": "transformation_moment",
        "duration": 10,
        "shot_type": "medium_wide",
        "action": "before_after",
        "prompt_template": "Transformation enabled by {product_name}, {style_aesthetic}, impactful change, emotional payoff",
        "camera_movement": "reveal",
        "typical_position": "middle",
        "compatible_products": ["beauty", "fitness", "home"],
        "energy_level": "medium",
    },
}
```

#### **Closing Beats (2)**

```python
CLOSING_BEATS = {
    "call_to_action": {
        "beat_id": "call_to_action",
        "duration": 5,
        "shot_type": "close_up",
        "action": "final_impression",
        "prompt_template": "Powerful final shot of {product_name}, {style_aesthetic}, memorable ending, strong brand presence",
        "camera_movement": "static_hold",
        "typical_position": "closing",
        "compatible_products": ["all"],
        "energy_level": "medium",
    },
    
    "brand_moment": {
        "beat_id": "brand_moment",
        "duration": 10,
        "shot_type": "wide_cinematic",
        "action": "brand_story",
        "prompt_template": "Cinematic brand moment with {product_name}, {style_aesthetic}, emotional storytelling, brand values",
        "camera_movement": "crane_up",
        "typical_position": "closing",
        "compatible_products": ["luxury", "automotive", "fashion"],
        "energy_level": "low",
    },
}
```

### **3.3 Complete Beat Library Dictionary**

```python
# File: backend/app/common/beat_library.py

BEAT_LIBRARY = {
    **OPENING_BEATS,
    **MIDDLE_PRODUCT_BEATS,
    **MIDDLE_DYNAMIC_BEATS,
    **CLOSING_BEATS
}

# Total: 15 beats
```

---

## **4. Template Archetypes**

### **4.1 Archetype Structure**

```python
{
    "archetype_id": str,
    "name": str,
    "description": str,
    "typical_duration_range": tuple,  # (min, max) seconds
    "suggested_beat_sequence": list,  # Default beat order (LLM can deviate)
    "typical_products": list,
    "style_hints": list,
    "energy_curve": str,  # "building", "steady", "peaking"
    "narrative_structure": str,
}
```

### **4.2 Five Core Archetypes**

```python
# File: backend/app/common/template_archetypes.py

TEMPLATE_ARCHETYPES = {
    "luxury_showcase": {
        "archetype_id": "luxury_showcase",
        "name": "Luxury Product Showcase",
        "description": "Elegant, cinematic product reveal for premium goods. Emphasizes craftsmanship, quality, and aspiration.",
        "typical_duration_range": (15, 30),
        "suggested_beat_sequence": [
            "hero_shot",           # 5s
            "detail_showcase",     # 5s
            "lifestyle_context",   # 10s
            "call_to_action"       # 5s
        ],  # Total: 25s
        "typical_products": ["watches", "jewelry", "luxury_cars", "high_end_fashion", "premium_tech"],
        "style_hints": ["elegant", "sophisticated", "premium", "minimalist", "cinematic"],
        "energy_curve": "steady",
        "narrative_structure": "reveal → appreciate → aspire → desire",
    },
    
    "energetic_lifestyle": {
        "archetype_id": "energetic_lifestyle",
        "name": "Energetic Lifestyle Ad",
        "description": "High-energy, dynamic advertising for active products. Fast-paced, motivational, real-world usage.",
        "typical_duration_range": (10, 20),
        "suggested_beat_sequence": [
            "dynamic_intro",       # 5s
            "action_montage",      # 5s
            "product_in_motion",   # 5s
            "call_to_action"       # 5s
        ],  # Total: 20s
        "typical_products": ["sportswear", "sneakers", "fitness_equipment", "energy_drinks", "outdoor_gear"],
        "style_hints": ["energetic", "vibrant", "dynamic", "authentic", "motivational"],
        "energy_curve": "building",
        "narrative_structure": "excite → engage → empower → inspire",
    },
    
    "minimalist_reveal": {
        "archetype_id": "minimalist_reveal",
        "name": "Minimalist Product Reveal",
        "description": "Clean, simple, focused product presentation. Lets the product speak for itself through elegant simplicity.",
        "typical_duration_range": (10, 20),
        "suggested_beat_sequence": [
            "hero_shot",           # 5s
            "detail_showcase",     # 5s
            "call_to_action"       # 5s
        ],  # Total: 15s
        "typical_products": ["tech_gadgets", "design_objects", "skincare", "minimal_fashion", "smart_devices"],
        "style_hints": ["minimalist", "clean", "modern", "simple", "focused"],
        "energy_curve": "steady",
        "narrative_structure": "reveal → appreciate → conclude",
    },
    
    "emotional_storytelling": {
        "archetype_id": "emotional_storytelling",
        "name": "Emotional Brand Storytelling",
        "description": "Narrative-driven ad focused on emotional connection. Shows how product fits into life moments.",
        "typical_duration_range": (20, 30),
        "suggested_beat_sequence": [
            "atmospheric_setup",      # 5s
            "usage_scenario",         # 10s
            "transformation_moment",  # 10s
            "call_to_action"          # 5s
        ],  # Total: 30s
        "typical_products": ["family_products", "healthcare", "home_goods", "insurance", "nonprofits"],
        "style_hints": ["emotional", "authentic", "warm", "human", "heartfelt"],
        "energy_curve": "building",
        "narrative_structure": "relate → connect → transform → remember",
    },
    
    "feature_demo": {
        "archetype_id": "feature_demo",
        "name": "Feature-Focused Demonstration",
        "description": "Informative showcase of product capabilities. Clear, educational, benefit-driven.",
        "typical_duration_range": (15, 30),
        "suggested_beat_sequence": [
            "hero_shot",                    # 5s
            "feature_highlight_sequence",   # 10s
            "benefit_showcase",             # 5s
            "call_to_action"                # 5s
        ],  # Total: 25s
        "typical_products": ["tech_products", "appliances", "software", "tools", "automotive"],
        "style_hints": ["informative", "clear", "professional", "modern", "benefit-driven"],
        "energy_curve": "steady",
        "narrative_structure": "introduce → demonstrate → explain → convince",
    },
}
```

---

## **5. Phase 1: Intelligent Planning**

### **5.1 Overview**

Phase 1 uses a **single GPT-4 agent** to:
1. Analyze user intent
2. Select appropriate archetype from library
3. Compose custom beat sequence from beat library
4. Build complete style specification

**No hardcoded selection logic** - LLM makes all decisions.

### **5.2 Configuration**

```python
# File: backend/app/common/constants.py

# Creativity control (0.0 = strict, 1.0 = creative)
BEAT_COMPOSITION_CREATIVITY = float(os.getenv('BEAT_COMPOSITION_CREATIVITY', 0.5))

# Temperature mapping: creativity → LLM temperature
# 0.0 → 0.2 (strict template adherence)
# 0.5 → 0.5 (balanced adaptation) [DEFAULT]
# 1.0 → 0.8 (creative reinterpretation)
def get_planning_temperature(creativity: float) -> float:
    return 0.2 + (creativity * 0.6)
```

### **5.3 Input/Output**

**Input:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "prompt": "Create a 15-second ad for Nike sneakers, energetic and urban style",
    "creativity_level": 0.5  # Optional, defaults to config value
}
```

**Output:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "phase": "phase1_planning",
    "status": "success",
    "cost_usd": 0.02,
    "duration_seconds": 5.3,
    "output_data": {
        "spec": {
            "template": "energetic_lifestyle",
            "duration": 15,
            "fps": 30,
            "resolution": "1280x720",
            "product": {
                "name": "Nike sneakers",
                "category": "sportswear"
            },
            "style": {
                "aesthetic": "energetic and athletic",
                "color_palette": ["black", "white", "neon green"],
                "mood": "energetic",
                "lighting": "urban night lighting, dynamic"
            },
            "beats": [
                {
                    "beat_id": "action_montage",
                    "name": "action_montage",
                    "start": 0,
                    "duration": 5,
                    "shot_type": "dynamic_multi",
                    "action": "fast_energy",
                    "prompt_template": "Dynamic montage style with Nike sneakers, fast-paced energy, energetic and athletic, exciting visuals",
                    "camera_movement": "fast_cuts",
                    "typical_position": "middle",
                    "energy_level": "high"
                },
                {
                    "beat_id": "product_in_motion",
                    "name": "product_in_motion",
                    "start": 5,
                    "duration": 5,
                    "shot_type": "tracking",
                    "action": "dynamic_product",
                    "prompt_template": "Nike sneakers in motion, dynamic movement, energetic and athletic, energetic showcase",
                    "camera_movement": "tracking_shot",
                    "typical_position": "middle",
                    "energy_level": "high"
                },
                {
                    "beat_id": "call_to_action",
                    "name": "call_to_action",
                    "start": 10,
                    "duration": 5,
                    "shot_type": "close_up",
                    "action": "final_impression",
                    "prompt_template": "Powerful final shot of Nike sneakers, energetic and athletic, memorable ending, strong brand presence",
                    "camera_movement": "static_hold",
                    "typical_position": "closing",
                    "energy_level": "medium"
                }
            ],
            "llm_reasoning": {
                "selected_archetype": "energetic_lifestyle",
                "archetype_reasoning": "Product is sportswear (Nike sneakers) with 'energetic' and 'urban' style keywords, which aligns perfectly with the energetic_lifestyle archetype.",
                "beat_selection_reasoning": "Used high-energy beats (action_montage, product_in_motion) to match the 'energetic' request, with a strong closing beat."
            }
        }
    }
}
```

### **5.4 Implementation**

**File:** `backend/app/phases/phase1_planning/task.py`

```python
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.services.openai import openai_client
from app.common.beat_library import BEAT_LIBRARY
from app.common.template_archetypes import TEMPLATE_ARCHETYPES
from app.common.constants import BEAT_COMPOSITION_CREATIVITY, get_planning_temperature
import json
import time
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def plan_video_intelligent(
    self,
    video_id: str,
    prompt: str,
    creativity_level: float = None
) -> dict:
    """
    Phase 1: Intelligent video planning using single LLM agent.
    
    Args:
        video_id: Unique video identifier
        prompt: Natural language user prompt
        creativity_level: 0.0-1.0 (strict to creative), defaults to config
        
    Returns:
        PhaseOutput dict with complete video spec
    """
    start_time = time.time()
    
    if creativity_level is None:
        creativity_level = BEAT_COMPOSITION_CREATIVITY
    
    logger.info(f"Phase 1 starting for video {video_id}")
    logger.info(f"Prompt: {prompt}")
    logger.info(f"Creativity level: {creativity_level}")
    
    try:
        # Build LLM system prompt
        system_prompt = build_planning_system_prompt()
        
        # Build user message
        user_message = f"Create a video advertisement: {prompt}"
        
        # Calculate temperature
        temperature = get_planning_temperature(creativity_level)
        
        logger.info(f"Calling GPT-4 with temperature={temperature}")
        
        # Call GPT-4
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=temperature
        )
        
        # Parse response
        llm_output = json.loads(response.choices[0].message.content)
        
        logger.info(f"LLM selected archetype: {llm_output.get('selected_archetype')}")
        logger.info(f"LLM composed {len(llm_output.get('beat_sequence', []))} beats")
        
        # Build full spec from LLM output
        spec = build_full_spec(llm_output, video_id)
        
        # Validate spec
        validate_spec(spec)
        
        logger.info(f"Phase 1 complete for video {video_id}")
        
        # Success
        return PhaseOutput(
            video_id=video_id,
            phase="phase1_planning",
            status="success",
            output_data={"spec": spec},
            cost_usd=0.02,  # GPT-4 Turbo cost
            duration_seconds=time.time() - start_time,
            error_message=None
        ).dict()
        
    except Exception as e:
        logger.error(f"Phase 1 failed for video {video_id}: {str(e)}")
        
        # Failure
        return PhaseOutput(
            video_id=video_id,
            phase="phase1_planning",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        ).dict()


def build_planning_system_prompt() -> str:
    """Build comprehensive system prompt for planning LLM"""
    
    return f"""
You are a professional video director and creative strategist. Your job is to plan a complete video advertisement based on the user's request.

===== AVAILABLE TEMPLATE ARCHETYPES =====

{json.dumps(TEMPLATE_ARCHETYPES, indent=2)}

===== AVAILABLE BEATS =====

{json.dumps(BEAT_LIBRARY, indent=2)}

===== YOUR TASK =====

Given the user's prompt, you must:

1. **Understand Intent**
   - Extract: product name, category, desired duration (default 30s if not specified)
   - Identify: style keywords, mood, energy level, key message

2. **Select Archetype**
   - Choose the archetype that best matches the product, mood, and style
   - Consider: product category, style keywords, desired energy level
   - You can choose ANY archetype from the library above

3. **Compose Beat Sequence**
   - Use beats from the library to create a compelling narrative
   - CRITICAL CONSTRAINTS:
     * Total duration MUST equal user's requested duration (or 30s default)
     * Each beat MUST be 5s, 10s, or 15s (NO other durations allowed)
     * First beat should typically be from opening beats (typical_position: "opening")
     * Last beat should typically be from closing beats (typical_position: "closing")
     * Middle beats from middle beats (typical_position: "middle")
     * Sum of all beat durations MUST equal total duration EXACTLY
   - Follow the selected archetype's narrative_structure
   - Maintain appropriate energy_curve
   - Ensure beat_ids match exactly those in the AVAILABLE BEATS library

4. **Build Style Specification**
   - Define: aesthetic (string describing overall visual style)
   - color_palette: array of 3-5 color names
   - mood: single word mood (energetic|elegant|minimalist|emotional|informative)
   - lighting: lighting style description
   - Ensure style matches the archetype and user's keywords

===== OUTPUT FORMAT =====

Return a JSON object with this EXACT structure:

{{
  "intent_analysis": {{
    "product": {{
      "name": "exact product name from prompt",
      "category": "category (e.g., sportswear, luxury, tech)"
    }},
    "duration": 15,
    "style_keywords": ["keyword1", "keyword2"],
    "mood": "energetic",
    "key_message": "brief description of what user wants to convey"
  }},
  "selected_archetype": "archetype_id",
  "archetype_reasoning": "1-2 sentence explanation of why you chose this archetype",
  "beat_sequence": [
    {{"beat_id": "hero_shot", "duration": 5}},
    {{"beat_id": "detail_showcase", "duration": 5}},
    {{"beat_id": "call_to_action", "duration": 5}}
  ],
  "beat_selection_reasoning": "1-2 sentence explanation of your beat choices",
  "style": {{
    "aesthetic": "description matching archetype and user intent",
    "color_palette": ["color1", "color2", "color3"],
    "mood": "mood matching user intent",
    "lighting": "lighting style description"
  }}
}}

===== VALIDATION CHECKLIST =====

Before returning, verify:
- ✓ Sum of beat durations == requested duration
- ✓ All beat_ids exist in BEAT_LIBRARY
- ✓ First beat has typical_position: "opening" (recommended)
- ✓ Last beat has typical_position: "closing" (recommended)
- ✓ All beat durations are 5, 10, or 15 seconds
- ✓ Style matches selected archetype and user keywords

If validation fails, adjust your beat sequence until it passes.
"""


def build_full_spec(llm_output: dict, video_id: str) -> dict:
    """
    Convert LLM output into full video specification.
    
    Fills in beat details from library and adds prompt templates.
    """
    
    intent = llm_output['intent_analysis']
    beat_sequence = llm_output['beat_sequence']
    style = llm_output['style']
    
    # Build beats with full details from library
    current_time = 0
    full_beats = []
    
    for beat_info in beat_sequence:
        beat_id = beat_info['beat_id']
        duration = beat_info['duration']
        
        # Get beat template from library
        if beat_id not in BEAT_LIBRARY:
            raise ValueError(f"Invalid beat_id: {beat_id}")
        
        beat_template = BEAT_LIBRARY[beat_id]
        
        # Build full beat
        beat = {
            **beat_template,  # Copy all fields from library
            "start": current_time,
            "duration": duration
        }
        
        # Fill in prompt template with actual product/style
        beat['prompt_template'] = beat['prompt_template'].format(
            product_name=intent['product']['name'],
            style_aesthetic=style['aesthetic'],
            setting=f"{style['mood']} setting"
        )
        
        full_beats.append(beat)
        current_time += duration
    
    # Assemble final spec
    spec = {
        "template": llm_output['selected_archetype'],
        "duration": current_time,
        "fps": 30,
        "resolution": "1280x720",
        "product": intent['product'],
        "style": style,
        "beats": full_beats,
        "llm_reasoning": {
            "selected_archetype": llm_output['selected_archetype'],
            "archetype_reasoning": llm_output['archetype_reasoning'],
            "beat_selection_reasoning": llm_output['beat_selection_reasoning']
        }
    }
    
    return spec


def validate_spec(spec: dict):
    """
    Validate spec meets all constraints.
    Raises exception if invalid.
    """
    
    beats = spec['beats']
    duration = spec['duration']
    
    # Check 1: Duration sums correctly
    total = sum(b['duration'] for b in beats)
    if total != duration:
        raise ValueError(f"Beat durations sum to {total}s, expected {duration}s")
    
    # Check 2: All beat durations valid (5, 10, or 15 seconds)
    for beat in beats:
        if beat['duration'] not in [5, 10, 15]:
            raise ValueError(f"Beat '{beat['beat_id']}' has invalid duration {beat['duration']}s (must be 5, 10, or 15)")
    
    # Check 3: Beat IDs exist in library
    for beat in beats:
        if beat['beat_id'] not in BEAT_LIBRARY:
            raise ValueError(f"Unknown beat_id: {beat['beat_id']}")
    
    # Check 4: At least one beat
    if len(beats) < 1:
        raise ValueError("Spec must have at least one beat")
    
    # Warnings (not errors)
    first_beat = BEAT_LIBRARY[beats[0]['beat_id']]
    last_beat = BEAT_LIBRARY[beats[-1]['beat_id']]
    
    if first_beat['typical_position'] not in ['opening', 'middle']:
        logger.warning(f"First beat '{beats[0]['beat_id']}' typically not used as opening")
    
    if last_beat['typical_position'] != 'closing':
        logger.warning(f"Last beat '{beats[-1]['beat_id']}' typically not used as closing")
    
    logger.info("Spec validation passed")
```

### **5.5 Test Cases**

| Test ID | Prompt | Creativity | Expected Archetype | Expected Duration | Expected Beats |
|---------|--------|-----------|-------------------|-------------------|----------------|
| TC1.1 | "15s Nike sneakers energetic" | 0.5 | energetic_lifestyle | 15s | 3 beats (5+5+5) |
| TC1.2 | "30s luxury watch elegant" | 0.5 | luxury_showcase | 30s | 4-6 beats |
| TC1.3 | "20s iPhone minimalist clean" | 0.5 | minimalist_reveal | 20s | 4 beats (5+5+5+5) |
| TC1.4 | "25s family car emotional story" | 0.5 | emotional_storytelling | 25s | 3-4 beats |
| TC1.5 | "No duration, new laptop features" | 0.5 | feature_demo | 30s (default) | 4-6 beats |
| TC1.6 | "15s Nike" (creativity=0.0) | 0.0 | energetic_lifestyle | 15s | Exact archetype template |
| TC1.7 | "15s Nike" (creativity=1.0) | 1.0 | Any archetype | 15s | Creative interpretation |

---

## **6. Phase 2: Storyboard Generation**

### **6.1 Overview**

Generate one high-quality 1280x720 storyboard image per beat using SDXL.

**Key Principle:** 1 beat = 1 image

### **6.2 Input/Output**

**Input:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "spec": { /* from Phase 1 */ }
}
```

**Output:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "phase": "phase2_storyboard",
    "status": "success",
    "cost_usd": 0.0165,  # 3 images × $0.0055
    "duration_seconds": 25.3,
    "output_data": {
        "storyboard_images": [
            {
                "beat_id": "action_montage",
                "beat_name": "action_montage",
                "start": 0,
                "duration": 5,
                "image_url": "s3://bucket/videos/{video_id}/storyboard/action_montage.png",
                "shot_type": "dynamic_multi",
                "prompt_used": "Dynamic montage style with Nike sneakers..."
            },
            {
                "beat_id": "product_in_motion",
                "beat_name": "product_in_motion",
                "start": 5,
                "duration": 5,
                "image_url": "s3://bucket/videos/{video_id}/storyboard/product_in_motion.png",
                "shot_type": "tracking",
                "prompt_used": "Nike sneakers in motion..."
            },
            {
                "beat_id": "call_to_action",
                "beat_name": "call_to_action",
                "start": 10,
                "duration": 5,
                "image_url": "s3://bucket/videos/{video_id}/storyboard/call_to_action.png",
                "shot_type": "close_up",
                "prompt_used": "Powerful final shot of Nike sneakers..."
            }
        ]
    }
}
```

### **6.3 Implementation**

**File:** `backend/app/phases/phase2_storyboard/task.py`

```python
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.common.constants import COST_SDXL_IMAGE
import tempfile
import requests
import time
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def generate_storyboard(self, video_id: str, spec: dict) -> dict:
    """
    Phase 2: Generate storyboard images for all beats.
    
    Args:
        video_id: Unique video identifier
        spec: Video specification from Phase 1
        
    Returns:
        PhaseOutput dict with storyboard image URLs
    """
    start_time = time.time()
    
    beats = spec['beats']
    style = spec['style']
    product = spec['product']
    
    logger.info(f"Phase 2 starting for video {video_id}")
    logger.info(f"Generating {len(beats)} storyboard images")
    
    try:
        storyboard_images = []
        total_cost = 0.0
        
        for i, beat in enumerate(beats):
            logger.info(f"Generating storyboard {i+1}/{len(beats)}: {beat['beat_id']}")
            
            # Generate image for this beat
            image_url, prompt_used = generate_beat_image(
                video_id=video_id,
                beat=beat,
                style=style,
                product=product
            )
            
            storyboard_images.append({
                "beat_id": beat['beat_id'],
                "beat_name": beat['name'],
                "start": beat['start'],
                "duration": beat['duration'],
                "image_url": image_url,
                "shot_type": beat['shot_type'],
                "prompt_used": prompt_used
            })
            
            total_cost += COST_SDXL_IMAGE
        
        logger.info(f"Phase 2 complete for video {video_id}")
        logger.info(f"Generated {len(storyboard_images)} images, total cost ${total_cost:.4f}")
        
        # Success
        return PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="success",
            output_data={"storyboard_images": storyboard_images},
            cost_usd=total_cost,
            duration_seconds=time.time() - start_time,
            error_message=None
        ).dict()
        
    except Exception as e:
        logger.error(f"Phase 2 failed for video {video_id}: {str(e)}")
        
        # Failure
        return PhaseOutput(
            video_id=video_id,
            phase="phase2_storyboard",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        ).dict()


def generate_beat_image(
    video_id: str,
    beat: dict,
    style: dict,
    product: dict
) -> tuple[str, str]:
    """
    Generate storyboard image for a single beat.
    
    Returns:
        (image_url, prompt_used)
    """
    
    # Beat already has prompt_template filled in from Phase 1
    base_prompt = beat['prompt_template']
    
    # Add style enhancements
    colors = ', '.join(style.get('color_palette', ['modern colors']))
    lighting = style.get('lighting', 'natural lighting')
    
    # Compose final prompt
    full_prompt = (
        f"{base_prompt}, "
        f"{colors} color palette, "
        f"{lighting}, "
        f"cinematic composition, "
        f"high quality professional photography, "
        f"1280x720 aspect ratio, "
        f"{beat['shot_type']} framing"
    )
    
    # Negative prompt
    negative_prompt = (
        "blurry, low quality, distorted, deformed, ugly, amateur, "
        "watermark, text, signature, letters, words, multiple subjects, "
        "cluttered, busy, messy, chaotic"
    )
    
    logger.info(f"SDXL prompt for '{beat['beat_id']}': {full_prompt[:100]}...")
    
    # Generate with SDXL
    output = replicate_client.run(
        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        input={
            "prompt": full_prompt,
            "negative_prompt": negative_prompt,
            "width": 1280,
            "height": 720,
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "scheduler": "K_EULER"
        }
    )
    
    # Download image from Replicate
    image_url = output[0]
    image_data = requests.get(image_url).content
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp:
        tmp.write(image_data)
        tmp_path = tmp.name
    
    # Upload to S3
    s3_key = f"videos/{video_id}/storyboard/{beat['beat_id']}.png"
    s3_url = s3_client.upload_file(tmp_path, s3_key)
    
    logger.info(f"Storyboard image uploaded: {s3_url}")
    
    return (s3_url, full_prompt)
```

### **6.4 Test Cases**

| Test ID | Spec Beats | Expected Images | Expected Cost |
|---------|-----------|----------------|---------------|
| TC2.1 | 3 beats (15s video) | 3 images | $0.0165 |
| TC2.2 | 6 beats (30s video) | 6 images | $0.033 |
| TC2.3 | 1 beat (5s video) | 1 image | $0.0055 |
| TC2.4 | Empty beats | Error | $0 |

---

## **7. Phase 3: Chunk Generation**

### **7.1 Overview**

Generate video chunks from storyboard images using Hailuo (or Wan).

**Key Principles:**
- Each beat with duration `D` → `ceil(D/5)` chunks
- First chunk of each beat uses storyboard image
- Subsequent chunks within same beat use last frame of previous chunk
- All chunks are exactly 5 seconds

### **7.2 Chunk Mapping Logic**

**Example 1: 15s video, 3 beats of 5s each**
```
Beat 1 (5s): action_montage
  └─ Chunk 0 (0-5s): Input = storyboard_action_montage.png

Beat 2 (5s): product_in_motion
  └─ Chunk 1 (5-10s): Input = storyboard_product_in_motion.png

Beat 3 (5s): call_to_action
  └─ Chunk 2 (10-15s): Input = storyboard_call_to_action.png

Result: 3 chunks, 3 storyboard images used
```

**Example 2: 25s video, mixed beat durations**
```
Beat 1 (5s): hero_shot
  └─ Chunk 0 (0-5s): Input = storyboard_hero_shot.png

Beat 2 (10s): lifestyle_context
  ├─ Chunk 1 (5-10s): Input = storyboard_lifestyle_context.png
  └─ Chunk 2 (10-15s): Input = last_frame_of_chunk_1.png

Beat 3 (10s): brand_moment
  ├─ Chunk 3 (15-20s): Input = storyboard_brand_moment.png
  └─ Chunk 4 (20-25s): Input = last_frame_of_chunk_3.png

Result: 5 chunks, 3 storyboard images used
```

### **7.3 Input/Output**

**Input:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "spec": { /* from Phase 1 */ },
    "storyboard": { /* from Phase 2 */ }
}
```

**Output:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "phase": "phase3_chunks",
    "status": "success",
    "cost_usd": 0.12,  # 3 chunks × $0.04
    "duration_seconds": 155.2,
    "output_data": {
        "chunks": [
            {
                "chunk_idx": 0,
                "beat_id": "action_montage",
                "start": 0,
                "duration": 5,
                "url": "s3://bucket/videos/{video_id}/chunks/chunk_00.mp4",
                "input_type": "storyboard",
                "input_url": "s3://bucket/videos/{video_id}/storyboard/action_montage.png"
            },
            {
                "chunk_idx": 1,
                "beat_id": "product_in_motion",
                "start": 5,
                "duration": 5,
                "url": "s3://bucket/videos/{video_id}/chunks/chunk_01.mp4",
                "input_type": "storyboard",
                "input_url": "s3://bucket/videos/{video_id}/storyboard/product_in_motion.png"
            },
            {
                "chunk_idx": 2,
                "beat_id": "call_to_action",
                "start": 10,
                "duration": 5,
                "url": "s3://bucket/videos/{video_id}/chunks/chunk_02.mp4",
                "input_type": "storyboard",
                "input_url": "s3://bucket/videos/{video_id}/storyboard/call_to_action.png"
            }
        ]
    }
}
```

### **7.4 Implementation**

**File:** `backend/app/phases/phase3_chunks/task.py`

```python
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.services.replicate import replicate_client
from app.services.s3 import s3_client
from app.services.ffmpeg import ffmpeg_service
from app.common.constants import DEFAULT_MODEL
from app.common.model_configs import MODEL_CONFIGS
import tempfile
import time
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def generate_chunks(self, video_id: str, spec: dict, storyboard: dict) -> dict:
    """
    Phase 3: Generate video chunks from storyboard images.
    
    Args:
        video_id: Unique video identifier
        spec: Video specification from Phase 1
        storyboard: Storyboard data from Phase 2
        
    Returns:
        PhaseOutput dict with chunk URLs
    """
    start_time = time.time()
    
    beats = spec['beats']
    storyboard_images = {
        img['beat_id']: img['image_url']
        for img in storyboard['storyboard_images']
    }
    
    model = DEFAULT_MODEL
    model_config = MODEL_CONFIGS[model]
    
    logger.info(f"Phase 3 starting for video {video_id}")
    logger.info(f"Using model: {model}")
    logger.info(f"Processing {len(beats)} beats")
    
    try:
        chunks = []
        total_cost = 0.0
        
        for beat in beats:
            logger.info(f"Processing beat '{beat['beat_id']}' ({beat['duration']}s)")
            
            # How many chunks does this beat need?
            num_chunks = beat['duration'] // 5
            
            for chunk_idx_in_beat in range(num_chunks):
                chunk_start = beat['start'] + (chunk_idx_in_beat * 5)
                global_chunk_idx = len(chunks)
                
                # Determine input image
                if chunk_idx_in_beat == 0:
                    # First chunk of beat: use storyboard image
                    input_image = storyboard_images[beat['beat_id']]
                    input_type = "storyboard"
                else:
                    # Subsequent chunks: use last frame of previous chunk
                    input_image = extract_last_frame(chunks[-1]['url'], video_id, global_chunk_idx)
                    input_type = "previous_frame"
                
                logger.info(f"  Chunk {global_chunk_idx} ({chunk_start}s): input_type={input_type}")
                
                # Generate video chunk
                chunk_url = generate_video_chunk(
                    video_id=video_id,
                    chunk_idx=global_chunk_idx,
                    input_image=input_image,
                    model=model
                )
                
                chunks.append({
                    "chunk_idx": global_chunk_idx,
                    "beat_id": beat['beat_id'],
                    "start": chunk_start,
                    "duration": 5,
                    "url": chunk_url,
                    "input_type": input_type,
                    "input_url": input_image
                })
                
                total_cost += model_config['cost_per_generation']
        
        logger.info(f"Phase 3 complete for video {video_id}")
        logger.info(f"Generated {len(chunks)} chunks, total cost ${total_cost:.2f}")
        
        # Success
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="success",
            output_data={"chunks": chunks},
            cost_usd=total_cost,
            duration_seconds=time.time() - start_time,
            error_message=None
        ).dict()
        
    except Exception as e:
        logger.error(f"Phase 3 failed for video {video_id}: {str(e)}")
        
        # Failure
        return PhaseOutput(
            video_id=video_id,
            phase="phase3_chunks",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        ).dict()


def generate_video_chunk(
    video_id: str,
    chunk_idx: int,
    input_image: str,
    model: str
) -> str:
    """
    Generate a single 5s video chunk from input image.
    
    Args:
        video_id: Video ID
        chunk_idx: Chunk index
        input_image: S3 URL of input image
        model: Model name (e.g., "hailuo", "wan")
        
    Returns:
        S3 URL of generated video chunk
    """
    
    config = MODEL_CONFIGS[model]
    
    # Download input image to temp file
    input_path = download_from_s3(input_image)
    
    logger.info(f"Generating chunk {chunk_idx} with {model}")
    
    # Generate video (IMAGE ONLY - no text prompt!)
    with open(input_path, 'rb') as f:
        output = replicate_client.run(
            config['replicate_model'],
            input={
                config['param_names']['image']: f,
                **config['params']
            }
        )
    
    # Download video from Replicate
    video_url = output if isinstance(output, str) else output[0]
    video_data = requests.get(video_url).content
    
    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(video_data)
        tmp_path = tmp.name
    
    # Upload to S3
    s3_key = f"videos/{video_id}/chunks/chunk_{chunk_idx:02d}.mp4"
    s3_url = s3_client.upload_file(tmp_path, s3_key)
    
    logger.info(f"Chunk {chunk_idx} uploaded: {s3_url}")
    
    return s3_url


def extract_last_frame(video_url: str, video_id: str, chunk_idx: int) -> str:
    """
    Extract last frame from video chunk.
    
    Args:
        video_url: S3 URL of video
        video_id: Video ID
        chunk_idx: Current chunk index
        
    Returns:
        S3 URL of extracted frame image
    """
    
    # Download video
    video_path = download_from_s3(video_url)
    
    # Extract last frame with ffmpeg
    output_path = tempfile.mktemp(suffix='.png')
    
    ffmpeg_service.run_command([
        'ffmpeg',
        '-sseof', '-0.1',  # 0.1 seconds before end
        '-i', video_path,
        '-update', '1',
        '-q:v', '1',  # High quality
        '-frames:v', '1',
        output_path
    ])
    
    # Upload to S3
    s3_key = f"videos/{video_id}/frames/chunk_{chunk_idx}_last_frame.png"
    s3_url = s3_client.upload_file(output_path, s3_key)
    
    logger.info(f"Extracted last frame from chunk {chunk_idx}: {s3_url}")
    
    return s3_url


def download_from_s3(s3_url: str) -> str:
    """Download file from S3 to temp location"""
    
    # Extract bucket and key from s3:// URL
    # s3://bucket/path/to/file.ext → bucket, path/to/file.ext
    parts = s3_url.replace('s3://', '').split('/', 1)
    bucket = parts[0]
    key = parts[1]
    
    # Download to temp
    suffix = os.path.splitext(key)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = tmp.name
    
    s3_client.client.download_file(bucket, key, tmp_path)
    
    return tmp_path
```

### **7.5 Test Cases**

| Test ID | Beats | Expected Chunks | Expected Cost (Hailuo) |
|---------|-------|----------------|------------------------|
| TC3.1 | 3 beats × 5s | 3 chunks | $0.12 (3 × $0.04) |
| TC3.2 | 2 beats × 5s + 1 beat × 10s | 4 chunks | $0.16 (4 × $0.04) |
| TC3.3 | 1 beat × 15s | 3 chunks | $0.12 (3 × $0.04) |
| TC3.4 | 6 beats × 5s | 6 chunks | $0.24 (6 × $0.04) |

---

## **8. Phase 4: Stitching**

### **8.1 Overview**

Stitch all video chunks into a single continuous video using FFmpeg.

### **8.2 Input/Output**

**Input:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "chunks": [ /* from Phase 3 */ ]
}
```

**Output:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "phase": "phase4_stitching",
    "status": "success",
    "cost_usd": 0.0,  # No API cost
    "duration_seconds": 3.2,
    "output_data": {
        "stitched_url": "s3://bucket/videos/{video_id}/stitched.mp4",
        "total_duration": 15.0,
        "resolution": "1280x720",
        "fps": 30
    }
}
```

### **8.3 Implementation**

**File:** `backend/app/phases/phase4_stitching/task.py`

```python
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.services.ffmpeg import ffmpeg_service
from app.services.s3 import s3_client
import tempfile
import time
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def stitch_chunks(self, video_id: str, chunks: list) -> dict:
    """
    Phase 4: Stitch video chunks into final video.
    
    Args:
        video_id: Unique video identifier
        chunks: List of chunk dicts from Phase 3
        
    Returns:
        PhaseOutput dict with stitched video URL
    """
    start_time = time.time()
    
    logger.info(f"Phase 4 starting for video {video_id}")
    logger.info(f"Stitching {len(chunks)} chunks")
    
    try:
        # Download all chunks
        chunk_paths = []
        for chunk in chunks:
            path = download_from_s3(chunk['url'])
            chunk_paths.append(path)
        
        # Create concat file list
        concat_file = tempfile.mktemp(suffix='.txt')
        with open(concat_file, 'w') as f:
            for path in chunk_paths:
                f.write(f"file '{path}'\n")
        
        # Stitch with FFmpeg
        output_path = tempfile.mktemp(suffix='.mp4')
        
        ffmpeg_service.run_command([
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',  # Copy streams (fast, no re-encode)
            output_path
        ])
        
        logger.info(f"Chunks stitched successfully")
        
        # Upload to S3
        s3_key = f"videos/{video_id}/stitched.mp4"
        stitched_url = s3_client.upload_file(output_path, s3_key)
        
        # Get video info
        total_duration = len(chunks) * 5.0  # All chunks are 5s
        
        logger.info(f"Phase 4 complete for video {video_id}")
        logger.info(f"Stitched video: {stitched_url}")
        
        # Success
        return PhaseOutput(
            video_id=video_id,
            phase="phase4_stitching",
            status="success",
            output_data={
                "stitched_url": stitched_url,
                "total_duration": total_duration,
                "resolution": "1280x720",
                "fps": 30
            },
            cost_usd=0.0,  # No API cost for stitching
            duration_seconds=time.time() - start_time,
            error_message=None
        ).dict()
        
    except Exception as e:
        logger.error(f"Phase 4 failed for video {video_id}: {str(e)}")
        
        # Failure
        return PhaseOutput(
            video_id=video_id,
            phase="phase4_stitching",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        ).dict()
```

---

## **9. Phase 5: Music Generation**

### **9.1 Overview**

Analyze stitched video, generate appropriate background music, and merge.

### **9.2 Input/Output**

**Input:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "spec": { /* from Phase 1 */ },
    "stitched_url": "s3://..." /* from Phase 4 */
}
```

**Output:**
```python
{
    "video_id": "550e8400-e29b-41d4-a716-446655440000",
    "phase": "phase5_music",
    "status": "success",
    "cost_usd": 0.15,
    "duration_seconds": 62.5,
    "output_data": {
        "final_video_url": "s3://bucket/videos/{video_id}/final.mp4",
        "music_url": "s3://bucket/videos/{video_id}/music.mp3"
    }
}
```

### **9.3 Implementation**

**File:** `backend/app/phases/phase5_music/task.py`

```python
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.services.replicate import replicate_client
from app.services.ffmpeg import ffmpeg_service
from app.services.s3 import s3_client
from app.common.constants import COST_MUSICGEN
import tempfile
import time
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def generate_music(self, video_id: str, spec: dict, stitched_url: str) -> dict:
    """
    Phase 5: Generate music and merge with video.
    
    Args:
        video_id: Unique video identifier
        spec: Video specification from Phase 1
        stitched_url: Stitched video URL from Phase 4
        
    Returns:
        PhaseOutput dict with final video URL
    """
    start_time = time.time()
    
    logger.info(f"Phase 5 starting for video {video_id}")
    
    try:
        # Build music prompt from spec
        music_prompt = build_music_prompt(spec)
        duration = spec['duration']
        
        logger.info(f"Music prompt: {music_prompt}")
        logger.info(f"Duration: {duration}s")
        
        # Generate music with MusicGen
        music_output = replicate_client.run(
            "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
            input={
                "prompt": music_prompt,
                "duration": duration,
                "model_version": "stereo-melody-large"
            }
        )
        
        # Download music
        music_url = music_output if isinstance(music_output, str) else music_output[0]
        music_data = requests.get(music_url).content
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp:
            tmp.write(music_data)
            music_path = tmp.name
        
        # Upload music to S3
        music_s3_key = f"videos/{video_id}/music.mp3"
        music_s3_url = s3_client.upload_file(music_path, music_s3_key)
        
        logger.info(f"Music generated and uploaded: {music_s3_url}")
        
        # Download stitched video
        video_path = download_from_s3(stitched_url)
        
        # Merge video and music
        output_path = tempfile.mktemp(suffix='.mp4')
        
        ffmpeg_service.run_command([
            'ffmpeg',
            '-i', video_path,
            '-i', music_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-shortest',  # Cut to shortest input
            output_path
        ])
        
        logger.info(f"Video and music merged")
        
        # Upload final video
        final_s3_key = f"videos/{video_id}/final.mp4"
        final_url = s3_client.upload_file(output_path, final_s3_key)
        
        logger.info(f"Phase 5 complete for video {video_id}")
        logger.info(f"Final video: {final_url}")
        
        # Success
        return PhaseOutput(
            video_id=video_id,
            phase="phase5_music",
            status="success",
            output_data={
                "final_video_url": final_url,
                "music_url": music_s3_url
            },
            cost_usd=COST_MUSICGEN,
            duration_seconds=time.time() - start_time,
            error_message=None
        ).dict()
        
    except Exception as e:
        logger.error(f"Phase 5 failed for video {video_id}: {str(e)}")
        
        # Failure
        return PhaseOutput(
            video_id=video_id,
            phase="phase5_music",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=time.time() - start_time,
            error_message=str(e)
        ).dict()


def build_music_prompt(spec: dict) -> str:
    """Build music generation prompt from spec"""
    
    style = spec.get('style', {})
    mood = style.get('mood', 'upbeat')
    aesthetic = style.get('aesthetic', 'modern')
    
    # Map mood to music style
    mood_to_music = {
        "energetic": "upbeat electronic music, fast tempo, motivational",
        "elegant": "sophisticated orchestral music, elegant strings, refined",
        "minimalist": "minimal ambient music, clean tones, modern",
        "emotional": "emotional piano music, heartfelt, warm",
        "informative": "corporate background music, professional, steady"
    }
    
    music_desc = mood_to_music.get(mood, "modern background music")
    
    return f"{music_desc}, {aesthetic} style, instrumental only, no vocals"
```

---

## **10. Data Models**

### **10.1 Database Schema**

```python
# File: backend/app/common/models.py

from sqlalchemy import Column, String, Float, DateTime, JSON, Enum as SQLEnum, Integer
from sqlalchemy.sql import func
from app.database import Base
import enum

class VideoStatus(str, enum.Enum):
    """Video generation status"""
    QUEUED = "queued"
    PLANNING = "planning"
    STORYBOARDING = "storyboarding"
    GENERATING_CHUNKS = "generating_chunks"
    STITCHING = "stitching"
    ADDING_MUSIC = "adding_music"
    COMPLETE = "complete"
    FAILED = "failed"

class VideoGeneration(Base):
    """Video generation record"""
    __tablename__ = "video_generations"
    
    # Primary
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)
    
    # Input
    prompt = Column(String, nullable=False)
    creativity_level = Column(Float, default=0.5)
    
    # Spec (from Phase 1)
    spec = Column(JSON, nullable=True)
    selected_archetype = Column(String, nullable=True)
    
    # Status
    status = Column(SQLEnum(VideoStatus), default=VideoStatus.QUEUED)
    progress = Column(Float, default=0.0)
    current_phase = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Phase Outputs
    storyboard_images = Column(JSON, default=list)
    chunk_urls = Column(JSON, default=list)
    stitched_url = Column(String, nullable=True)
    music_url = Column(String, nullable=True)
    final_video_url = Column(String, nullable=True)
    
    # Metadata
    cost_usd = Column(Float, default=0.0)
    cost_breakdown = Column(JSON, default=dict)
    generation_time_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Stats
    num_beats = Column(Integer, nullable=True)
    num_chunks = Column(Integer, nullable=True)
```

---

## **11. Cost Analysis**

### **11.1 Cost Breakdown by Phase**

| Phase | Service | Cost per Call | Notes |
|-------|---------|--------------|-------|
| Phase 1 | GPT-4 Turbo | $0.02 | Planning |
| Phase 2 | SDXL | $0.0055 per image | N images = N beats |
| Phase 3 | Hailuo 2.3 Fast | $0.04 per chunk | N chunks = ceil(duration/5) |
| Phase 4 | FFmpeg | $0.00 | Local processing |
| Phase 5 | MusicGen | $0.15 | Music generation |

### **11.2 Example Cost Calculations**

**15s video (3 beats × 5s):**
```
Phase 1: $0.02
Phase 2: 3 images × $0.0055 = $0.0165
Phase 3: 3 chunks × $0.04 = $0.12
Phase 4: $0.00
Phase 5: $0.15
----------------------------
Total: $0.3065
```

**30s video (6 beats × 5s):**
```
Phase 1: $0.02
Phase 2: 6 images × $0.0055 = $0.033
Phase 3: 6 chunks × $0.04 = $0.24
Phase 4: $0.00
Phase 5: $0.15
----------------------------
Total: $0.443
```

**25s video (1×5s + 1×10s + 1×10s):**
```
Phase 1: $0.02
Phase 2: 3 images × $0.0055 = $0.0165
Phase 3: 5 chunks × $0.04 = $0.20
Phase 4: $0.00
Phase 5: $0.15
----------------------------
Total: $0.3865
```

---

## **12. Testing Strategy**

### **12.1 Unit Tests**

**Phase 1:**
- [ ] Test intent extraction with various prompts
- [ ] Test archetype selection logic (via LLM)
- [ ] Test beat sequence composition (via LLM)
- [ ] Test spec validation (duration sum, beat IDs, durations)
- [ ] Test creativity levels (0.0, 0.5, 1.0)

**Phase 2:**
- [ ] Test single beat image generation
- [ ] Test multiple beats image generation
- [ ] Test prompt template filling
- [ ] Test S3 upload

**Phase 3:**
- [ ] Test chunk generation from storyboard
- [ ] Test last frame extraction
- [ ] Test beat-to-chunk mapping (5s, 10s, 15s beats)
- [ ] Test model selection

**Phase 4:**
- [ ] Test FFmpeg stitching
- [ ] Test concat file generation
- [ ] Test S3 upload

**Phase 5:**
- [ ] Test music prompt generation
- [ ] Test music generation
- [ ] Test video+music merge

### **12.2 Integration Tests**

- [ ] End-to-end: 15s video with 3 beats
- [ ] End-to-end: 30s video with 6 beats
- [ ] End-to-end: Variable beat durations (5s, 10s, 15s mixed)
- [ ] End-to-end: All 5 archetypes
- [ ] End-to-end: Creativity levels (0.0, 0.5, 1.0)
- [ ] Failure handling: Phase 1 LLM failure
- [ ] Failure handling: Phase 3 video gen timeout
- [ ] Failure handling: Invalid beat sequence

### **12.3 Test Data**

```python
# File: backend/app/tests/fixtures/test_prompts.py

TEST_PROMPTS = [
    {
        "id": "TP1",
        "prompt": "15s Nike sneakers energetic urban",
        "expected_archetype": "energetic_lifestyle",
        "expected_duration": 15,
        "expected_beats": 3
    },
    {
        "id": "TP2",
        "prompt": "30s luxury watch elegant sophisticated",
        "expected_archetype": "luxury_showcase",
        "expected_duration": 30,
        "expected_beats": 4-6
    },
    {
        "id": "TP3",
        "prompt": "20s iPhone minimalist clean modern",
        "expected_archetype": "minimalist_reveal",
        "expected_duration": 20,
        "expected_beats": 4
    },
    {
        "id": "TP4",
        "prompt": "Create an ad for family car with emotional story",
        "expected_archetype": "emotional_storytelling",
        "expected_duration": 30,
        "expected_beats": 3-4
    },
    {
        "id": "TP5",
        "prompt": "Smart thermostat features demo 25 seconds",
        "expected_archetype": "feature_demo",
        "expected_duration": 25,
        "expected_beats": 4-5
    }
]
```

---

## **13. Implementation Roadmap**

### **13.1 Phase-by-Phase Implementation**

**Week 1: Foundation + Phase 1**
- [ ] Set up beat library (15 beats)
- [ ] Set up template archetypes (5 archetypes)
- [ ] Implement Phase 1 LLM agent
- [ ] Implement spec validation
- [ ] Write Phase 1 unit tests
- [ ] Test with 10+ prompts

**Week 2: Phase 2 + Phase 3**
- [ ] Implement Phase 2 storyboard generation
- [ ] Write Phase 2 unit tests
- [ ] Implement Phase 3 chunk generation
- [ ] Implement last frame extraction
- [ ] Write Phase 3 unit tests
- [ ] Test Phase 1-2-3 integration

**Week 3: Phase 4 + Phase 5**
- [ ] Implement Phase 4 stitching
- [ ] Write Phase 4 unit tests
- [ ] Implement Phase 5 music generation
- [ ] Write Phase 5 unit tests
- [ ] Test full pipeline end-to-end

**Week 4: Integration + Testing**
- [ ] Integration tests for all workflows
- [ ] Stress testing (concurrent jobs)
- [ ] Cost analysis and optimization
- [ ] Documentation
- [ ] Demo preparation

### **13.2 Success Metrics**

- [ ] 95%+ spec validation pass rate
- [ ] <5 min generation time for 30s video
- [ ] <$0.50 cost for 30s video
- [ ] 90%+ narrative coherence (human eval)
- [ ] 0% chunk generation failures
- [ ] 100% database consistency

---

## **14. Appendix**

### **14.1 Example Complete Workflow**

**User Input:**
```
"Create a 15-second ad for Nike sneakers, energetic and urban style"
```

**Phase 1 Output:**
```json
{
  "template": "energetic_lifestyle",
  "duration": 15,
  "beats": [
    {"beat_id": "action_montage", "start": 0, "duration": 5},
    {"beat_id": "product_in_motion", "start": 5, "duration": 5},
    {"beat_id": "call_to_action", "start": 10, "duration": 5}
  ]
}
```

**Phase 2 Output:**
```json
{
  "storyboard_images": [
    {"beat_id": "action_montage", "image_url": "s3://.../action_montage.png"},
    {"beat_id": "product_in_motion", "image_url": "s3://.../product_in_motion.png"},
    {"beat_id": "call_to_action", "image_url": "s3://.../call_to_action.png"}
  ]
}
```

**Phase 3 Output:**
```json
{
  "chunks": [
    {"chunk_idx": 0, "url": "s3://.../chunk_00.mp4", "input": "action_montage.png"},
    {"chunk_idx": 1, "url": "s3://.../chunk_01.mp4", "input": "product_in_motion.png"},
    {"chunk_idx": 2, "url": "s3://.../chunk_02.mp4", "input": "call_to_action.png"}
  ]
}
```

**Phase 4 Output:**
```json
{
  "stitched_url": "s3://.../stitched.mp4"
}
```

**Phase 5 Output:**
```json
{
  "final_video_url": "s3://.../final.mp4"
}
```

---

**END OF TDD**