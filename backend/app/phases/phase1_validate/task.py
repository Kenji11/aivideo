"""
Phase 1: Intelligent Planning Task with o1-preview (Structured Outputs)

This implementation uses:
- o1-preview reasoning model for superior planning
- Structured Outputs via Pydantic schemas (no JSON parsing)
- Automatic fallback to GPT-4 Turbo if o1-preview fails
- Beat library (15 reusable beats)
- Template archetypes (5 high-level guides)
"""

import json
import time
import logging
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.services.openai import openai_client
from app.phases.phase1_validate.validation import validate_spec, build_full_spec, validate_llm_beat_durations
from app.phases.phase1_validate.schemas import VideoPlanning
from app.common.constants import BEAT_COMPOSITION_CREATIVITY, get_planning_temperature
from app.common.beat_library import BEAT_LIBRARY
from app.common.template_archetypes import TEMPLATE_ARCHETYPES
from app.database import SessionLocal
from app.common.models import VideoGeneration, VideoStatus
from app.orchestrator.progress import update_progress
from app.database.checkpoint_queries import create_checkpoint, create_artifact, approve_checkpoint, update_checkpoint_phase_output

logger = logging.getLogger(__name__)

# Configuration flags
USE_GPT4O_MINI = True  # Set to False to use GPT-4 Turbo by default
GPT4O_MINI_FALLBACK = True  # Auto-fallback to gpt-4-turbo-preview if gpt-4o-mini fails


# ===== Task Entry Point =====

@celery_app.task(bind=True)
def plan_video_intelligent(
    self,
    video_id: str,
    prompt: str,
    creativity_level: float = None,
    force_model: str = None  # "gpt-4o-mini
) -> dict:
    """
    Phase 1: Intelligent video planning using gpt-4o-mini with Structured Outputs.
    Falls back to gpt-4o if gpt-4o-mini fails.
    
    Args:
        video_id: Unique video identifier
        prompt: Natural language user prompt describing desired video
        creativity_level: 0.0-1.0 controlling creative freedom
                         (0.0 = strict template adherence, 1.0 = creative reinterpretation)
                         Defaults to BEAT_COMPOSITION_CREATIVITY config value
        force_model: Override model selection ("gpt-4o-mini" or "gpt-4o")
        
    Returns:
        PhaseOutput dict with:
        - status: "success" or "failed"
        - output_data: {"spec": complete_video_spec, "model_used": "...", ...}
        - cost_usd: API cost
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
    
    # Determine which model to use
    if force_model:
        use_mini = (force_model == "gpt-4o-mini")
        logger.info(f"   Model forced: {force_model}")
    else:
        use_mini = USE_GPT4O_MINI
        logger.info(f"   Using gpt-4o-mini: {use_mini}")
    
    try:
        if use_mini:
            # Try gpt-4o-mini first
            try:
                logger.info("   Attempting gpt-4o-mini...")
                result = plan_with_gpt4o_mini(video_id, prompt, creativity_level, start_time)
                logger.info("✅ gpt-4o-mini succeeded")
                return result

            except Exception as e:
                logger.error(f"❌ gpt-4o-mini failed: {str(e)}")

                if GPT4O_MINI_FALLBACK:
                    logger.info("🔄 Falling back to gpt-4-turbo-preview")
                    result = plan_with_gpt4_turbo(video_id, prompt, creativity_level, start_time)
                    logger.info("✅ gpt-4-turbo-preview fallback succeeded")
                    return result
                else:
                    raise
        else:
            # Use gpt-4-turbo-preview directly
            logger.info("   Using gpt-4-turbo-preview (direct)")
            result = plan_with_gpt4_turbo(video_id, prompt, creativity_level, start_time)
            logger.info("✅ gpt-4-turbo-preview succeeded")
            return result
        
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


# ===== Model-Specific Planning Functions =====

def plan_with_gpt4o_mini(
    video_id: str,
    prompt: str,
    creativity_level: float,
    start_time: float
) -> dict:
    """
    Plan video using gpt-4o-mini with Structured Outputs.
    
    gpt-4o-mini: Fast, cheap, and supports structured outputs.
    """
    
    # Build prompts (gpt-4o-mini supports system messages)
    system_prompt = build_gpt4_system_prompt()
    user_message = f"Create a video advertisement: {prompt}"
    
    logger.info(f"   Calling gpt-4o-mini with structured outputs...")
    
    # Call gpt-4o-mini with Structured Outputs using responses API
    response = openai_client.client.responses.parse(
        model="gpt-4o-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        text_format=VideoPlanning
    )
    
    # Get parsed output (automatically validated by Pydantic)
    llm_output = response.output_parsed
    
    if llm_output is None:
        logger.error(f"   o1-preview returned None output")
        raise ValueError(f"Model returned None output")
    
    # Log token usage
    if hasattr(response, 'usage') and response.usage:
        logger.info(f"   gpt-4o-mini completed:")
        logger.info(f"     Input tokens: {response.usage.input_tokens}")
        logger.info(f"     Output tokens: {response.usage.output_tokens}")
        logger.info(f"     Total tokens: {response.usage.total_tokens}")
    
    # Convert Pydantic model to dict for processing
    llm_output_dict = llm_output.model_dump()
    
    logger.info(f"📄 RAW LLM OUTPUT (gpt-4o-mini):")
    logger.info(json.dumps(llm_output_dict, indent=2))
    
    # Log planning results
    logger.info(f"   LLM selected archetype: {llm_output.selected_archetype}")
    logger.info(f"   LLM composed {len(llm_output.beat_sequence)} beats")
    
    # Validate and fix beat durations (ensures 5/10/15s only)
    llm_output_dict = validate_llm_beat_durations(llm_output_dict)
    
    # Build full spec from LLM output
    spec = build_full_spec(llm_output_dict, video_id)
    
    logger.info(f"📄 BUILT SPEC (gpt-4o-mini):")
    logger.info(json.dumps(spec, indent=2))
    
    # Validate spec meets all constraints
    validate_spec(spec)
    
    # Calculate actual cost (gpt-4o-mini pricing: $0.15/$0.60 per 1M tokens)
    if hasattr(response, 'usage') and response.usage:
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cost = (input_tokens * 0.00000015) + (output_tokens * 0.0000006)
    else:
        cost = 0.001  # Estimate if usage not available
    
    # Calculate duration
    duration_seconds = time.time() - start_time
    
    logger.info(f"✅ Phase 1 complete for video {video_id}")
    logger.info(f"   Cost: ${cost:.4f} (gpt-4o-mini)")
    logger.info(f"   Duration: {duration_seconds:.2f}s")
    logger.info(f"   Total video duration: {spec['duration']}s")
    logger.info(f"   Beats: {len(spec['beats'])}")

    # Build PhaseOutput
    output = PhaseOutput(
        video_id=video_id,
        phase="phase1_planning",
        status="success",
        output_data={
            "spec": spec,
            "model_used": "gpt-4o-mini"
        },
        cost_usd=cost,
        duration_seconds=duration_seconds,
        error_message=None
    )

    # Get user_id from video record
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            raise Exception(f"Video {video_id} not found")

        user_id = video.user_id

        # Create checkpoint record
        logger.info(f"Creating Phase 1 checkpoint for video {video_id}")
        checkpoint_id = create_checkpoint(
            video_id=video_id,
            branch_name='main',  # Always start on main branch
            phase_number=1,
            version=1,  # First version
            phase_output=output.model_dump(),
            cost_usd=cost,
            user_id=user_id,
            parent_checkpoint_id=None  # Root checkpoint
        )
        logger.info(f"✅ Created checkpoint {checkpoint_id}")

        # Create artifact for spec (stored in DB, not S3)
        artifact_id = create_artifact(
            checkpoint_id=checkpoint_id,
            artifact_type='spec',
            artifact_key='spec',
            s3_url='',  # Spec stored in DB, not S3
            s3_key='',
            version=1,
            metadata={'spec': spec}
        )
        logger.info(f"✅ Created spec artifact {artifact_id}")

        # Add checkpoint_id to output
        output.checkpoint_id = checkpoint_id

        # Update checkpoint's phase_output to include checkpoint_id for next phase
        update_checkpoint_phase_output(checkpoint_id, {'checkpoint_id': checkpoint_id})

        # Update video status to paused
        video.status = VideoStatus.PAUSED_AT_PHASE1
        video.current_phase = 'phase1'
        video.progress = 20.0  # Phase 1 complete (20% of total pipeline)
        if not video.phase_outputs:
            video.phase_outputs = {}
        video.phase_outputs['phase1_planning'] = output.model_dump()
        video.spec = spec  # Store spec in DB
        db.commit()
        logger.info(f"✅ Updated video status to PAUSED_AT_PHASE1")

        # Update progress in Redis
        update_progress(
            video_id,
            status='paused_at_phase1',
            current_phase='phase1',
            progress=20.0,
            spec=spec,
            phase_outputs=video.phase_outputs
        )

        # Check YOLO mode (auto_continue)
        if hasattr(video, 'auto_continue') and video.auto_continue:
            logger.info(f"🚀 YOLO mode enabled - auto-continuing to Phase 2")
            approve_checkpoint(checkpoint_id)

            # Import here to avoid circular dependency
            from app.orchestrator.pipeline import dispatch_next_phase
            dispatch_next_phase(video_id, checkpoint_id)
        else:
            logger.info(f"⏸️  Pipeline paused at Phase 1 - awaiting user approval")

    finally:
        db.close()

    # Success - return PhaseOutput with checkpoint_id
    return output.model_dump()


def plan_with_gpt4_turbo(
    video_id: str,
    prompt: str,
    creativity_level: float,
    start_time: float
) -> dict:
    """
    Plan video using gpt-4-turbo-preview with JSON mode (fallback or direct use).
    
    Uses traditional JSON mode since gpt-4-turbo-preview doesn't support structured outputs.
    """
    
    # Build separate system and user prompts
    system_prompt = build_gpt4_system_prompt()
    user_message = f"Create a video advertisement: {prompt}"
    
    # Calculate temperature
    temperature = get_planning_temperature(creativity_level)
    
    logger.info(f"   Calling gpt-4-turbo-preview with JSON mode...")
    logger.info(f"   Temperature: {temperature}")
    
    # Call gpt-4-turbo-preview with traditional JSON mode (not structured outputs)
    response = openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        response_format={"type": "json_object"},
        temperature=temperature
    )
    
    # Parse JSON response
    llm_output_dict = json.loads(response.choices[0].message.content)
    
    logger.info(f"📄 RAW LLM OUTPUT (gpt-4-turbo-preview):")
    logger.info(json.dumps(llm_output_dict, indent=2))
    
    # Log planning results
    logger.info(f"   LLM selected archetype: {llm_output_dict.get('selected_archetype')}")
    logger.info(f"   LLM composed {len(llm_output_dict.get('beat_sequence', []))} beats")
    
    # Validate and fix beat durations
    llm_output_dict = validate_llm_beat_durations(llm_output_dict)
    
    # Build full spec
    spec = build_full_spec(llm_output_dict, video_id)
    
    logger.info(f"📄 BUILT SPEC (gpt-4-turbo-preview):")
    logger.info(json.dumps(spec, indent=2))
    
    # Validate spec
    validate_spec(spec)
    
    # Calculate actual cost (gpt-4-turbo-preview: $10/$30 per 1M tokens)
    if hasattr(response, 'usage') and response.usage:
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens * 0.000010) + (output_tokens * 0.000030)
    else:
        cost = 0.02  # Estimate if usage not available
    
    # Calculate duration
    duration_seconds = time.time() - start_time
    
    logger.info(f"✅ Phase 1 complete for video {video_id}")
    logger.info(f"   Cost: ${cost:.4f} (gpt-4-turbo-preview)")
    logger.info(f"   Duration: {duration_seconds:.2f}s")
    logger.info(f"   Total video duration: {spec['duration']}s")
    logger.info(f"   Beats: {len(spec['beats'])}")

    # Build PhaseOutput
    output = PhaseOutput(
        video_id=video_id,
        phase="phase1_planning",
        status="success",
        output_data={
            "spec": spec,
            "model_used": "gpt-4-turbo-preview"
        },
        cost_usd=cost,
        duration_seconds=duration_seconds,
        error_message=None
    )

    # Get user_id from video record
    db = SessionLocal()
    try:
        video = db.query(VideoGeneration).filter(VideoGeneration.id == video_id).first()
        if not video:
            logger.error(f"Video {video_id} not found")
            raise Exception(f"Video {video_id} not found")

        user_id = video.user_id

        # Create checkpoint record
        logger.info(f"Creating Phase 1 checkpoint for video {video_id}")
        checkpoint_id = create_checkpoint(
            video_id=video_id,
            branch_name='main',  # Always start on main branch
            phase_number=1,
            version=1,  # First version
            phase_output=output.model_dump(),
            cost_usd=cost,
            user_id=user_id,
            parent_checkpoint_id=None  # Root checkpoint
        )
        logger.info(f"✅ Created checkpoint {checkpoint_id}")

        # Create artifact for spec (stored in DB, not S3)
        artifact_id = create_artifact(
            checkpoint_id=checkpoint_id,
            artifact_type='spec',
            artifact_key='spec',
            s3_url='',  # Spec stored in DB, not S3
            s3_key='',
            version=1,
            metadata={'spec': spec}
        )
        logger.info(f"✅ Created spec artifact {artifact_id}")

        # Add checkpoint_id to output
        output.checkpoint_id = checkpoint_id

        # Update checkpoint's phase_output to include checkpoint_id for next phase
        update_checkpoint_phase_output(checkpoint_id, {'checkpoint_id': checkpoint_id})

        # Update video status to paused
        video.status = VideoStatus.PAUSED_AT_PHASE1
        video.current_phase = 'phase1'
        video.progress = 20.0  # Phase 1 complete (20% of total pipeline)
        if not video.phase_outputs:
            video.phase_outputs = {}
        video.phase_outputs['phase1_planning'] = output.model_dump()
        video.spec = spec  # Store spec in DB
        db.commit()
        logger.info(f"✅ Updated video status to PAUSED_AT_PHASE1")

        # Update progress in Redis
        update_progress(
            video_id,
            status='paused_at_phase1',
            current_phase='phase1',
            progress=20.0,
            spec=spec,
            phase_outputs=video.phase_outputs
        )

        # Check YOLO mode (auto_continue)
        if hasattr(video, 'auto_continue') and video.auto_continue:
            logger.info(f"🚀 YOLO mode enabled - auto-continuing to Phase 2")
            approve_checkpoint(checkpoint_id)

            # Import here to avoid circular dependency
            from app.orchestrator.pipeline import dispatch_next_phase
            dispatch_next_phase(video_id, checkpoint_id)
        else:
            logger.info(f"⏸️  Pipeline paused at Phase 1 - awaiting user approval")

    finally:
        db.close()

    # Success - return PhaseOutput with checkpoint_id
    return output.model_dump()


# ===== Prompt Builders =====

def build_gpt4_system_prompt() -> str:
    """
    Build system prompt for GPT-4 Turbo (kept separate from user message).
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
     * Each beat MUST be 5s, 10s, or 15s (NO other durations allowed)
     * First beat should typically be from opening beats (typical_position: "opening")
     * Last beat should typically be from closing beats (typical_position: "closing")
     * Middle beats from middle beats (typical_position: "middle")
     * Sum of all beat durations MUST equal total duration EXACTLY
   - Follow the selected archetype's narrative_structure
   - Maintain appropriate energy_curve
   - Ensure beat_ids match exactly those in the AVAILABLE BEATS library

4. **Build Style Specification**
   - Define: aesthetic (string describing overall visual style)
   - color_palette: array of 3-5 color names
   - mood: single word mood (energetic|elegant|minimalist|emotional|informative)
   - lighting: lighting style description
   - Ensure style matches the archetype and user's keywords

===== VALIDATION CHECKLIST =====

Before returning, verify:
- ✓ Sum of beat durations == requested duration
- ✓ All beat_ids exist in BEAT_LIBRARY
- ✓ First beat has typical_position: "opening" (recommended)
- ✓ Last beat has typical_position: "closing" (recommended)
- ✓ All beat durations are 5, 10, or 15 seconds
- ✓ Style matches selected archetype and user keywords

If validation fails, adjust your beat sequence until it passes.

The response will be parsed as structured JSON matching the VideoPlanning schema.
"""
