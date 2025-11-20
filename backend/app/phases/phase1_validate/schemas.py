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
    """Individual beat in the sequence"""
    beat_id: str = Field(description="Beat identifier from BEAT_LIBRARY")
    duration: int = Field(description="Beat duration - MUST be 5, 10, or 15 seconds ONLY")


class StyleSpec(BaseModel):
    """Visual style specification"""
    aesthetic: str = Field(description="Overall visual style description matching archetype")
    color_palette: List[str] = Field(description="3-5 color names for the video")
    mood: str = Field(description="Mood matching user intent")
    lighting: str = Field(description="Lighting style description")


class VideoPlanning(BaseModel):
    """Complete video planning output with reasoning (for structured outputs)"""
    reasoning_process: Optional[str] = Field(
        default=None,
        description="Step-by-step thought process explaining decisions (2-4 sentences)"
    )
    intent_analysis: IntentAnalysis
    selected_archetype: str = Field(description="Selected archetype ID from TEMPLATE_ARCHETYPES")
    archetype_reasoning: str = Field(description="1-2 sentences explaining archetype choice")
    beat_sequence: List[BeatInfo] = Field(description="Ordered list of beats forming the video")
    beat_selection_reasoning: str = Field(description="1-2 sentences explaining beat choices")
    duration_verification: Optional[str] = Field(
        default=None,
        description="Explicit verification that beat durations sum to total duration"
    )
    style: StyleSpec


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
