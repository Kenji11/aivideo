"""
Phase 0: Reference Asset Preparation Task

Extracts entities from prompt and recommends best matching reference assets.
Runs before Phase 1 planning to inform LLM's reference asset decisions.
"""

import time
import logging
from app.orchestrator.celery_app import celery_app
from app.common.schemas import PhaseOutput
from app.phases.phase0_reference_prep.entity_extraction import entity_extraction_service
from app.phases.phase0_reference_prep.product_selector import product_selector_service
from app.common.constants import COST_GPT4_TURBO

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def prepare_references(
    self,
    video_id: str,
    prompt: str,
    user_id: str
) -> dict:
    """
    Phase 0: Reference asset preparation.
    
    Checks if user has assets, extracts entities, and recommends best matches.
    Skips entity extraction if user has 0 assets (performance optimization).
    
    Args:
        video_id: Video generation ID
        prompt: User's video generation prompt
        user_id: User ID
        
    Returns:
        PhaseOutput dict with:
            - phase: "phase0_reference_prep"
            - output_data:
                - entities: extracted entities dict (or empty)
                - user_assets: list of ALL available assets with metadata
                - recommended_product: best matching product asset
                - recommended_logo: best matching logo asset
                - selection_rationale: why these were recommended
                - has_assets: boolean
            - cost_usd: API cost (if extraction ran)
            - duration_seconds: execution time
    """
    start_time = time.time()
    
    logger.info(f"🔍 Phase 0 (Reference Preparation) starting for video {video_id}")
    logger.info(f"   User: {user_id}")
    logger.info(f"   Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    
    try:
        # Step 1: Extract entities (checks for assets internally)
        extraction_result = entity_extraction_service.extract_entities_from_prompt(
            user_id=user_id,
            prompt=prompt
        )
        
        entities = extraction_result["entities"]
        user_assets = extraction_result["user_assets"]
        has_assets = extraction_result["has_assets"]
        product_mentioned = extraction_result["product_mentioned"]
        
        # If user has no assets, return early
        if not has_assets:
            logger.info("✅ Phase 0 complete - User has no assets, skipping recommendations")
            duration = time.time() - start_time
            
            return PhaseOutput(
                video_id=video_id,
                phase="phase0_reference_prep",
                status="success",
                output_data={
                    "entities": {},
                    "user_assets": [],
                    "recommended_product": None,
                    "recommended_logo": None,
                    "selection_rationale": "User has no reference assets uploaded",
                    "has_assets": False,
                    "product_mentioned": False
                },
                cost_usd=0.0,
                duration_seconds=duration
            ).dict()
        
        logger.info(f"   Extracted entities: product={entities.get('product')}, brand={entities.get('brand')}, category={entities.get('product_category')}")
        logger.info(f"   User has {len(user_assets)} assets")
        logger.info(f"   Product mentioned in prompt: {product_mentioned}")
        
        # Step 2: Select best product
        product_selection = product_selector_service.select_best_product(
            user_assets=user_assets,
            entities=entities,
            prompt=prompt
        )
        
        recommended_product = product_selection["selected_product"]
        product_rationale = product_selection["selection_rationale"]
        product_confidence = product_selection["confidence"]
        
        if recommended_product:
            logger.info(f"   Recommended product: {recommended_product.get('name')} (confidence: {product_confidence:.2f})")
            logger.info(f"   Rationale: {product_rationale}")
        else:
            logger.info("   No suitable product found")
        
        # Step 3: Select best logo
        logo_selection = product_selector_service.select_best_logo(
            user_assets=user_assets,
            entities=entities
        )
        
        recommended_logo = logo_selection["selected_logo"]
        logo_rationale = logo_selection["selection_rationale"]
        logo_confidence = logo_selection["confidence"]
        
        if recommended_logo:
            logger.info(f"   Recommended logo: {recommended_logo.get('name')} (confidence: {logo_confidence:.2f})")
            logger.info(f"   Rationale: {logo_rationale}")
        else:
            logger.info("   No logo found")
        
        # Step 4: Combine rationales
        combined_rationale = []
        if recommended_product:
            combined_rationale.append(f"Product: {product_rationale}")
        if recommended_logo:
            combined_rationale.append(f"Logo: {logo_rationale}")
        
        if not combined_rationale:
            combined_rationale.append("No suitable assets found for recommendations")
        
        selection_rationale = " | ".join(combined_rationale)
        
        # Calculate cost (entity extraction uses gpt-4o-mini, roughly $0.001 per call)
        # More accurate: input tokens * $0.15/1M + output tokens * $0.60/1M
        # For simplicity, estimate ~$0.002 per extraction call
        cost_usd = 0.002 if has_assets else 0.0
        
        duration = time.time() - start_time
        
        logger.info(f"✅ Phase 0 complete in {duration:.2f}s (cost: ${cost_usd:.4f})")
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase0_reference_prep",
            status="success",
            output_data={
                "entities": entities,
                "user_assets": user_assets,
                "recommended_product": recommended_product,
                "recommended_logo": recommended_logo,
                "selection_rationale": selection_rationale,
                "product_confidence": product_confidence if recommended_product else 0.0,
                "logo_confidence": logo_confidence if recommended_logo else 0.0,
                "has_assets": True,
                "product_mentioned": product_mentioned
            },
            cost_usd=cost_usd,
            duration_seconds=duration
        ).dict()
    
    except Exception as e:
        duration = time.time() - start_time
        error_msg = f"Phase 0 failed: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        
        return PhaseOutput(
            video_id=video_id,
            phase="phase0_reference_prep",
            status="failed",
            output_data={},
            cost_usd=0.0,
            duration_seconds=duration,
            error_message=error_msg
        ).dict()

