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

logger = logging.getLogger(__name__)

# Configuration flags
USE_GPT4O_MINI = True  # Set to False to use GPT-4 Turbo by default
GPT4O_MINI_FALLBACK = True  # Auto-fallback to gpt-4-turbo-preview if gpt-4o-mini fails


# ===== Task Entry Point =====

@celery_app.task(bind=True)
def plan_video_intelligent(
    self,
    phase0_output: dict,
    video_id: str = None,
    prompt: str = None,
    creativity_level: float = None,
    force_model: str = None  # "gpt-4o-mini
) -> dict:
    """
    Phase 1: Intelligent video planning using gpt-4o-mini with Structured Outputs.
    Falls back to gpt-4o if gpt-4o-mini fails.
    
    Args:
        phase0_output: Output from Phase 0 (reference preparation) containing:
                      - video_id, entities, user_assets, recommended_product, recommended_logo
        video_id: Unique video identifier (fallback if not in phase0_output)
        prompt: Natural language user prompt (fallback if not in phase0_output)
        creativity_level: 0.0-1.0 controlling creative freedom
                         (0.0 = strict template adherence, 1.0 = creative reinterpretation)
                         Defaults to BEAT_COMPOSITION_CREATIVITY config value
        force_model: Override model selection ("gpt-4o-mini" or "gpt-4o")
        
    Returns:
        PhaseOutput dict with:
        - status: "success" or "failed"
        - output_data: {"spec": complete_video_spec, "reference_mapping": {...}, "model_used": "...", ...}
        - cost_usd: API cost
        - duration_seconds: Time taken
        - error_message: Error details if failed
    """
    start_time = time.time()
    
    # Extract data from phase0_output
    if phase0_output:
        video_id = phase0_output.get('video_id', video_id)
        # Note: prompt should be passed separately, not from phase0
        output_data = phase0_output.get('output_data', {})
        entities = output_data.get('entities', {})
        user_assets = output_data.get('user_assets', [])
        recommended_product = output_data.get('recommended_product')
        recommended_logo = output_data.get('recommended_logo')
        has_assets = output_data.get('has_assets', False)
        product_mentioned = output_data.get('product_mentioned', False)
    else:
        # Fallback if no Phase 0 output (backward compatibility)
        entities = {}
        user_assets = []
        recommended_product = None
        recommended_logo = None
        has_assets = False
        product_mentioned = False
    
    # Use config default if creativity_level not specified
    if creativity_level is None:
        creativity_level = BEAT_COMPOSITION_CREATIVITY
    
    # Log phase start
    logger.info(f"🚀 Phase 1 (Intelligent Planning) starting for video {video_id}")
    logger.info(f"   Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    logger.info(f"   Creativity level: {creativity_level}")
    logger.info(f"   User has assets: {has_assets}")
    if has_assets:
        logger.info(f"   Assets available: {len(user_assets)}")
        if recommended_product:
            logger.info(f"   Recommended product: {recommended_product.get('name', 'N/A')}")
        if recommended_logo:
            logger.info(f"   Recommended logo: {recommended_logo.get('name', 'N/A')}")
    
    # Determine which model to use
    if force_model:
        use_mini = (force_model == "gpt-4o-mini")
        logger.info(f"   Model forced: {force_model}")
    else:
        use_mini = USE_GPT4O_MINI
        logger.info(f"   Using gpt-4o-mini: {use_mini}")
    
    # Package reference context for planning functions
    reference_context = {
        'has_assets': has_assets,
        'entities': entities,
        'user_assets': user_assets,
        'recommended_product': recommended_product,
        'recommended_logo': recommended_logo,
        'product_mentioned': product_mentioned
    }
    
    try:
        if use_mini:
            # Try gpt-4o-mini first
            try:
                logger.info("   Attempting gpt-4o-mini...")
                result = plan_with_gpt4o_mini(video_id, prompt, creativity_level, start_time, reference_context, phase0_output)
                logger.info("✅ gpt-4o-mini succeeded")
                return result
            
            except Exception as e:
                logger.error(f"❌ gpt-4o-mini failed: {str(e)}")
                
                if GPT4O_MINI_FALLBACK:
                    logger.info("🔄 Falling back to gpt-4-turbo-preview")
                    result = plan_with_gpt4_turbo(video_id, prompt, creativity_level, start_time, reference_context, phase0_output)
                    logger.info("✅ gpt-4-turbo-preview fallback succeeded")
                    return result
                else:
                    raise
        else:
            # Use gpt-4-turbo-preview directly
            logger.info("   Using gpt-4-turbo-preview (direct)")
            result = plan_with_gpt4_turbo(video_id, prompt, creativity_level, start_time, reference_context, phase0_output)
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
    start_time: float,
    reference_context: dict = None,
    phase0_output: dict = None
) -> dict:
    """
    Plan video using gpt-4o-mini with Structured Outputs.
    
    gpt-4o-mini: Fast, cheap, and supports structured outputs.
    """
    
    # Build prompts (gpt-4o-mini supports system messages)
    system_prompt = build_gpt4_system_prompt(reference_context)
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
    
    # Extract reference_mapping if present
    reference_mapping = llm_output_dict.get('reference_mapping', {})
    if reference_mapping:
        logger.info(f"   LLM generated reference_mapping for {len(reference_mapping)} beats")
    
    # Validate reference asset usage if user has assets
    if reference_context and reference_context.get('has_assets'):
        validate_reference_asset_usage(reference_mapping, reference_context)
    
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
    
    # Success - return PhaseOutput
    return PhaseOutput(
        video_id=video_id,
        phase="phase1_planning",
        status="success",
        output_data={
            "spec": spec,
            "reference_mapping": reference_mapping,
            "model_used": "gpt-4o-mini",
            "phase0_output": phase0_output  # Pass Phase 0 output for Phase 2
        },
        cost_usd=cost,
        duration_seconds=duration_seconds,
        error_message=None
    ).dict()


def plan_with_gpt4_turbo(
    video_id: str,
    prompt: str,
    creativity_level: float,
    start_time: float,
    reference_context: dict = None,
    phase0_output: dict = None
) -> dict:
    """
    Plan video using gpt-4-turbo-preview with JSON mode (fallback or direct use).
    
    Uses traditional JSON mode since gpt-4-turbo-preview doesn't support structured outputs.
    """
    
    # Build separate system and user prompts
    system_prompt = build_gpt4_system_prompt(reference_context)
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
    
    # Extract reference_mapping if present
    reference_mapping = llm_output_dict.get('reference_mapping', {})
    if reference_mapping:
        logger.info(f"   LLM generated reference_mapping for {len(reference_mapping)} beats")
    
    # Validate reference asset usage if user has assets
    if reference_context and reference_context.get('has_assets'):
        validate_reference_asset_usage(reference_mapping, reference_context)
    
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
    
    # Success - return PhaseOutput
    return PhaseOutput(
        video_id=video_id,
        phase="phase1_planning",
        status="success",
        output_data={
            "spec": spec,
            "reference_mapping": reference_mapping,
            "model_used": "gpt-4-turbo-preview",
            "phase0_output": phase0_output  # Pass Phase 0 output for Phase 2
        },
        cost_usd=cost,
        duration_seconds=duration_seconds,
        error_message=None
    ).dict()


# ===== Prompt Builders =====

def validate_reference_asset_usage(reference_mapping: dict, reference_context: dict):
    """
    Validate that LLM used reference assets appropriately.
    
    Checks:
    - If user has products → at least one product beat should have product reference
    - If user has logo → closing beat should have logo reference
    - Asset IDs in mapping exist in user's library
    
    Logs warnings if validation fails but doesn't raise exceptions
    (LLM may have good reasons for decisions).
    """
    user_assets = reference_context.get('user_assets', [])
    recommended_product = reference_context.get('recommended_product')
    recommended_logo = reference_context.get('recommended_logo')
    
    # Build asset ID lookup
    valid_asset_ids = {asset['asset_id'] for asset in user_assets}
    
    # Check if referenced assets exist
    for beat_id, mapping in reference_mapping.items():
        asset_ids = mapping.get('asset_ids', [])
        for asset_id in asset_ids:
            if asset_id not in valid_asset_ids:
                logger.warning(f"   ⚠️  Beat '{beat_id}' references unknown asset '{asset_id}'")
    
    # Check if product was used (if available)
    if recommended_product:
        product_id = recommended_product['asset_id']
        product_used = any(
            product_id in mapping.get('asset_ids', [])
            for mapping in reference_mapping.values()
        )
        if not product_used:
            logger.warning(f"   ⚠️  Recommended product '{recommended_product.get('name')}' was NOT used in any beat")
            logger.warning(f"       This is an advertising app - products should be featured!")
        else:
            logger.info(f"   ✓ Recommended product is used in reference_mapping")
    
    # Check if logo was used in closing (if available)
    if recommended_logo:
        logo_id = recommended_logo['asset_id']
        logo_used = any(
            logo_id in mapping.get('asset_ids', [])
            for mapping in reference_mapping.values()
        )
        if not logo_used:
            logger.warning(f"   ⚠️  Recommended logo '{recommended_logo.get('name')}' was NOT used in any beat")
            logger.warning(f"       Logos should ALWAYS appear in closing beats for brand reinforcement!")
        else:
            logger.info(f"   ✓ Recommended logo is used in reference_mapping")
    
    logger.info(f"   Reference asset validation complete")


def build_reference_asset_guidelines(reference_context: dict) -> str:
    """
    Build reference asset usage guidelines section for system prompt.
    
    This section is ONLY included if user has reference assets available.
    Kept minimal - Phase 0 already did the selection work, Phase 1 just decides placement.
    """
    recommended_product = reference_context.get('recommended_product')
    recommended_logo = reference_context.get('recommended_logo')
    
    if not recommended_product and not recommended_logo:
        logger.info("📋 No reference assets to include in prompt")
        return ""
    
    product_id = recommended_product.get('asset_id') if recommended_product else None
    product_name = recommended_product.get('name', 'Product') if recommended_product else None
    logo_id = recommended_logo.get('asset_id') if recommended_logo else None
    logo_name = recommended_logo.get('name', 'Logo') if recommended_logo else None
    
    # Build example mapping parts
    product_example = f'    "hero_shot": {{\n      "asset_ids": ["{product_id}"],\n      "usage_type": "product",\n      "rationale": "Hero shot showcases the product"\n    }}' if recommended_product else ''
    logo_example = f'    "call_to_action": {{\n      "asset_ids": ["{logo_id}"],\n      "usage_type": "logo",\n      "rationale": "Closing beat includes brand logo"\n    }}' if recommended_logo else ''
    comma = ',' if (recommended_product and recommended_logo) else ''
    
    section = f"""
===== REFERENCE ASSETS =====

{'' if not recommended_product else f"User has uploaded product '{product_name}' (ID: {product_id}) - decide when/if to include in beats using reference_mapping."}
{'' if not recommended_logo else f"User has uploaded logo '{logo_name}' (ID: {logo_id}) - always include in closing beats using reference_mapping."}

**CRITICAL: reference_mapping Structure**
Keys MUST be beat_ids from your beat_sequence (e.g., 'hero_shot', 'dynamic_intro'), NOT asset IDs.

**Example reference_mapping:**
```json
{{
  "reference_mapping": {{
{product_example}{comma}
{logo_example}
  }}
}}
```
"""
    
    logger.info("📋 Built reference asset guidelines section:")
    logger.info(section)
    
    return section


def build_gpt4_system_prompt(reference_context: dict = None) -> str:
    """
    Build system prompt for GPT-4 Turbo (kept separate from user message).
    
    Args:
        reference_context: Optional dict containing Phase 0 reference asset information
    """
    
    # Build reference asset section if available
    reference_section = ""
    if reference_context and reference_context.get('has_assets'):
        reference_section = build_reference_asset_guidelines(reference_context)
    
    return f"""You are a professional video director and creative strategist. Your job is to plan a complete video advertisement based on the user's request.

{reference_section}

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
