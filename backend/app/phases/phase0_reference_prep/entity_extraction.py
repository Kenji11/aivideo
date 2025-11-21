"""
Entity Extraction Service

Extracts relevant entities from user prompts to match against reference assets.
Only runs if user has reference assets available (performance optimization).
"""

import logging
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.services.openai import openai_client
from app.database import SessionLocal
from app.phases.phase0_reference_prep.prompts import build_entity_extraction_prompt

logger = logging.getLogger(__name__)


class EntityExtractionService:
    """Service for extracting entities from user prompts"""
    
    def __init__(self):
        self.model = "gpt-4o-mini"  # Cheaper, fast enough for entity extraction
        self.temperature = 0.3  # More deterministic
    
    def extract_entities_from_prompt(
        self, 
        user_id: str, 
        prompt: str
    ) -> dict:
        """
        Extract entities from user prompt to match against reference assets.
        
        Checks if user has assets first - if not, returns empty result immediately
        (performance optimization: skip LLM call if user has no assets).
        
        Args:
            user_id: User ID to check for assets
            prompt: User's video generation prompt
            
        Returns:
            dict with:
                - entities: dict with product, brand, product_category, style_keywords
                - user_assets: list of user's available assets with metadata
                - has_assets: boolean
                - product_mentioned: boolean (true if specific product named in prompt)
        """
        logger.info(f"Entity extraction starting for user {user_id}")
        
        # Step 1: Check if user has any assets
        user_assets = self._get_user_assets(user_id)
        
        if not user_assets:
            logger.info(f"User {user_id} has 0 assets - skipping entity extraction")
            return {
                "entities": {},
                "user_assets": [],
                "has_assets": False,
                "product_mentioned": False
            }
        
        logger.info(f"User {user_id} has {len(user_assets)} assets - proceeding with extraction")
        
        # Step 2: Extract entities using GPT-4
        entities = self._extract_entities_via_llm(prompt)
        
        # Step 3: Determine if specific product was mentioned
        product_mentioned = bool(
            entities.get("product") and 
            entities["product"].lower() not in ["product", "item", "object"]
        )
        
        return {
            "entities": entities,
            "user_assets": user_assets,
            "has_assets": True,
            "product_mentioned": product_mentioned
        }
    
    def _get_user_assets(self, user_id: str) -> list[dict]:
        """
        Query database for user's reference assets.
        
        Returns:
            List of asset dicts with metadata
        """
        # Import here to avoid circular dependency
        from app.services.asset_search import get_user_asset_library
        
        db = SessionLocal()
        try:
            return get_user_asset_library(user_id, db)
        finally:
            db.close()
    
    def _extract_entities_via_llm(self, prompt: str) -> dict:
        """
        Use GPT-4 to extract entities from prompt.
        
        Extracts:
            - product: Specific product name (or null if not mentioned)
            - brand: Brand name (or null if not mentioned)
            - product_category: General category (e.g., "sneakers", "watch", "phone")
        
        Args:
            prompt: User's video generation prompt
            
        Returns:
            dict with extracted entities (fields may be null/generic)
        """
        system_prompt = build_entity_extraction_prompt()
        
        logger.info(f"🤖 Calling LLM for entity extraction...")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Temperature: {self.temperature}")
        logger.info(f"   User prompt: {prompt}")
        
        try:
            response = openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            logger.info(f"✅ LLM response received:")
            logger.info(f"   Raw content: {content}")
            
            entities = json.loads(content)
            
            logger.info(f"📦 Parsed entities: {json.dumps(entities, indent=2)}")
            
            # Validate structure
            return {
                "product": entities.get("product"),
                "brand": entities.get("brand"),
                "product_category": entities.get("product_category", "product")
            }
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {e}", exc_info=True)
            # Return empty/generic entities on failure
            return {
                "product": None,
                "brand": None,
                "product_category": "product"
            }


# Global service instance
entity_extraction_service = EntityExtractionService()

