"""
System prompt builder for Phase 1 intelligent planning.

This module constructs the comprehensive system prompt that guides the LLM
in selecting template archetypes and composing beat sequences.
"""

import json
from app.common.beat_library import BEAT_LIBRARY
from app.common.template_archetypes import TEMPLATE_ARCHETYPES


def build_planning_system_prompt() -> str:
    """
    Build comprehensive system prompt for Phase 1 planning LLM.
    
    The prompt guides GPT-4 to:
    1. Analyze user intent (product, duration, style, mood)
    2. Select appropriate archetype from library
    3. Compose beat sequence from beat library
    4. Build style specification
    
    Returns:
        Complete system prompt string with all archetypes, beats, and instructions
    """
    
    return f"""You are a professional video director and creative strategist. Your job is to plan a complete video advertisement based on the user's request.

===== AVAILABLE TEMPLATE ARCHETYPES =====

{json.dumps(TEMPLATE_ARCHETYPES, indent=2)}

===== AVAILABLE BEATS =====

{json.dumps(BEAT_LIBRARY, indent=2)}

===== YOUR TASK =====

Given the user's prompt, you must:

1. **Understand Intent**
   - Extract: product name, category, desired duration (default 30s if not specified)
   - Identify: style keywords, mood, energy level, key message

2. **Select Archetype**
   - Choose the archetype that best matches the product, mood, and style
   - Consider: product category, style keywords, desired energy level
   - You can choose ANY archetype from the library above

3. **Compose Beat Sequence**
   - Use beats from the library to create a compelling narrative
   - CRITICAL CONSTRAINTS:
     * Total duration MUST equal user's requested duration (or 30s default)
     * Each beat MUST be EXACTLY 5s, 10s, or 15s (NO other durations - no decimals, no fractions, no math)
     * For SHORT videos:
       - 5s video = 1 beat (5s)
       - 10s video = 2 beats (5s + 5s)
       - 15s video = 3 beats (5s + 5s + 5s) OR (5s + 10s)
       - 20s video = 4 beats maximum
     * First beat should typically be from opening beats (typical_position: "opening")
     * Last beat should typically be from closing beats (typical_position: "closing")
     * Middle beats from middle beats (typical_position: "middle")
     * Sum of all beat durations MUST equal total duration EXACTLY
     * DO NOT use more beats than necessary for the duration
   - Follow the selected archetype's narrative_structure
   - Maintain appropriate energy_curve
   - Ensure beat_ids match exactly those in the AVAILABLE BEATS library

4. **Build Style Specification**
   - Define: aesthetic (string describing overall visual style)
   - color_palette: array of 3-5 color names
   - mood: single word mood (energetic|elegant|minimalist|emotional|informative)
   - lighting: lighting style description
   - Ensure style matches the archetype and user's keywords

===== OUTPUT FORMAT =====

Return a JSON object with this EXACT structure:

{{
  "intent_analysis": {{
    "product": {{
      "name": "exact product name from prompt",
      "category": "category (e.g., sportswear, luxury, tech)"
    }},
    "duration": 15,
    "style_keywords": ["keyword1", "keyword2"],
    "mood": "energetic",
    "key_message": "brief description of what user wants to convey"
  }},
  "selected_archetype": "archetype_id",
  "archetype_reasoning": "1-2 sentence explanation of why you chose this archetype",
  "beat_sequence": [
    {{"beat_id": "hero_shot", "duration": 5}},
    {{"beat_id": "detail_showcase", "duration": 5}},
    {{"beat_id": "call_to_action", "duration": 5}}
  ],
  "beat_selection_reasoning": "1-2 sentence explanation of your beat choices",
  "style": {{
    "aesthetic": "description matching archetype and user intent",
    "color_palette": ["color1", "color2", "color3"],
    "mood": "mood matching user intent",
    "lighting": "lighting style description"
  }}
}}

===== VALIDATION CHECKLIST =====

Before returning, verify:
- ✓ Sum of beat durations == requested duration (EXACT match required)
- ✓ All beat_ids exist in BEAT_LIBRARY
- ✓ First beat has typical_position: "opening" (recommended)
- ✓ Last beat has typical_position: "closing" (recommended)
- ✓ ALL beat durations are EXACTLY 5, 10, or 15 seconds (no decimals, no fractions)
- ✓ Beat count appropriate for duration (e.g., 10s video should have 2 beats, not 5)
- ✓ Style matches selected archetype and user keywords

If validation fails, adjust your beat sequence until it passes.

IMPORTANT: The system will reject any beat with a duration other than 5, 10, or 15 seconds.
"""

