#!/usr/bin/env python3
"""
Test Phase 1 Intelligent Planning - Beat-Based Architecture

This script tests the new intelligent planning system that uses:
- Beat library (15 reusable beats)
- Template archetypes (5 high-level guides)
- Single LLM agent for composition
- Creativity control via temperature mapping

Usage:
    python scripts/test_phase1_intelligent.py
    python scripts/test_phase1_intelligent.py "Create a 15-second Nike ad, energetic style"
    python scripts/test_phase1_intelligent.py --creativity 0.8
"""

import sys
import os
import json
import uuid
from pathlib import Path
from typing import Optional

# Load .env if exists
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"⚠️  No .env file found at {env_path}")
    print("   Make sure environment variables are set")

# Override database URL for local testing (connects to Docker Compose postgres on localhost)
os.environ['DATABASE_URL'] = 'postgresql://dev:devpass@localhost:5434/videogen'

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.phases.phase1_validate.prompts import build_planning_system_prompt
from app.phases.phase1_validate.validation import validate_spec, build_full_spec
from app.common.constants import BEAT_COMPOSITION_CREATIVITY, get_planning_temperature
from app.services.openai import openai_client


def test_phase1_intelligent(
    prompt: Optional[str] = None,
    creativity_level: Optional[float] = None
):
    """
    Test Phase 1 intelligent planning without Celery.
    
    Args:
        prompt: User prompt for video generation
        creativity_level: 0.0-1.0 creativity control (None = use config default)
    """
    
    print("=" * 80)
    print("🎬 Phase 1 Intelligent Planning Test - Beat-Based Architecture")
    print("=" * 80)
    print()
    
    # Get prompt from argument or user input
    if not prompt:
        if len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
            prompt = sys.argv[1]
        else:
            print("Enter your video prompt (or press Enter for default):")
            prompt = input("> ").strip()
            if not prompt:
                prompt = "Create a 15-second ad for Nike sneakers, energetic and urban style"
                print(f"Using default: {prompt}")
    
    # Get creativity level from argument or default
    if creativity_level is None:
        if '--creativity' in sys.argv:
            idx = sys.argv.index('--creativity')
            if idx + 1 < len(sys.argv):
                creativity_level = float(sys.argv[idx + 1])
        else:
            creativity_level = BEAT_COMPOSITION_CREATIVITY
    
    # Generate video ID
    video_id = str(uuid.uuid4())
    
    print()
    print("📋 INPUTS")
    print("=" * 80)
    print(f"Video ID: {video_id}")
    print(f"Prompt: {prompt}")
    print(f"Creativity Level: {creativity_level}")
    print(f"Temperature: {get_planning_temperature(creativity_level)}")
    print()
    
    try:
        # Build system prompt
        print("🔨 Building system prompt...")
        system_prompt = build_planning_system_prompt()
        print(f"   System prompt: {len(system_prompt)} characters")
        print(f"   Contains {system_prompt.count('beat_id')} beat references")
        print()
        
        # Build user message
        user_message = f"Create a video advertisement: {prompt}"
        
        # Calculate temperature
        temperature = get_planning_temperature(creativity_level)
        
        print("🤖 Calling GPT-4 Turbo...")
        print(f"   Model: gpt-4-turbo-preview")
        print(f"   Temperature: {temperature}")
        print(f"   Response format: JSON")
        print()
        
        # Call GPT-4
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=temperature
        )
        
        # Parse response
        llm_output = json.loads(response.choices[0].message.content)
        
        print("📊 LLM OUTPUT (Raw)")
        print("=" * 80)
        print(json.dumps(llm_output, indent=2))
        print()
        
        # Build full spec
        print("🔨 Building full specification...")
        spec = build_full_spec(llm_output, video_id)
        print(f"   Template: {spec['template']}")
        print(f"   Duration: {spec['duration']}s")
        print(f"   Beats: {len(spec['beats'])}")
        print()
        
        # Validate spec
        print("✅ Validating specification...")
        validate_spec(spec)
        print("   All validations passed!")
        print()
        
        # Display spec details
        print("📊 FULL SPECIFICATION")
        print("=" * 80)
        print(f"Template Archetype: {spec['template']}")
        print(f"Duration: {spec['duration']}s")
        print(f"Resolution: {spec['resolution']}")
        print(f"FPS: {spec['fps']}")
        print()
        
        print("Product:")
        print(f"  Name: {spec['product']['name']}")
        print(f"  Category: {spec['product']['category']}")
        print()
        
        print("Style:")
        print(f"  Aesthetic: {spec['style']['aesthetic']}")
        print(f"  Mood: {spec['style']['mood']}")
        print(f"  Color Palette: {', '.join(spec['style']['color_palette'])}")
        print(f"  Lighting: {spec['style']['lighting']}")
        print()
        
        print(f"Beats ({len(spec['beats'])} total):")
        for i, beat in enumerate(spec['beats'], 1):
            print(f"  {i}. [{beat['start']}s-{beat['start']+beat['duration']}s] {beat['beat_id']} ({beat['duration']}s)")
            print(f"     Shot: {beat['shot_type']} | Action: {beat['action']}")
            print(f"     Camera: {beat['camera_movement']} | Energy: {beat['energy_level']}")
        print()
        
        print("LLM Reasoning:")
        print(f"  Selected Archetype: {spec['llm_reasoning']['selected_archetype']}")
        print(f"  Archetype Reasoning: {spec['llm_reasoning']['archetype_reasoning']}")
        print(f"  Beat Selection: {spec['llm_reasoning']['beat_selection_reasoning']}")
        print()
        
        # Save spec to file
        output_file = Path(__file__).parent / f"phase1_output_{video_id}.json"
        with open(output_file, 'w') as f:
            json.dump(spec, f, indent=2)
        
        print("=" * 80)
        print("✅ Phase 1 Test: SUCCESS!")
        print("=" * 80)
        print(f"Video ID: {video_id}")
        print(f"Spec saved to: {output_file}")
        print(f"Total Duration: {spec['duration']}s")
        print(f"Total Beats: {len(spec['beats'])}")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ Phase 1 Test: FAILED")
        print("=" * 80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print()
        print("Full Traceback:")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return 1


if __name__ == "__main__":
    # Parse arguments
    prompt = None
    creativity = None
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        sys.exit(0)
    
    # Get prompt from first non-flag argument
    for arg in sys.argv[1:]:
        if not arg.startswith('--'):
            prompt = arg
            break
    
    # Get creativity from --creativity flag
    if '--creativity' in sys.argv:
        idx = sys.argv.index('--creativity')
        if idx + 1 < len(sys.argv):
            creativity = float(sys.argv[idx + 1])
    
    exit_code = test_phase1_intelligent(prompt, creativity)
    sys.exit(exit_code)

