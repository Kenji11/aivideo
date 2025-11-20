"""
Phase 1: Intelligent Planning Task (TDD Beat-Based Architecture)

This is the NEW intelligent planning task that uses:
- Beat library (15 reusable beats)
- Template archetypes (5 high-level guides)
- Single LLM agent for composition
- Creativity control via temperature mapping

This replaces the old template selection approach.
"""

import json
import time
import logging
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.services.openai import openai_client
from app.phases.phase1_validate.prompts import build_planning_system_prompt
from app.phases.phase1_validate.validation import validate_spec, build_full_spec, validate_llm_beat_durations
from app.common.constants import BEAT_COMPOSITION_CREATIVITY, get_planning_temperature

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def plan_video_intelligent(
    self,
    video_id: str,
    prompt: str,
    creativity_level: float = None
) -> dict:
    """
    Phase 1: Intelligent video planning using single LLM agent.
    
    The LLM analyzes the user's prompt and:
    1. Selects appropriate template archetype
    2. Composes custom beat sequence from beat library
    3. Builds complete style specification
    
    Args:
        video_id: Unique video identifier
        prompt: Natural language user prompt describing desired video
        creativity_level: 0.0-1.0 controlling LLM temperature
                         (0.0 = strict template adherence, 1.0 = creative reinterpretation)
                         Defaults to BEAT_COMPOSITION_CREATIVITY config value
        
    Returns:
        PhaseOutput dict with:
        - status: "success" or "failed"
        - output_data: {"spec": complete_video_spec}
        - cost_usd: GPT-4 API cost
        - duration_seconds: Time taken
        - error_message: Error details if failed
    """
    start_time = time.time()
    
    # Use config default if creativity_level not specified
    if creativity_level is None:
        creativity_level = BEAT_COMPOSITION_CREATIVITY
    
    # Log phase start
    logger.info(f"🚀 Phase 1 (Intelligent Planning) starting for video {video_id}")
    logger.info(f"   Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    logger.info(f"   Creativity level: {creativity_level}")
    
    try:
        # Build comprehensive system prompt with all archetypes and beats
        system_prompt = build_planning_system_prompt()
        
        # Build user message
        user_message = f"Create a video advertisement: {prompt}"
        
        # Calculate temperature from creativity level
        # 0.0 → 0.2 (strict), 0.5 → 0.5 (balanced), 1.0 → 0.8 (creative)
        temperature = get_planning_temperature(creativity_level)
        
        logger.info(f"   Calling GPT-4 with temperature={temperature}")
        
        # Call GPT-4 Turbo with JSON mode
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=temperature
        )
        
        # Parse LLM response
        llm_output = json.loads(response.choices[0].message.content)
        
        logger.info(f"   LLM selected archetype: {llm_output.get('selected_archetype')}")
        logger.info(f"   LLM composed {len(llm_output.get('beat_sequence', []))} beats")
        
        # Validate and fix LLM beat durations BEFORE building full spec
        # Ensures all beat durations are 5s, 10s, or 15s (no fractional/invalid durations)
        llm_output = validate_llm_beat_durations(llm_output)
        
        # Build full spec from LLM output
        # Fills in beat details from library and substitutes product/style
        spec = build_full_spec(llm_output, video_id)
        
        # Validate spec meets all constraints
        # Checks duration sums, valid beat durations (5/10/15s), beat_ids exist
        validate_spec(spec)
        
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        logger.info(f"✅ Phase 1 complete for video {video_id}")
        logger.info(f"   Duration: {duration_seconds:.2f}s")
        logger.info(f"   Total video duration: {spec['duration']}s")
        logger.info(f"   Beats: {len(spec['beats'])}")
        
        # Success - return PhaseOutput
        return PhaseOutput(
            video_id=video_id,
            phase="phase1_planning",
            status="success",
            output_data={"spec": spec},
            cost_usd=0.02,  # GPT-4 Turbo approximate cost
            duration_seconds=duration_seconds,
            error_message=None
        ).dict()
        
    except Exception as e:
        # Calculate duration
        duration_seconds = time.time() - start_time
        
        logger.error(f"❌ Phase 1 failed for video {video_id}: {str(e)}")
        logger.error(f"   Error type: {type(e).__name__}")
        
        # Failure - return PhaseOutput with error
        return PhaseOutput(
            video_id=video_id,
            phase="phase1_planning",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration_seconds,
            error_message=str(e)
        ).dict()

