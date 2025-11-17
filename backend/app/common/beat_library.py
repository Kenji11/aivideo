"""
Beat Library - Reusable shot types for video composition

This module defines 15 beats organized by typical position:
- 5 Opening Beats: Start the video with impact
- 5 Middle Product Beats: Showcase product features
- 3 Middle Dynamic Beats: Add energy and demonstrate benefits
- 2 Closing Beats: End with strong impression

All beat durations MUST be 5s, 10s, or 15s (no exceptions).
"""

# Opening Beats (5 total)
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

# Middle Beats - Product Focus (5 total)
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

# Middle Beats - Dynamic (3 total)
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

# Closing Beats (2 total)
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

# Complete Beat Library - 15 beats total
BEAT_LIBRARY = {
    **OPENING_BEATS,
    **MIDDLE_PRODUCT_BEATS,
    **MIDDLE_DYNAMIC_BEATS,
    **CLOSING_BEATS
}

# Verify we have exactly 15 beats
assert len(BEAT_LIBRARY) == 15, f"Beat library must have exactly 15 beats, found {len(BEAT_LIBRARY)}"

# Verify all durations are 5, 10, or 15 seconds
ALLOWED_DURATIONS = {5, 10, 15}
for beat_id, beat in BEAT_LIBRARY.items():
    assert beat["duration"] in ALLOWED_DURATIONS, \
        f"Beat '{beat_id}' has invalid duration {beat['duration']}s. Must be 5, 10, or 15s."

