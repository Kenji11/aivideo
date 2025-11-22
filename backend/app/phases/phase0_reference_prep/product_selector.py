"""
Product Selector Service

Implements intelligent product and logo selection logic with prioritized ranking.
"""

import logging
import numpy as np
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.clip_embeddings import clip_service
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class ProductSelectorService:
    """Service for selecting best matching products and logos"""
    
    def __init__(self):
        self.clip_service = clip_service
    
    def select_best_product(
        self,
        user_assets: list[dict],
        entities: dict,
        prompt: str,
        product_mentioned: bool = False,
        brand_mentioned: bool = False
    ) -> dict:
        """
        Select the best matching product from user's asset library.
        
        Flow logic:
        - If product_mentioned = True OR brand_mentioned = True:
            - Find MOST SIMILAR product using similarity ranking
            - If similarity < 0.25, return None (empty)
            - If similarity >= 0.25, return the best match
        - If product_mentioned = False AND brand_mentioned = False:
            - Rank all products by similarity + recency + popularity
            - Fallback to most recently uploaded product if no good matches
        
        Args:
            user_assets: List of user's available assets with metadata
            entities: Extracted entities (product, brand, category, style_keywords)
            prompt: Original user prompt for semantic similarity
            product_mentioned: Whether a specific product was mentioned in the prompt
            brand_mentioned: Whether a specific brand was mentioned in the prompt
            
        Returns:
            dict with:
                - selected_product: asset dict or None
                - selection_rationale: string explaining selection
                - confidence: float 0.0-1.0
        """
        specific_entity_mentioned = product_mentioned or brand_mentioned
        logger.info(f"Selecting best product from asset library (product_mentioned={product_mentioned}, brand_mentioned={brand_mentioned})")
        
        # Filter to products only
        products = [
            asset for asset in user_assets 
            if asset.get("reference_asset_type") == "product"
        ]
        
        if not products:
            logger.info("No products found in user assets")
            return {
                "selected_product": None,
                "selection_rationale": "No products available in user's asset library",
                "confidence": 0.0
            }
        
        # Flow 2 & 3: Product or brand mentioned - use similarity-based selection with threshold
        if specific_entity_mentioned:
            entity_type = "product" if product_mentioned else "brand"
            logger.info(f"{entity_type.capitalize()} mentioned in prompt - using similarity-based selection with threshold")
            ranked_products = self.rank_products_by_similarity(products, prompt)
            
            if not ranked_products:
                logger.info("No products ranked - returning empty")
                return {
                    "selected_product": None,
                    "selection_rationale": f"{entity_type.capitalize()} mentioned but no suitable matches found",
                    "confidence": 0.0
                }
            
            best = ranked_products[0]
            similarity_score = best.get("_similarity", 0.0)
            
            # Similarity threshold: 0.25
            SIMILARITY_THRESHOLD = 0.25
            if similarity_score < SIMILARITY_THRESHOLD:
                logger.info(f"Best match similarity ({similarity_score:.2f}) below threshold ({SIMILARITY_THRESHOLD}) - returning empty")
                return {
                    "selected_product": None,
                    "selection_rationale": f"{entity_type.capitalize()} mentioned but best match similarity ({similarity_score:.2f}) is below threshold ({SIMILARITY_THRESHOLD})",
                    "confidence": similarity_score
                }
            
            logger.info(f"Best match found: {best['name']} (similarity: {similarity_score:.2f})")
            return {
                "selected_product": best,
                "selection_rationale": f"{entity_type.capitalize()} mentioned: selected most similar product '{best.get('name', best['primary_object'])}' (similarity: {similarity_score:.2f})",
                "confidence": similarity_score
            }
        
        # Flow 1: No product or brand mentioned - use fallback flow (rank all or most recent)
        logger.info("No product or brand mentioned - using fallback flow")
        ranked_products = self.rank_products_by_similarity(products, prompt)
        
        if ranked_products:
            best = ranked_products[0]
            logger.info(f"Best match from ranking: {best['name']}")
            return {
                "selected_product": best,
                "selection_rationale": f"Best overall match: asset '{best.get('name', best['primary_object'])}' has highest combined score (similarity + recency + popularity = {best.get('_rank_score', 0.0):.2f})",
                "confidence": 0.70
            }
        
        # Fallback: Most recent product
        most_recent = max(products, key=lambda x: x.get("created_at", ""))
        logger.info(f"Fallback to most recent: {most_recent['name']}")
        return {
            "selected_product": most_recent,
            "selection_rationale": f"Fallback: using most recently uploaded product '{most_recent.get('name', most_recent['primary_object'])}'",
            "confidence": 0.50
        }
    
    def rank_products_by_similarity(
        self,
        products: list[dict],
        prompt: str
    ) -> list[dict]:
        """
        Rank products by combined score: similarity + recency + popularity.
        
        Uses CLIP embeddings for semantic similarity.
        Weighted formula: 0.6 * similarity + 0.2 * recency_score + 0.2 * popularity_score
        
        Args:
            products: List of product assets with asset_id
            prompt: User prompt for semantic similarity
            
        Returns:
            Ranked list (highest score first) with _rank_score attached
        """
        if not products:
            return []
        
        try:
            logger.info(f"Ranking {len(products)} products by CLIP similarity to prompt: '{prompt[:50]}...'")
            
            # Generate prompt embedding using CLIP
            logger.info("Calling CLIP service to generate text embedding...")
            
            # Check if CLIP model is loaded
            if not self.clip_service._model_loaded:
                logger.warning("CLIP model not loaded yet, falling back to text-based similarity")
                raise RuntimeError("CLIP model not loaded")
            
            try:
                prompt_embedding = self.clip_service.generate_text_embedding(prompt)
                logger.info(f"CLIP embedding generated successfully, shape: {len(prompt_embedding)}")
                prompt_embedding = np.array(prompt_embedding)
                    
            except Exception as clip_error:
                logger.error(f"CLIP service failed: {clip_error}", exc_info=True)
                logger.warning("Falling back to text-based similarity matching")
                # Fallback to text matching for all products
                scored_products = []
                max_usage_count = max((p.get("usage_count", 0) for p in products), default=1)
                for product in products:
                    similarity_score = self._calculate_text_similarity(product, prompt)
                    recency_score = self._calculate_recency_score(product)
                    popularity_score = product.get("usage_count", 0) / max_usage_count if max_usage_count > 0 else 0.0
                    combined_score = 0.6 * similarity_score + 0.2 * recency_score + 0.2 * popularity_score
                    product["_rank_score"] = combined_score
                    product["_similarity"] = similarity_score
                    product["_recency"] = recency_score
                    product["_popularity"] = popularity_score
                    scored_products.append(product)
                return sorted(scored_products, key=lambda x: x["_rank_score"], reverse=True)
            
            # Get embeddings from database for all products
            db = SessionLocal()
            try:
                product_embeddings = self._fetch_product_embeddings(db, products)
            finally:
                db.close()
            
            # Calculate scores for each product
            scored_products = []
            max_usage_count = max((p.get("usage_count", 0) for p in products), default=1)
            
            for product in products:
                asset_id = product.get("asset_id")
                
                # Similarity score using CLIP embeddings (0.0-1.0)
                if asset_id in product_embeddings:
                    asset_embedding = np.array(product_embeddings[asset_id])
                    # Calculate cosine similarity (dot product for normalized vectors)
                    cosine_sim = np.dot(prompt_embedding, asset_embedding)
                    similarity_score = float(cosine_sim)  # Convert to 0.0-1.0 range
                    # Clamp to [0, 1]
                    similarity_score = max(0.0, min(1.0, similarity_score))
                else:
                    # Fallback to text matching if no embedding
                    logger.warning(f"No embedding found for asset {asset_id}, using text matching")
                    similarity_score = self._calculate_text_similarity(product, prompt)
                
                # Recency score (0.0 - 1.0, based on age)
                recency_score = self._calculate_recency_score(product)
                
                # Popularity score (0.0 - 1.0, normalized usage_count)
                popularity_score = product.get("usage_count", 0) / max_usage_count if max_usage_count > 0 else 0.0
                
                # Combined score: 60% similarity, 20% recency, 20% popularity
                combined_score = (
                    0.6 * similarity_score +
                    0.2 * recency_score +
                    0.2 * popularity_score
                )
                
                # Attach score and add to list
                product["_rank_score"] = combined_score
                product["_similarity"] = similarity_score
                product["_recency"] = recency_score
                product["_popularity"] = popularity_score
                scored_products.append(product)
            
            # Filter by minimum similarity threshold (0.3)
            SIMILARITY_THRESHOLD = 0.3
            filtered_products = [p for p in scored_products if p["_similarity"] >= SIMILARITY_THRESHOLD]
            
            if not filtered_products:
                logger.warning(f"No products met similarity threshold {SIMILARITY_THRESHOLD}, returning all products")
                filtered_products = scored_products
            
            # Sort by combined score (descending)
            ranked = sorted(filtered_products, key=lambda x: x["_rank_score"], reverse=True)
            
            logger.info(f"Ranked {len(ranked)} products by similarity (threshold: {SIMILARITY_THRESHOLD})")
            if ranked:
                top = ranked[0]
                logger.info(f"   Top product: {top.get('name')} (similarity: {top['_similarity']:.2f}, score: {top['_rank_score']:.2f})")
            
            return ranked
            
        except Exception as e:
            logger.error(f"Error ranking products: {e}", exc_info=True)
            # Fallback: sort by recency, set similarity to 0.0 since we couldn't calculate it
            logger.warning("Falling back to recency-based sorting")
            for product in products:
                product["_similarity"] = 0.0
            return sorted(products, key=lambda x: x.get("created_at", ""), reverse=True)
    
    def _fetch_product_embeddings(self, db: Session, products: list[dict]) -> dict:
        """
        Fetch CLIP embeddings from database for given products.
        
        Args:
            db: Database session
            products: List of product dicts with asset_id
            
        Returns:
            Dict mapping asset_id to embedding vector (list of floats)
        """
        from sqlalchemy import text
        
        asset_ids = [p.get("asset_id") for p in products if p.get("asset_id")]
        if not asset_ids:
            return {}
        
        embeddings = {}
        
        try:
            # Fetch embeddings for all products in one query
            placeholders = ','.join([f':id_{i}' for i in range(len(asset_ids))])
            sql = f"""
                SELECT id, embedding::text 
                FROM assets 
                WHERE id IN ({placeholders})
                  AND embedding IS NOT NULL
            """
            
            params = {f'id_{i}': asset_id for i, asset_id in enumerate(asset_ids)}
            result = db.execute(text(sql), params)
            
            for row in result:
                asset_id = row[0]
                embedding_str = row[1]
                # Parse embedding string: "[0.1,0.2,...]" -> list of floats
                embedding_list = [float(x.strip()) for x in embedding_str.strip('[]').split(',')]
                embeddings[asset_id] = embedding_list
            
            logger.info(f"Fetched embeddings for {len(embeddings)}/{len(asset_ids)} products")
            
        except Exception as e:
            logger.error(f"Error fetching product embeddings: {e}", exc_info=True)
        
        return embeddings
    
    def _calculate_text_similarity(self, product: dict, prompt: str) -> float:
        """
        Calculate text-based similarity between product metadata and prompt.
        
        This is a simplified version that uses keyword matching.
        In production with embeddings available, this would use CLIP cosine similarity.
        
        Args:
            product: Product asset dict
            prompt: User prompt
            
        Returns:
            Similarity score 0.0 - 1.0
        """
        prompt_lower = prompt.lower()
        score = 0.0
        
        # Check primary_object
        if product.get("primary_object"):
            if product["primary_object"].lower() in prompt_lower:
                score += 0.3
        
        # Check name
        if product.get("name"):
            if product["name"].lower() in prompt_lower:
                score += 0.2
        
        # Check style_tags
        style_tags = product.get("style_tags", [])
        if style_tags:
            matching_tags = sum(1 for tag in style_tags if tag.lower() in prompt_lower)
            score += min(0.5, matching_tags * 0.1)  # Up to 0.5 for matching tags
        
        return min(1.0, score)
    
    def _calculate_recency_score(self, product: dict) -> float:
        """
        Calculate recency score based on creation date.
        
        More recent = higher score.
        Score decays over 365 days to 0.0.
        
        Args:
            product: Product asset dict with created_at timestamp
            
        Returns:
            Recency score 0.0 - 1.0
        """
        try:
            created_at_str = product.get("created_at")
            if not created_at_str:
                return 0.5  # Default middle score if no timestamp
            
            # Parse ISO format timestamp
            created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            now = datetime.now(created_at.tzinfo)
            
            # Calculate age in days
            age_days = (now - created_at).days
            
            # Decay function: exponential decay over 365 days
            # Score = e^(-age_days / 365)
            # 0 days = 1.0, 180 days ≈ 0.6, 365 days ≈ 0.37
            import math
            score = math.exp(-age_days / 365.0)
            
            return max(0.0, min(1.0, score))
            
        except Exception as e:
            logger.warning(f"Error calculating recency score: {e}")
            return 0.5  # Default middle score on error
    
    def select_best_logo(
        self,
        user_assets: list[dict],
        entities: dict
    ) -> dict:
        """
        Select the best matching logo from user's asset library.
        
        Selection priority:
        1. If entities['brand'] specified → return logo matching brand
        2. If multiple logos → return most recent
        3. If no logos → return None
        
        Args:
            user_assets: List of user's available assets
            entities: Extracted entities (product, brand, category)
            
        Returns:
            dict with:
                - selected_logo: asset dict or None
                - selection_rationale: string explaining selection
                - confidence: float 0.0-1.0
        """
        logger.info("Selecting best logo from asset library")
        
        # Filter to logos only
        logos = [
            asset for asset in user_assets 
            if asset.get("reference_asset_type") == "logo" or asset.get("is_logo") is True
        ]
        
        if not logos:
            logger.info("No logos found in user assets")
            return {
                "selected_logo": None,
                "selection_rationale": "No logos available in user's asset library",
                "confidence": 0.0
            }
        
        # Priority 1: Brand match
        if entities.get("brand"):
            brand_name = entities["brand"].lower()
            for asset in logos:
                # Check in name or primary_object
                matches_name = brand_name in asset.get("name", "").lower()
                matches_object = brand_name in asset.get("primary_object", "").lower()
                
                if matches_name or matches_object:
                    logger.info(f"Brand logo match found: {asset['name']}")
                    return {
                        "selected_logo": asset,
                        "selection_rationale": f"Brand match: logo '{asset.get('name', asset['primary_object'])}' matches brand '{entities['brand']}'",
                        "confidence": 0.95
                    }
        
        # Priority 2: Most recent logo
        most_recent = max(logos, key=lambda x: x.get("created_at", ""))
        logger.info(f"Using most recent logo: {most_recent['name']}")
        return {
            "selected_logo": most_recent,
            "selection_rationale": f"Most recent: using logo '{most_recent.get('name', most_recent.get('primary_object', 'logo'))}'",
            "confidence": 0.80
        }


# Global service instance
product_selector_service = ProductSelectorService()

