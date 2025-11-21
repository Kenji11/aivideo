# Video specifications
DEFAULT_DURATION = 30  # seconds
DEFAULT_FPS = 30
DEFAULT_RESOLUTION = "1080p"

# Beat composition creativity control (0.0-1.0)
# Controls how strictly the LLM follows template archetypes
# 0.0 = strict template adherence, 1.0 = creative reinterpretation
import os
BEAT_COMPOSITION_CREATIVITY = float(os.getenv('BEAT_COMPOSITION_CREATIVITY', '0.5'))


def get_planning_temperature(creativity: float) -> float:
    """
    Map creativity level (0.0-1.0) to LLM temperature for Phase 1 planning.
    
    Temperature ranges:
    - 0.0 → 0.2 (strict template adherence - follows archetype closely)
    - 0.5 → 0.5 (balanced adaptation - default, good mix of structure + creativity)
    - 1.0 → 0.8 (creative reinterpretation - maximum creative freedom)
    
    Linear mapping: temperature = 0.2 + (creativity * 0.6)
    
    Args:
        creativity: Creativity level from 0.0 (strict) to 1.0 (creative)
        
    Returns:
        LLM temperature from 0.2 to 0.8
        
    Examples:
        >>> get_planning_temperature(0.0)
        0.2
        >>> get_planning_temperature(0.5)
        0.5
        >>> get_planning_temperature(1.0)
        0.8
    """
    return 0.2 + (creativity * 0.6)

# Cost per API call (USD)
COST_GPT4_TURBO = 0.01
COST_SDXL_IMAGE = 0.0055  # Legacy, not used anymore
COST_FLUX_SCHNELL_IMAGE = 0.003  # Phase 2: Animatic frames (cheapest)
COST_FLUX_DEV_IMAGE = 0.025  # Phase 2: Storyboard images (better quality)
COST_FLUX_DEV_CONTROLNET_IMAGE = 0.058  # Phase 2: Storyboard images with ControlNet (product consistency)
COST_FLUX_PRO_IMAGE = 0.04  # Phase 3: Reference assets (best quality, for final)
# Phase 4: Video generation model costs (per chunk generation, typically 5 seconds)
# NOTE: Costs are per chunk, not per second. Multiply by chunk count for total video cost.
# Verified pricing marked with [VERIFIED], others are estimates based on model tiers
# Sorted by price (cheapest to most expensive)
COST_AUDIO_CROP = 0.05  # FFmpeg audio crop (local, no cost)
COST_SEEDANCE = 0.06  # Seedance 1.0 Pro Fast - Estimated (claimed 60% cheaper than Pro)
COST_PIXVERSE = 0.07  # Pixverse v5 - Estimated (mid-tier pricing)
COST_WAN = 0.09  # Wan 2.1 (480p) - Estimated
COST_WAN_25_I2V = 0.09  # Wan 2.5 I2V Fast - Estimated (similar to Wan 2.1)
COST_ZEROSCOPE = 0.10  # Zeroscope v2 XL - Estimated
COST_WAN_25_T2V = 0.10  # Wan 2.5 T2V - Estimated (similar to Wan 2.1)
COST_STABLE_AUDIO = 0.10  # stackadoc/stable-audio-open-1.0 per 30s (avg $0.06-$0.15)
COST_BARK_MUSIC = 0.10  # Legacy: suno-ai/bark per 30s
COST_VEO_FAST = 0.12  # Google Veo 3.1 Fast - Estimated (premium model, fast tier)
COST_VEO = 0.15  # Google Veo 3.1 - Estimated (premium model, standard tier)
COST_MUSICGEN = 0.15  # meta/musicgen per 30s
COST_HAILUO_23_FAST = 0.19  # Hailuo 2.3 Fast [VERIFIED] - $0.19 per 6s chunk at 768p, ~$0.19 per 5s at 720p
COST_ANIMATEDIFF = 0.20  # AnimateDiff - Estimated
COST_SORA = 0.20  # OpenAI Sora 2 - Estimated (premium model)
COST_KLING_21 = 0.25  # Kling 2.1 [VERIFIED] - $0.25 per 5s chunk at 720p (1080p is $0.45)
COST_RUNWAY = 0.25  # Runway Gen-2 - Estimated
COST_HAILUO_23 = 0.28  # Minimax Hailuo 2.3 (standard, not fast) [VERIFIED] - $0.28 per 6s chunk
COST_KLING_25_PRO = 0.35  # Kling 2.5 Turbo Pro [VERIFIED] - $0.35 per 5s chunk
COST_KLING_21_1080P = 0.45  # Kling 2.1 [VERIFIED] - $0.45 per 5s chunk at 1080p
COST_KLING_16_PRO = 0.475  # Kling 1.6 Pro [VERIFIED] - $0.475 per 5s chunk
COST_MINIMAX_VIDEO_01 = 0.5  # Minimax Video-01 [VERIFIED] - $0.5 per chunk (accepts subject reference)
COST_RUNWAY_GEN4_TURBO = 0.60  # Runway Gen-4 Turbo - Estimated ($0.12/sec * 5s = $0.60 per chunk)

# Legacy constants (kept for backwards compatibility)
COST_ZEROSCOPE_VIDEO = COST_ZEROSCOPE
COST_WAN_480P_VIDEO = COST_WAN  # Phase 4: Video chunks per second (current)
COST_WAN_720P_VIDEO = 0.25  # Phase 4: Video chunks per second (higher quality)
COST_ANIMATEDIFF_VIDEO = COST_ANIMATEDIFF

# S3 paths
# Legacy prefixes (deprecated - kept for backward compatibility with existing test data)
S3_ANIMATIC_PREFIX = "animatic"
S3_REFERENCES_PREFIX = "references"  # DEPRECATED: Use get_video_s3_prefix() instead
S3_CHUNKS_PREFIX = "chunks"  # DEPRECATED: Use get_video_s3_prefix() instead
S3_FINAL_PREFIX = "final"  # DEPRECATED: Use get_video_s3_prefix() instead


def get_video_s3_prefix(user_id: str, video_id: str) -> str:
    """
    Generate the S3 prefix for all video-related outputs.
    
    New standard structure: {userId}/videos/{videoId}/
    All video outputs (references, chunks, stitched, music, final) are stored here.
    
    Why user-scoped paths?
    - User Isolation: All user data naturally partitioned at top level for better security
    - Consistency: Matches existing assets/{userId}/ pattern for uniform organization
    - Scalability: Easier to implement user-level permissions, storage analytics, and lifecycle policies
    - Organization: All files for a single video co-located in one directory for easy access
    
    Args:
        user_id: User ID from VideoGeneration.user_id
        video_id: Video generation ID
        
    Returns:
        S3 prefix path (e.g., "user123/videos/video456")
        
    Example:
        >>> get_video_s3_prefix("user-123", "video-456")
        "user-123/videos/video-456"
    """
    return f"{user_id}/videos/{video_id}"


def get_video_s3_key(user_id: str, video_id: str, filename: str) -> str:
    """
    Generate a full S3 key for a video output file.
    
    Args:
        user_id: User ID from VideoGeneration.user_id
        video_id: Video generation ID
        filename: Filename (e.g., "style_guide.png", "chunk_00.mp4")
        
    Returns:
        Full S3 key (e.g., "user123/videos/video456/style_guide.png")
        
    Example:
        >>> get_video_s3_key("user-123", "video-456", "style_guide.png")
        "user-123/videos/video-456/style_guide.png"
    """
    prefix = get_video_s3_prefix(user_id, video_id)
    return f"{prefix}/{filename}"


def get_asset_s3_key(user_id: str, filename: str) -> str:
    """
    Generate the S3 key for a reference asset file.
    
    New standard structure: {user_id}/assets/{filename}
    Original filename is preserved (sanitized for safety).
    
    Args:
        user_id: User ID
        filename: Original filename from user upload (e.g., "nike_sneaker.png")
        
    Returns:
        S3 key (e.g., "user123/assets/nike_sneaker.png")
        
    Example:
        >>> get_asset_s3_key("user-123", "nike_sneaker.png")
        "user-123/assets/nike_sneaker.png"
    """
    return f"{user_id}/assets/{filename}"


def get_asset_thumbnail_s3_key(user_id: str, filename: str) -> str:
    """
    Generate the S3 key for a reference asset thumbnail.
    
    Structure: {user_id}/assets/{base_name}_thumbnail.jpg
    Replaces file extension with _thumbnail.jpg
    
    Args:
        user_id: User ID
        filename: Original filename (e.g., "nike_sneaker.png")
        
    Returns:
        S3 key (e.g., "user123/assets/nike_sneaker_thumbnail.jpg")
        
    Example:
        >>> get_asset_thumbnail_s3_key("user-123", "nike_sneaker.png")
        "user-123/assets/nike_sneaker_thumbnail.jpg"
    """
    # Extract base name without extension
    from pathlib import Path
    base_name = Path(filename).stem
    return f"{user_id}/assets/{base_name}_thumbnail.jpg"

# Timeouts (seconds)
PHASE1_TIMEOUT = 60
PHASE2_TIMEOUT = 300
PHASE3_TIMEOUT = 300
PHASE4_TIMEOUT = 600
PHASE5_TIMEOUT = 300
PHASE6_TIMEOUT = 180

# Mock user ID for development/testing (DEPRECATED - do not use in production routes)
# This is kept for backward compatibility and testing purposes only.
# All production API routes now require Firebase authentication and use real user IDs.
MOCK_USER_ID = "mock-user-00000000-0000-0000-0000-000000000000"
