#!/usr/bin/env python3
"""
Test Phase 1 with gpt-4o-mini and Structured Outputs

This script tests Phase 1 with structured outputs:
- Tests gpt-4o-mini (fast and cheap)
- Tests gpt-4o (more powerful fallback)
- Uses Pydantic schemas for type-safe outputs
- Bypasses Celery for direct testing

Usage:
    python scripts/test_o4_mini.py
    python scripts/test_o4_mini.py --model gpt-4o-mini
    python scripts/test_o4_mini.py --model gpt-4o
"""

import sys
import os
import json
import uuid
import time
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

# Load .env if exists
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
try:
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded .env from {env_path}")
    else:
        print(f"⚠️  No .env file found at {env_path}")
except Exception as e:
    print(f"⚠️  Could not load .env: {e}")

# Override database URL for local testing (not needed for this test, but prevents errors)
os.environ.setdefault('DATABASE_URL', 'postgresql://dev:devpass@localhost:5434/videogen')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')
os.environ.setdefault('S3_BUCKET', 'test-bucket')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'test')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test')
os.environ.setdefault('REPLICATE_API_TOKEN', 'test')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.phases.phase1_validate.validation import validate_spec, build_full_spec, validate_llm_beat_durations
from app.phases.phase1_validate.schemas import VideoPlanning
from app.common.constants import BEAT_COMPOSITION_CREATIVITY, get_planning_temperature
from app.common.beat_library import BEAT_LIBRARY
from app.common.template_archetypes import TEMPLATE_ARCHETYPES
from app.services.openai import openai_client


# ===== Prompt Builders =====

def build_gpt4_system_prompt() -> str:
    """Build system prompt for GPT-4 Turbo"""
    
    return f"""You are a professional video director and creative strategist. Your job is to plan a complete video advertisement.

===== AVAILABLE TEMPLATE ARCHETYPES =====

{json.dumps(TEMPLATE_ARCHETYPES, indent=2)}

===== AVAILABLE BEATS =====

{json.dumps(BEAT_LIBRARY, indent=2)}

===== YOUR TASK =====

1. **Understand Intent** - Extract product, duration, style, mood
2. **Select Archetype** - Choose best match for the product
3. **Compose Beat Sequence** - CRITICAL: Total duration MUST equal requested duration, each beat MUST be 5/10/15s
4. **Build Style Specification** - Define aesthetic, colors, mood, lighting

===== VALIDATION CHECKLIST =====

Before returning, verify:
- ✓ Sum of beat durations == requested duration
- ✓ All beat_ids exist in BEAT_LIBRARY
- ✓ All beat durations are 5, 10, or 15 seconds
"""


# ===== Test Functions =====

def test_gpt4o_mini(prompt: str, creativity_level: float):
    """Test gpt-4o-mini with structured outputs"""
    
    print("\n" + "=" * 80)
    print("TEST: gpt-4o-mini with Structured Outputs")
    print("=" * 80)
    
    video_id = str(uuid.uuid4())
    start_time = time.time()
    
    print(f"\nVideo ID: {video_id}")
    print(f"Prompt: {prompt}")
    print(f"Creativity: {creativity_level}")
    
    try:
        # Build prompts
        system_prompt = build_gpt4_system_prompt()
        user_message = f"Create a video advertisement: {prompt}"
        
        print(f"\n📞 Calling gpt-4o-mini...")
        
        # Call gpt-4o-mini with Structured Outputs using responses API
        response = openai_client.client.responses.parse(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            text_format=VideoPlanning
        )
        
        # Get parsed output
        llm_output = response.output_parsed
        if llm_output is None:
            print(f"\n❌ gpt-4o-mini returned None")
            return False
        
        # Log usage
        if hasattr(response, 'usage') and response.usage:
            print(f"\n✅ gpt-4o-mini completed:")
            print(f"   Input tokens: {response.usage.input_tokens}")
            print(f"   Output tokens: {response.usage.output_tokens}")
            print(f"   Total tokens: {response.usage.total_tokens}")
            
            # Calculate cost (gpt-4o-mini: $0.15/$0.60 per 1M tokens)
            cost = (response.usage.input_tokens * 0.00000015) + (response.usage.output_tokens * 0.0000006)
            print(f"   Cost: ${cost:.4f}")
        else:
            print(f"\n✅ gpt-4o-mini completed (no usage info)")
        
        # Convert to dict
        llm_output_dict = llm_output.model_dump()
        
        print(f"\n📊 FULL LLM RESPONSE")
        print("=" * 80)
        print(json.dumps(llm_output_dict, indent=2))
        print("=" * 80)
        
        print(f"\n📊 Planning Summary:")
        print(f"   Archetype: {llm_output.selected_archetype}")
        print(f"   Reasoning: {llm_output.archetype_reasoning}")
        print(f"   Beats: {len(llm_output.beat_sequence)}")
        for i, beat in enumerate(llm_output.beat_sequence, 1):
            print(f"     {i}. {beat.beat_id} ({beat.duration}s)")
        print(f"   Beat Reasoning: {llm_output.beat_selection_reasoning}")
        
        if llm_output.reasoning_process:
            print(f"\n💭 Reasoning: {llm_output.reasoning_process}")
        
        # Validate and build spec
        llm_output_dict = validate_llm_beat_durations(llm_output_dict)
        spec = build_full_spec(llm_output_dict, video_id)
        validate_spec(spec)
        
        duration = time.time() - start_time
        print(f"\n✅ SUCCESS")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Video duration: {spec['duration']}s")
        
        return True
        
    except Exception as e:
        print(f"\n❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ===== Main =====

if __name__ == "__main__":
    print("=" * 80)
    print("🎬 Phase 1 Test - gpt-4o-mini with Structured Outputs")
    print("=" * 80)
    print()
    
    # Parse arguments
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    # Get prompt
    prompt = None
    if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        prompt = sys.argv[1]
    else:
        print("\nEnter your video prompt (or press Enter for default):")
        prompt = input("> ").strip()
        if not prompt:
            prompt = "Create a 15-second energetic ad for Nike Air Max sneakers, dynamic and bold"
            print(f"Using default: {prompt}")
    
    # Get creativity level
    creativity_level = BEAT_COMPOSITION_CREATIVITY
    if '--creativity' in sys.argv:
        idx = sys.argv.index('--creativity')
        if idx + 1 < len(sys.argv):
            creativity_level = float(sys.argv[idx + 1])
    
    print()
    print("📋 TEST CONFIGURATION")
    print("=" * 80)
    print(f"Model: gpt-4o-mini")
    print(f"Prompt: {prompt}")
    print(f"Creativity Level: {creativity_level}")
    print()
    
    # Test gpt-4o-mini only
    try:
        success = test_gpt4o_mini(prompt, creativity_level)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
