"""
Spec validation and builder for Phase 1 intelligent planning.

This module validates LLM output and builds the complete video specification
with full beat details from the beat library.
"""

import logging
from app.common.beat_library import BEAT_LIBRARY, OPENING_BEATS, CLOSING_BEATS

logger = logging.getLogger(__name__)

# Allowed beat durations
ALLOWED_BEAT_DURATIONS = {5, 10, 15}


def validate_spec(spec: dict) -> None:
    """
    Validate video specification meets all constraints.
    
    Checks:
    - Beat durations sum to total duration
    - All beat durations are 5, 10, or 15 seconds
    - All beat_ids exist in BEAT_LIBRARY
    - At least one beat exists
    - Warnings for first/last beat positions
    
    Args:
        spec: Complete video specification dictionary
        
    Raises:
        ValueError: If validation fails
    """
    
    beats = spec.get('beats', [])
    duration = spec.get('duration')
    
    # Check 1: At least one beat
    if not beats:
        raise ValueError("Spec must contain at least one beat")
    
    # Check 2: Duration sums correctly
    total = sum(b['duration'] for b in beats)
    if total != duration:
        raise ValueError(
            f"Beat durations sum to {total}s, expected {duration}s. "
            f"Difference: {abs(total - duration)}s"
        )
    
    # Check 3: All beat durations valid (5, 10, or 15 seconds)
    for beat in beats:
        if beat['duration'] not in [5, 10, 15]:
            raise ValueError(
                f"Beat '{beat['beat_id']}' has invalid duration {beat['duration']}s "
                f"(must be 5, 10, or 15)"
            )
    
    # Check 4: All beat_ids exist in BEAT_LIBRARY
    for beat in beats:
        beat_id = beat.get('beat_id')
        if beat_id not in BEAT_LIBRARY:
            raise ValueError(
                f"Unknown beat_id: '{beat_id}'. "
                f"Must be one of: {', '.join(BEAT_LIBRARY.keys())}"
            )
    
    # Warning: First beat should be from opening beats
    if beats:
        first_beat_id = beats[0].get('beat_id')
        if first_beat_id not in OPENING_BEATS:
            logger.warning(
                f"First beat '{first_beat_id}' is not from opening beats. "
                f"Consider using: {', '.join(OPENING_BEATS.keys())}"
            )
    
    # Warning: Last beat should be from closing beats
    if beats:
        last_beat_id = beats[-1].get('beat_id')
        if last_beat_id not in CLOSING_BEATS:
            logger.warning(
                f"Last beat '{last_beat_id}' is not from closing beats. "
                f"Consider using: {', '.join(CLOSING_BEATS.keys())}"
            )
    
    logger.info(f"✅ Spec validation passed: {len(beats)} beats, {duration}s total")


def validate_llm_beat_durations(llm_output: dict) -> dict:
    """
    Validate and fix beat durations from LLM output BEFORE building full spec.
    
    This ensures LLM-returned beat durations are valid (5s, 10s, or 15s only).
    If invalid durations found, they are fixed to nearest valid duration.
    
    Args:
        llm_output: Raw LLM output with beat_sequence
        
    Returns:
        Fixed llm_output with valid beat durations
        
    Raises:
        ValueError: If beat_sequence is missing or empty
    """
    if 'beat_sequence' not in llm_output or not llm_output['beat_sequence']:
        raise ValueError("LLM output missing 'beat_sequence' field")
    
    beat_sequence = llm_output['beat_sequence']
    fixed_count = 0
    
    for beat_info in beat_sequence:
        original_duration = beat_info.get('duration')
        
        if original_duration not in ALLOWED_BEAT_DURATIONS:
            # Fix to nearest valid duration
            if original_duration <= 7:
                fixed_duration = 5
            elif original_duration <= 12:
                fixed_duration = 10
            else:
                fixed_duration = 15
            
            logger.warning(
                f"⚠️  LLM returned invalid beat duration: {original_duration}s "
                f"(beat_id={beat_info.get('beat_id')}). Fixed to {fixed_duration}s"
            )
            beat_info['duration'] = fixed_duration
            fixed_count += 1
    
    if fixed_count > 0:
        logger.warning(
            f"⚠️  Fixed {fixed_count} invalid beat durations from LLM output. "
            f"All beat durations must be 5s, 10s, or 15s."
        )
    
    return llm_output


def build_full_spec(llm_output: dict, video_id: str) -> dict:
    """
    Convert LLM output into full video specification.
    
    Takes the LLM's beat sequence and fills in complete details from the
    beat library, including prompt templates with product/style substitutions.
    
    Args:
        llm_output: Raw output from GPT-4 containing intent_analysis,
                   selected_archetype, beat_sequence, and style
        video_id: Unique video identifier
        
    Returns:
        Complete video specification dictionary with full beat details
        
    Raises:
        KeyError: If required fields missing from llm_output
        ValueError: If beat_id not found in BEAT_LIBRARY
    """
    
    # Extract required sections
    intent = llm_output['intent_analysis']
    beat_sequence = llm_output['beat_sequence']
    style = llm_output['style']
    
    # Build beats with full details from library
    current_time = 0
    full_beats = []
    
    for beat_info in beat_sequence:
        beat_id = beat_info['beat_id']
        duration = beat_info['duration']
        
        # Get beat template from library
        if beat_id not in BEAT_LIBRARY:
            raise ValueError(
                f"Invalid beat_id: '{beat_id}'. "
                f"Available beats: {', '.join(BEAT_LIBRARY.keys())}"
            )
        
        beat_template = BEAT_LIBRARY[beat_id]
        
        # Build full beat by copying all fields from library
        beat = {
            **beat_template,  # Copy all fields from library
            "start": current_time,
            "duration": duration  # Override with requested duration
        }
        
        # Fill in prompt template with actual product/style
        # Handle {product_name}, {style_aesthetic}, {setting} placeholders
        beat['prompt_template'] = beat['prompt_template'].format(
            product_name=intent['product']['name'],
            style_aesthetic=style['aesthetic'],
            setting=f"{style['mood']} setting"
        )
        
        full_beats.append(beat)
        current_time += duration
    
    # Assemble final spec
    spec = {
        "template": llm_output['selected_archetype'],
        "duration": current_time,
        "fps": 30,
        "resolution": "1280x720",
        "product": intent['product'],
        "style": style,
        "beats": full_beats,
        "llm_reasoning": {
            "selected_archetype": llm_output['selected_archetype'],
            "archetype_reasoning": llm_output.get('archetype_reasoning', ''),
            "beat_selection_reasoning": llm_output.get('beat_selection_reasoning', '')
        }
    }
    
    logger.info(
        f"✅ Built full spec: {len(full_beats)} beats, "
        f"{current_time}s duration, archetype={spec['template']}"
    )
    
    return spec

