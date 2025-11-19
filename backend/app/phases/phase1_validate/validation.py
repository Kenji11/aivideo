"""
Spec validation and builder for Phase 1 intelligent planning.

This module validates LLM output and builds the complete video specification
with full beat details from the beat library.
"""

import logging
import math
import os
from pathlib import Path
from datetime import datetime
from app.common.beat_library import BEAT_LIBRARY, OPENING_BEATS, CLOSING_BEATS

logger = logging.getLogger(__name__)

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
TRUNCATION_LOG = LOGS_DIR / "beat_truncation.log"


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


def validate_and_fix_beat_count(spec: dict, video_id: str) -> dict:
    """
    Validate beat count against duration and truncate if necessary.
    
    This is a guardrail to prevent Phase 1 LLM from returning too many beats.
    If beats exceed maximum for the duration, truncate and log warning.
    
    Args:
        spec: Video specification with beats
        video_id: Video ID for logging
        
    Returns:
        Fixed spec (may have truncated beats)
    """
    duration = spec.get('duration', 30)
    beats = spec.get('beats', [])
    
    # Calculate maximum beats (assuming 5s minimum beat length)
    max_beats = math.ceil(duration / 5)
    
    if len(beats) <= max_beats:
        # Beat count is valid
        return spec
    
    # Too many beats - truncate
    original_count = len(beats)
    truncated_beats = beats[:max_beats]
    
    # Recalculate start times to ensure they're sequential
    current_time = 0
    for beat in truncated_beats:
        beat['start'] = current_time
        current_time += beat['duration']
    
    # Update spec with truncated beats
    spec['beats'] = truncated_beats
    spec['duration'] = current_time  # Update duration to match truncated beats
    
    # Log warning
    warning_msg = (
        f"⚠️  Beat count truncation: video_id={video_id}, "
        f"original_beats={original_count}, truncated_to={max_beats}, "
        f"original_duration={duration}s, new_duration={current_time}s"
    )
    logger.warning(warning_msg)
    
    # Save to truncation log file
    try:
        timestamp = datetime.now().isoformat()
        log_entry = (
            f"{timestamp} | video_id={video_id} | "
            f"original_beats={original_count} | truncated_to={max_beats} | "
            f"original_duration={duration}s | new_duration={current_time}s\n"
        )
        with open(TRUNCATION_LOG, 'a') as f:
            f.write(log_entry)
        logger.info(f"Truncation event logged to: {TRUNCATION_LOG}")
    except Exception as e:
        logger.error(f"Failed to write truncation log: {e}")
    
    return spec


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
    
    # Validate and fix beat count (truncate if too many beats)
    spec = validate_and_fix_beat_count(spec, video_id)
    
    return spec

