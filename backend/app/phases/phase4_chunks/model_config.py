# Phase 4: Model Configuration Management
"""
Model configuration system for video chunk generation.

This module provides a centralized way to manage video generation models,
their parameters, costs, and capabilities. To switch models, simply change
the DEFAULT_MODEL constant below.

Available Models:
- 'wan': Wan 2.1 (wavespeedai/wan-2.1-i2v-480p) - Default, verified working
- 'zeroscope': Zeroscope v2 XL - Alternative option
- 'animatediff': AnimateDiff - Alternative option
- 'runway': Runway Gen-2 - Alternative option

Usage:
    from app.phases.phase4_chunks.model_config import get_default_model, get_model_config
    
    # Get default model config
    model = get_default_model()
    
    # Get specific model config
    model = get_model_config('wan')
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

