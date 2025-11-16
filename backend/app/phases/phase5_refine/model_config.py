# Phase 5: Music Model Configuration Management
"""
Music model configuration system for music generation.

This module provides a centralized way to manage music generation models,
their parameters, costs, and capabilities. To switch models, simply change
the DEFAULT_MUSIC_MODEL constant below.

Available Models:
- 'musicgen': Meta MusicGen (melody-large) - Default, reliable, clean instrumentals
- 'stable_audio': Stable Audio Open 1.0 (stackadoc version) - Best for electronic, rock, pop, guitar/synth-heavy

Model Config Fields:
- name: Model identifier
- replicate_model: Replicate API model identifier (can be model:version format, replicate.run() handles it automatically)
- cost_per_generation: Cost per 30s generation
- max_duration: Maximum duration the model can generate in one call
- input_params: Required input parameters for the model

Usage:
    from app.phases.phase5_refine.model_config import get_default_music_model, get_music_model_config
    
    # Get default model config
    model = get_default_music_model()
    max_duration = model['max_duration']  # 30 for musicgen
    
    # Use model in generation
    replicate_model = model['replicate_model']
    input_params = model['input_params'].copy()
    input_params['prompt'] = "your prompt here"
"""

from typing import Dict, Optional
from app.common.exceptions import PhaseException
from app.common.constants import (
    COST_MUSICGEN,
    COST_STABLE_AUDIO,
)

# Default model (currently used model)
DEFAULT_MUSIC_MODEL = 'musicgen'

# Model configurations dictionary
MUSIC_MODEL_CONFIGS: Dict[str, Dict] = {
    'musicgen': {
        'name': 'musicgen',
        'replicate_model': 'facebookresearch/musicgen:7a76a8258b23fae65c5a22debb8841d1d7e816b75c2f24218cd2bd8573787906',  # Version hash for stable access
        'cost_per_generation': COST_MUSICGEN,  # $0.15 per 30s
        'max_duration': 30,  # MusicGen supports up to 30s per generation
        'use_version_hash': True,  # Must use version hash (model name doesn't work)
        'input_params': {
            'model_version': 'large',  # Best quality version (options: "melody", "large", "encode-decode")
            'output_format': 'mp3',
            'normalization_strategy': 'peak',  # 'peak' or 'loudness'
        },
        'description': 'Meta MusicGen - reliable, clean instrumentals, best for most ad music',
    },
    'stable_audio': {
        'name': 'stable_audio',
        'replicate_model': 'stackadoc/stable-audio-open-1.0:2cd7d762d12df80757b18439c8fcd0ac3311251eb94ac6bdc026bb4ce4540868',  # replicate.run() handles model:version format
        'cost_per_generation': COST_STABLE_AUDIO,  # $0.10 per 30s
        'max_duration': 47,  # Stable Audio Open supports up to 47s
        'input_params': {
            'sample_rate': 44100,
            'output_format': 'mp3',
        },
        'description': 'Stable Audio Open - best for electronic, rock, pop, guitar/synth-heavy music',
    },
}


def get_music_model_config(model_name: str) -> Dict:
    """
    Get configuration for a specific music model.
    
    Args:
        model_name: Name of the model ('musicgen', 'stable_audio')
        
    Returns:
        Dictionary containing model configuration
        
    Raises:
        PhaseException: If model_name is not found in MUSIC_MODEL_CONFIGS
    """
    if model_name not in MUSIC_MODEL_CONFIGS:
        available_models = ', '.join(MUSIC_MODEL_CONFIGS.keys())
        raise PhaseException(
            f"Unknown music model '{model_name}'. Available models: {available_models}"
        )
    
    return MUSIC_MODEL_CONFIGS[model_name].copy()


def get_default_music_model() -> Dict:
    """
    Get configuration for the default music model.
    
    Returns:
        Dictionary containing default music model configuration
        
    Note:
        To change the default model, update the DEFAULT_MUSIC_MODEL constant at the top of this file.
    """
    return get_music_model_config(DEFAULT_MUSIC_MODEL)

