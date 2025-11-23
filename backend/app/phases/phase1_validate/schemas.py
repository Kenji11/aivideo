from pydantic import BaseModel, Field
from typing import Dict, List, Optional


# ===== Structured Output Schemas for LLM Planning =====

class ProductInfo(BaseModel):
    """Product information extracted from user prompt"""
    name: str = Field(description="Exact product name from user's prompt")
    category: str = Field(description="Product category (sportswear, luxury, tech, etc.)")


class IntentAnalysis(BaseModel):
    """Analysis of user's intent and requirements"""
    product: ProductInfo
    duration: int = Field(description="Video duration in seconds (default 30 if not specified)")
    style_keywords: List[str] = Field(description="List of style-related keywords from prompt")
    mood: str = Field(description="Overall mood (energetic|elegant|minimalist|emotional|informative)")
    key_message: str = Field(description="Brief description of what user wants to convey")


class BeatInfo(BaseModel):
    """Individual beat in the sequence with composed prompt"""
    beat_id: str = Field(description="Beat identifier from BEAT_LIBRARY")
    duration: int = Field(description="Beat duration - MUST be 5, 10, or 15 seconds ONLY")
    composed_prompt: str = Field(
        description="Full scene description composed by LLM (2-3 sentences). "
                    "Should incorporate product, style, colors, mood, and create narrative flow. "
                    "Example: 'Close-up shot of the luxury watch on a man's wrist as he adjusts the time. "
                    "Dramatic golden lighting highlights the polished metal finish and intricate dial details. "
                    "Slow dolly movement creates cinematic elegance.'"
    )


class StyleSpec(BaseModel):
    """Visual style specification"""
    aesthetic: str = Field(description="Overall visual style description matching archetype")
    color_palette: List[str] = Field(description="3-5 color names for the video")
    mood: str = Field(description="Mood matching user intent")
    lighting: str = Field(description="Lighting style description")


class ReferenceAssetMapping(BaseModel):
    """Reference asset mapping for a specific beat"""
    asset_ids: List[str] = Field(description="List of asset IDs to use for this beat")
    usage_type: str = Field(description="Asset usage type: 'product' | 'logo' | 'environment'")
    rationale: str = Field(description="1-2 sentences explaining why these assets were chosen for this beat")


class VideoPlanning(BaseModel):
    """Complete video planning output with reasoning (for structured outputs)
    
    Example output:
    {
        "reasoning_process": "User wants a luxury watch ad with elegant feel...",
        "intent_analysis": {...},
        "brand_name": "Rolex",
        "music_theme": "cinematic orchestral",
        "color_scheme": ["gold", "black", "deep blue"],
        "scene_requirements": {
            "hero_shot": "show watch on wrist",
            "call_to_action": "include brand logo prominently"
        },
        "selected_archetype": "luxury_showcase",
        "beat_sequence": [
            {
                "beat_id": "hero_shot",
                "duration": 5,
                "composed_prompt": "Close-up shot of the Rolex watch..."
            }
        ],
        "style": {...},
        "reference_mapping": {...}
    }
    """
    reasoning_process: Optional[str] = Field(
        default=None,
        description="Step-by-step thought process explaining decisions (2-4 sentences)"
    )
    intent_analysis: IntentAnalysis
    brand_name: Optional[str] = Field(
        default=None,
        description="Company/brand name extracted from prompt (e.g., 'Nike', 'Apple', 'Rolex'). "
                    "Extract if explicitly mentioned, otherwise None. "
                    "Used for closing beat brand overlay if no logo asset available."
    )
    music_theme: Optional[str] = Field(
        default=None,
        description="Music genre/mood for the video (e.g., 'upbeat electronic', 'cinematic orchestral', 'hip-hop beats'). "
                    "Extract if user mentions music preferences, otherwise infer based on archetype and mood."
    )
    color_scheme: Optional[List[str]] = Field(
        default=None,
        description="List of 3-5 primary colors for the video (e.g., ['gold', 'black', 'white'], ['red', 'orange', 'yellow']). "
                    "Extract if user specifies colors, otherwise infer based on product category and style. "
                    "Should be consistent across all beat prompts."
    )
    scene_requirements: Optional[Dict[str, str]] = Field(
        default=None,
        description="Dict mapping beat_ids to specific user scene requirements. "
                    "Only include if user explicitly describes specific scenes. "
                    "Example: {'hero_shot': 'show watch on wrist', 'usage_scenario': 'person running outdoors'}"
    )
    selected_archetype: str = Field(description="Selected archetype ID from TEMPLATE_ARCHETYPES")
    archetype_reasoning: str = Field(description="1-2 sentences explaining archetype choice")
    beat_sequence: List[BeatInfo] = Field(description="Ordered list of beats forming the video")
    beat_selection_reasoning: str = Field(description="1-2 sentences explaining beat choices")
    duration_verification: Optional[str] = Field(
        default=None,
        description="Explicit verification that beat durations sum to total duration"
    )
    style: StyleSpec
    reference_mapping: Optional[Dict[str, ReferenceAssetMapping]] = Field(
        default=None,
        description="Optional mapping of beat_id to reference assets (empty if user has no assets)"
    )


# ===== Legacy Schemas (kept for compatibility) =====

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
