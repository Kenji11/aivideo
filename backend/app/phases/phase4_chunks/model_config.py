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
- 'hailuo': Hailuo 2.3 Fast (minimax/hailuo-2.3-fast) - Default, outputs 5s chunks, 720p @ 30fps
- 'seedance': Seedance 1.0 Pro Fast (bytedance/seedance-1-pro-fast) - 2-12s clips, 3x faster, 60% cheaper
- 'wan': Wan 2.1 (wavespeedai/wan-2.1-i2v-480p) - Outputs 5s chunks
- 'zeroscope': Zeroscope v2 XL - Outputs 3s chunks
- 'animatediff': AnimateDiff - Outputs 2s chunks (controllable)
- 'runway': Runway Gen-2 - Outputs 5-10s chunks (controllable with Gen-3)
- 'kling': Kling v2.5 Turbo Pro (kwaivgi/kling-v2.5-turbo-pro) - High quality, fast generation
- 'pixverse': Pixverse v5 (pixverse/pixverse-v5) - Advanced video generation
- 'wan_25_t2v': Wan 2.5 T2V (wan-video/wan-2.5-t2v) - Text-to-video model
- 'wan_25_i2v': Wan 2.5 I2V Fast (wan-video/wan-2.5-i2v-fast) - Fast image-to-video
- 'veo_fast': Google Veo 3.1 Fast (google/veo-3.1-fast) - Fast Google Veo model
- 'veo': Google Veo 3.1 (google/veo-3.1) - Standard Google Veo model
- 'hailuo_23': Minimax Hailuo 2.3 (minimax/hailuo-2.3) - Standard Hailuo (not fast)
- 'sora': OpenAI Sora 2 (openai/sora-2) - OpenAI's latest video model

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
    COST_HAILUO,
    COST_SEEDANCE,
    COST_KLING,
    COST_PIXVERSE,
    COST_WAN_25_T2V,
    COST_WAN_25_I2V,
    COST_VEO_FAST,
    COST_VEO,
    COST_HAILUO_23,
    COST_SORA,
)

# Default model (currently used model)
DEFAULT_MODEL = 'hailuo'

# Model configurations dictionary
MODEL_CONFIGS: Dict[str, Dict] = {
    'wan': {
        'name': 'wan',
        'replicate_model': 'wavespeedai/wan-2.1-i2v-480p',
        'cost_per_generation': COST_WAN,
        'params': {
            'num_frames': 80,
            'fps': 24,
            'width': 480,
            'height': 480,
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': False,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'zeroscope': {
        'name': 'zeroscope',
        'replicate_model': 'anotherjesse/zeroscope-v2-xl',
        'cost_per_generation': COST_ZEROSCOPE,
        'params': {
            'num_frames': 24,
            'fps': 8,
            'width': 1024,
            'height': 576,
        },
        'actual_chunk_duration': 3.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'animatediff': {
        'name': 'animatediff',
        'replicate_model': 'lucataco/animatediff',
        'cost_per_generation': COST_ANIMATEDIFF,
        'params': {
            'num_frames': 16,
            'fps': 8,
            'width': 512,
            'height': 512,
        },
        'actual_chunk_duration': 2.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'runway': {
        'name': 'runway',
        'replicate_model': 'runway-gen2',
        'cost_per_generation': COST_RUNWAY,
        'params': {
            'num_frames': 4,
            'fps': 24,
            'width': 1280,
            'height': 768,
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'hailuo': {
        'name': 'hailuo',
        'replicate_model': 'minimax/hailuo-2.3-fast',  # Official, fastest, cheapest high-quality version
        'cost_per_generation': COST_HAILUO,  # $0.04 per 5s chunk ($0.008/second)
        'params': {
            'num_frames': 151,      # 151 frames @ 30fps = ~5.03s (max reliable)
            'fps': 30,              # Native 30fps, smoother motion
            'width': 1280,          # Supports up to 1080p, 720p default on fast tier
            'height': 720,
        },
        'param_names': {
            'image': 'first_frame_image',  # Hailuo uses 'first_frame_image' instead of 'image'
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
        },
        'actual_chunk_duration': 5.0,  # Trained on 5s clips, outputs ~5s consistently
        'duration_controllable': True,  # Can control via num_frames (30–151 frames)
        'supports_multi_image': False,  # Single image input only
        'max_reference_assets': 0,      # No extra assets
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'seedance': {
        'name': 'seedance',
        'replicate_model': 'bytedance/seedance-1-pro-fast',  # ByteDance Seedance 1.0 Pro Fast
        'cost_per_generation': COST_SEEDANCE,  # $0.06 per generation (estimated, 60% cheaper than Pro)
        'params': {
            'duration': 5,          # 2-12 seconds controllable, default 5s
            'width': 1280,          # Supports 480p, 720p, 1080p
            'height': 720,          # 720p default (can go up to 1080p)
            'fps': 24,              # Standard 24fps
        },
        'param_names': {
            'image': 'image',       # Standard 'image' parameter
            'prompt': 'prompt',
            'duration': 'duration',  # Duration in seconds (2-12)
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,  # Default 5s, controllable 2-12s
        'duration_controllable': True,  # Can control duration (2-12 seconds)
        'supports_multi_image': False,  # Single image input
        'max_reference_assets': 0,      # No extra assets
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'kling': {
        'name': 'kling',
        'replicate_model': 'kwaivgi/kling-v2.5-turbo-pro',
        'cost_per_generation': COST_KLING,
        'params': {
            'num_frames': 120,
            'fps': 24,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'pixverse': {
        'name': 'pixverse',
        'replicate_model': 'pixverse/pixverse-v5',
        'cost_per_generation': COST_PIXVERSE,
        'params': {
            'num_frames': 100,
            'fps': 24,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 4.2,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'wan_25_t2v': {
        'name': 'wan_25_t2v',
        'replicate_model': 'wan-video/wan-2.5-t2v',
        'cost_per_generation': COST_WAN_25_T2V,
        'params': {
            'num_frames': 80,
            'fps': 24,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'wan_25_i2v': {
        'name': 'wan_25_i2v',
        'replicate_model': 'wan-video/wan-2.5-i2v-fast',
        'cost_per_generation': COST_WAN_25_I2V,
        'params': {
            'num_frames': 80,
            'fps': 24,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': False,
        'supports_image_to_video': True,
    },
    'veo_fast': {
        'name': 'veo_fast',
        'replicate_model': 'google/veo-3.1-fast',
        'cost_per_generation': COST_VEO_FAST,
        'params': {
            'num_frames': 120,
            'fps': 24,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'veo': {
        'name': 'veo',
        'replicate_model': 'google/veo-3.1',
        'cost_per_generation': COST_VEO,
        'params': {
            'num_frames': 120,
            'fps': 24,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'hailuo_23': {
        'name': 'hailuo_23',
        'replicate_model': 'minimax/hailuo-2.3',
        'cost_per_generation': COST_HAILUO_23,
        'params': {
            'num_frames': 151,
            'fps': 30,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'first_frame_image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
        'supports_multi_image': False,
        'max_reference_assets': 0,
        'supports_text_to_video': True,
        'supports_image_to_video': True,
    },
    'sora': {
        'name': 'sora',
        'replicate_model': 'openai/sora-2',
        'cost_per_generation': COST_SORA,
        'params': {
            'num_frames': 120,
            'fps': 24,
            'width': 1280,
            'height': 720,
        },
        'param_names': {
            'image': 'image',
            'prompt': 'prompt',
            'num_frames': 'num_frames',
            'fps': 'fps',
            'width': 'width',
            'height': 'height',
        },
        'actual_chunk_duration': 5.0,
        'duration_controllable': True,
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

