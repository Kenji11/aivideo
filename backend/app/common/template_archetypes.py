"""
Template Archetypes - High-level video structures to guide LLM composition

This module defines 5 archetype templates that serve as creative guides
for the LLM when composing beat sequences. The LLM can adapt and deviate
from these suggestions based on user intent.

Archetypes:
1. luxury_showcase - Elegant, cinematic premium goods
2. energetic_lifestyle - High-energy, dynamic active products
3. minimalist_reveal - Clean, simple, focused presentation
4. emotional_storytelling - Narrative-driven emotional connection
5. feature_demo - Informative capability showcase
"""

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

# Verify we have exactly 5 archetypes
assert len(TEMPLATE_ARCHETYPES) == 5, f"Must have exactly 5 archetypes, found {len(TEMPLATE_ARCHETYPES)}"

# Verify all required fields are present
REQUIRED_FIELDS = {
    "archetype_id", "name", "description", "typical_duration_range",
    "suggested_beat_sequence", "typical_products", "style_hints",
    "energy_curve", "narrative_structure"
}

for archetype_id, archetype in TEMPLATE_ARCHETYPES.items():
    missing_fields = REQUIRED_FIELDS - set(archetype.keys())
    assert not missing_fields, \
        f"Archetype '{archetype_id}' missing fields: {missing_fields}"
    
    # Verify typical_duration_range is a tuple of two integers
    assert isinstance(archetype["typical_duration_range"], tuple), \
        f"Archetype '{archetype_id}' typical_duration_range must be a tuple"
    assert len(archetype["typical_duration_range"]) == 2, \
        f"Archetype '{archetype_id}' typical_duration_range must have 2 values"
    
    # Verify suggested_beat_sequence is a non-empty list
    assert isinstance(archetype["suggested_beat_sequence"], list), \
        f"Archetype '{archetype_id}' suggested_beat_sequence must be a list"
    assert len(archetype["suggested_beat_sequence"]) > 0, \
        f"Archetype '{archetype_id}' suggested_beat_sequence cannot be empty"

