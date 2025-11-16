# Video specifications
DEFAULT_DURATION = 30  # seconds
DEFAULT_FPS = 30
DEFAULT_RESOLUTION = "1080p"

# Cost per API call (USD)
COST_GPT4_TURBO = 0.01
COST_SDXL_IMAGE = 0.0055  # Legacy, not used anymore
COST_FLUX_SCHNELL_IMAGE = 0.003  # Phase 2: Animatic frames (cheapest)
COST_FLUX_DEV_IMAGE = 0.025  # Phase 3: Reference assets (better quality)
COST_FLUX_PRO_IMAGE = 0.04  # Phase 3: Reference assets (best quality, for final)
# Phase 4: Video generation model costs (per second of video)
COST_WAN = 0.09  # Wan 2.1 (480p) - Default model
COST_ZEROSCOPE = 0.10  # Zeroscope v2 XL
COST_ANIMATEDIFF = 0.20  # AnimateDiff
COST_RUNWAY = 0.25  # Runway Gen-2 (estimated)
COST_HAILUO = 0.04  # Hailuo 2.3 (fast)
COST_SEEDANCE = 0.06  # Seedance 1.0 Pro Fast (estimated, 2-12s clips, 60% cheaper than Pro)
# New models
COST_KLING = 0.08  # Kling v2.5 Turbo Pro (estimated)
COST_PIXVERSE = 0.07  # Pixverse v5 (estimated)
COST_WAN_25_T2V = 0.10  # Wan 2.5 T2V (estimated)
COST_WAN_25_I2V = 0.09  # Wan 2.5 I2V Fast (estimated)
COST_VEO_FAST = 0.12  # Google Veo 3.1 Fast (estimated)
COST_VEO = 0.15  # Google Veo 3.1 (estimated)
COST_HAILUO_23 = 0.05  # Minimax Hailuo 2.3 (standard, not fast)
COST_SORA = 0.20  # OpenAI Sora 2 (estimated)

# Legacy constants (kept for backwards compatibility)
COST_ZEROSCOPE_VIDEO = COST_ZEROSCOPE
COST_WAN_480P_VIDEO = COST_WAN  # Phase 4: Video chunks per second (current)
COST_WAN_720P_VIDEO = 0.25  # Phase 4: Video chunks per second (higher quality)
COST_ANIMATEDIFF_VIDEO = COST_ANIMATEDIFF
COST_MUSICGEN = 0.15  # meta/musicgen per 30s
COST_STABLE_AUDIO = 0.10  # stackadoc/stable-audio-open-1.0 per 30s (avg $0.06-$0.15)
COST_BARK_MUSIC = 0.10  # Legacy: suno-ai/bark per 30s
COST_AUDIO_CROP = 0.05  # FFmpeg audio crop (local, no cost)

# S3 paths
S3_ANIMATIC_PREFIX = "animatic"
S3_REFERENCES_PREFIX = "references"
S3_CHUNKS_PREFIX = "chunks"
S3_FINAL_PREFIX = "final"

# Timeouts (seconds)
PHASE1_TIMEOUT = 60
PHASE2_TIMEOUT = 300
PHASE3_TIMEOUT = 300
PHASE4_TIMEOUT = 600
PHASE5_TIMEOUT = 300
PHASE6_TIMEOUT = 180

# Mock user ID for development/testing (before auth is implemented)
MOCK_USER_ID = "mock-user-00000000-0000-0000-0000-000000000000"
