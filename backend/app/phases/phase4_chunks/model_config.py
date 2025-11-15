# Phase 4: Model Configuration Management
"""
Model configuration system for video chunk generation.

This module provides a centralized way to manage video generation models,
their parameters, costs, and capabilities. To switch models, simply change
the DEFAULT_MODEL constant below.

CRITICAL: Models output different chunk durations regardless of parameters!
- Use 'actual_chunk_duration' to know what the model really outputs
- Use 'duration_controllable' to know if you can change it

Available Models:
- 'wan': Wan 2.1 (wavespeedai/wan-2.1-i2v-480p) - Default, outputs 5s chunks
- 'zeroscope': Zeroscope v2 XL - Outputs 3s chunks
- 'animatediff': AnimateDiff - Outputs 2s chunks (controllable)
- 'runway': Runway Gen-2 - Outputs 5-10s chunks (controllable with Gen-3)

Model Config Fields:
- name: Model identifier
- replicate_model: Replicate API model name
- cost_per_generation: Cost per chunk generation
- params: num_frames, fps, width, height (what we REQUEST)
- actual_chunk_duration: Reality of what model OUTPUTS in seconds
- duration_controllable: Can we reliably control chunk duration?
- supports_text_to_video: Can generate from prompt only
- supports_image_to_video: Can generate from image + prompt

Usage:
    from app.phases.phase4_chunks.model_config import get_default_model, get_model_config
    
    # Get default model config
    model = get_default_model()
    actual_duration = model['actual_chunk_duration']  # 5.0 for wan
    
    # Calculate chunk count for 30s video
    chunk_count = math.ceil(30 / actual_duration)  # 6 chunks for wan
"""

from typing import Dict, Optional
from app.common.exceptions import PhaseException
from app.common.constants import (
    COST_WAN,
    COST_ZEROSCOPE,
    COST_ANIMATEDIFF,
    COST_RUNWAY,
)

# Default model (currently used model)
DEFAULT_MODEL = 'wan'

# Model configurations dictionary
MODEL_CONFIGS: Dict[str, Dict] = {
    'wan': {
        'name': 'wan',
        'replicate_model': 'wavespeedai/wan-2.1-i2v-480p',
        'cost_per_generation': COST_WAN,  # Cost per second of video
        'params': {
            'num_frames': 80,  # Maximum frames supported
            'fps': 24,  # Default FPS
            'width': 480,  # Output width
            'height': 480,  # Output height
        },
        'actual_chunk_duration': 5.0,  # Reality: model outputs ~5s chunks regardless of params (trained on 5s clips)
        'duration_controllable': False,  # Cannot reliably control chunk duration
        'supports_multi_image': False,  # Does not support multiple image inputs
        'max_reference_assets': 0,  # No reference assets support
        'supports_text_to_video': True,  # Can generate from text prompt only
        'supports_image_to_video': True,  # Can generate from image input
    },
    'zeroscope': {
        'name': 'zeroscope',
        'replicate_model': 'anotherjesse/zeroscope-v2-xl',
        'cost_per_generation': COST_ZEROSCOPE,  # Cost per second of video
        'params': {
            'num_frames': 24,  # Maximum frames supported
            'fps': 8,  # Default FPS
            'width': 1024,  # Output width
            'height': 576,  # Output height
        },
        'actual_chunk_duration': 3.0,  # Reality: 24 frames @ 8fps = 3 seconds
        'duration_controllable': True,  # Some control via num_frames parameter
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'animatediff': {
        'name': 'animatediff',
        'replicate_model': 'lucataco/animatediff',
        'cost_per_generation': COST_ANIMATEDIFF,  # Cost per second of video
        'params': {
            'num_frames': 16,  # Maximum frames supported
            'fps': 8,  # Default FPS
            'width': 512,  # Output width
            'height': 512,  # Output height
        },
        'actual_chunk_duration': 2.0,  # Reality: 16 frames @ 8fps = 2 seconds (actually works!)
        'duration_controllable': True,  # Good control via num_frames parameter
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'runway': {
        'name': 'runway',
        'replicate_model': 'runway-gen2',  # Note: May need actual Replicate model name
        'cost_per_generation': COST_RUNWAY,  # Cost per second of video
        'params': {
            'num_frames': 4,  # Maximum frames supported
            'fps': 24,  # Default FPS
            'width': 1280,  # Output width
            'height': 768,  # Output height
        },
        'actual_chunk_duration': 5.0,  # Reality: ~5-10s depending on tier (conservative estimate)
        'duration_controllable': True,  # Gen-3 API allows 5s or 10s selection
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
}


def get_model_config(model_name: str) -> Dict:
    """
    Get configuration for a specific model.
    
    Args:
        model_name: Name of the model ('wan', 'zeroscope', 'animatediff', 'runway')
        
    Returns:
        Dictionary containing model configuration
        
    Raises:
        PhaseException: If model_name is not found in MODEL_CONFIGS
    """
    if model_name not in MODEL_CONFIGS:
        available_models = ', '.join(MODEL_CONFIGS.keys())
        raise PhaseException(
            f"Unknown model '{model_name}'. Available models: {available_models}"
        )
    
    return MODEL_CONFIGS[model_name].copy()


def get_default_model() -> Dict:
    """
    Get configuration for the default model.
    
    Returns:
        Dictionary containing default model configuration
        
    Note:
        To change the default model, update the DEFAULT_MODEL constant at the top of this file.
    """
    return get_model_config(DEFAULT_MODEL)

