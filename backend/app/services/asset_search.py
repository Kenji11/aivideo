"""
Asset Search Service for Semantic and Visual Similarity Search

Provides vector similarity search using CLIP embeddings stored in pgvector.
Uses raw SQL queries for pgvector operations (cosine distance).
"""
import logging
from typing import List, Optional, Dict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.common.models import Asset, AssetSource, ReferenceAssetType
from app.services.clip_embeddings import clip_service

logger = logging.getLogger(__name__)


def get_user_asset_library(user_id: str, db: Session) -> list[dict]:
    """
    Get all reference assets for a user with relevant metadata.
    
    Used by Phase 0 to fetch user's complete asset library for matching.
    
    Args:
        user_id: User ID
        db: Database session
        
    Returns:
        List of asset dicts with metadata needed for matching:
            - asset_id, asset_type, reference_asset_type
            - name, primary_object, colors, style_tags
            - recommended_shot_types, usage_contexts
            - thumbnail_url, created_at, usage_count
    """
    try:
        assets = db.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.source == AssetSource.USER_UPLOAD.name  # User-uploaded assets only
        ).all()
        
        # Convert to dicts with relevant metadata
        asset_list = []
        for asset in assets:
            asset_dict = {
                "asset_id": asset.id,
                "asset_type": asset.asset_type.value if asset.asset_type else None,
                "reference_asset_type": asset.reference_asset_type,
                "name": asset.name,
                "primary_object": asset.primary_object,
                "colors": asset.colors or [],
                "style_tags": asset.style_tags or [],
                "recommended_shot_types": asset.recommended_shot_types or [],
                "usage_contexts": asset.usage_contexts or [],
                "thumbnail_url": asset.thumbnail_url,
                "created_at": asset.created_at.isoformat() if asset.created_at else None,
                "usage_count": asset.usage_count or 0,
                "is_logo": asset.is_logo or False
            }
            asset_list.append(asset_dict)
        
        logger.info(f"Retrieved {len(asset_list)} assets for user {user_id}")
        return asset_list
        
    except Exception as e:
        logger.error(f"Error retrieving user asset library: {str(e)}", exc_info=True)
        raise


def cosine_distance(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine distance between two vectors.
    
    Cosine distance = 1 - cosine_similarity
    For normalized vectors, cosine_similarity = dot product
    
    Args:
        vec1: First vector (normalized)
        vec2: Second vector (normalized)
        
    Returns:
        Cosine distance (0.0 = identical, 2.0 = opposite)
    """
    vec1_array = np.array(vec1)
    vec2_array = np.array(vec2)
    
    # Cosine similarity for normalized vectors is just dot product
    cosine_similarity = np.dot(vec1_array, vec2_array)
    
    # Cosine distance = 1 - similarity
    return 1.0 - cosine_similarity


class AssetSearchService:
    """Service for semantic and visual similarity search of assets"""
    
    def __init__(self):
        self.clip_service = clip_service
    
    def search_assets_by_text(
        self,
        db: Session,
        user_id: str,
        query: str,
        asset_type: Optional[ReferenceAssetType] = None,
        limit: int = 10
    ) -> List[Asset]:
        """
        Search assets by text query using semantic similarity.
        
        Args:
            db: Database session
            user_id: User ID to filter assets
            query: Text query (e.g., "red Nike sneaker")
            asset_type: Optional filter by asset type
            limit: Maximum number of results
            
        Returns:
            List of Asset objects with similarity_score attribute attached
        """
        try:
            # Generate query embedding
            query_embedding = self.clip_service.generate_text_embedding(query)
            embedding_str = '[' + ','.join(str(f) for f in query_embedding) + ']'
            
            # Build SQL query with pgvector cosine distance operator (<=>)
            # Cosine distance: embedding <=> query_embedding
            # Lower distance = more similar
            
            sql = """
                SELECT 
                    id,
                    user_id,
                    s3_key,
                    s3_url,
                    asset_type,
                    source,
                    file_name,
                    file_size_bytes,
                    mime_type,
                    asset_metadata,
                    name,
                    description,
                    reference_asset_type,
                    thumbnail_url,
                    width,
                    height,
                    has_transparency,
                    analysis,
                    primary_object,
                    colors,
                    dominant_colors_rgb,
                    style_tags,
                    recommended_shot_types,
                    usage_contexts,
                    is_logo,
                    logo_position_preference,
                    embedding,
                    updated_at,
                    usage_count,
                    created_at,
                    1 - (embedding <=> CAST(:query_embedding AS vector)) AS similarity_score
                FROM assets
                WHERE user_id = :user_id
                  AND source = :source
                  AND embedding IS NOT NULL
                  AND (1 - (embedding <=> CAST(:query_embedding AS vector))) >= 0.25
            """
            
            # Use .name for raw SQL - PostgreSQL enum expects label name (USER_UPLOAD), not value (user_upload)
            params = {
                "user_id": user_id,
                "source": AssetSource.USER_UPLOAD.name,
                "query_embedding": embedding_str
            }
            
            # Add asset type filter if provided
            if asset_type:
                sql += " AND reference_asset_type = :asset_type"
                params["asset_type"] = asset_type.value
            
            # Order by cosine distance (ascending = most similar first)
            sql += " ORDER BY embedding <=> CAST(:query_embedding AS vector) LIMIT :limit"
            params["limit"] = limit
            
            # Execute query
            result = db.execute(text(sql), params)
            
            # Convert rows to Asset objects
            assets = []
            for row in result:
                asset = db.query(Asset).filter(Asset.id == row.id).first()
                if asset:
                    # Attach similarity score as attribute
                    asset.similarity_score = float(row.similarity_score)
                    assets.append(asset)
            
            logger.info(f"Found {len(assets)} assets for query: '{query}' (min similarity: 0.25)")
            return assets
            
        except Exception as e:
            logger.error(f"Error searching assets by text: {str(e)}", exc_info=True)
            raise
    
    def find_similar_assets(
        self,
        db: Session,
        reference_asset_id: str,
        limit: int = 10,
        exclude_self: bool = True
    ) -> List[Asset]:
        """
        Find visually similar assets to a reference asset.
        
        Args:
            db: Database session
            reference_asset_id: ID of the reference asset
            limit: Maximum number of results
            exclude_self: Whether to exclude the reference asset from results
            
        Returns:
            List of Asset objects with similarity_score attribute attached
        """
        try:
            # Fetch reference asset
            reference_asset = db.query(Asset).filter(Asset.id == reference_asset_id).first()
            if not reference_asset:
                raise ValueError(f"Asset {reference_asset_id} not found")
            
            # Get embedding as string for SQL
            # Fetch embedding from database using raw SQL (pgvector type)
            # pgvector returns embeddings as array format: [0.1,0.2,...]
            # Note: We check embedding via SQL since it's not a SQLAlchemy column attribute
            embedding_result = db.execute(
                text("SELECT embedding::text FROM assets WHERE id = :asset_id"),
                {"asset_id": reference_asset_id}
            ).first()
            
            if not embedding_result or not embedding_result[0]:
                logger.warning(f"Asset {reference_asset_id} has no embedding")
                return []
            
            # pgvector returns as array string, use directly
            reference_embedding_str = embedding_result[0]
            
            # Build SQL query
            # Filter by minimum 70% similarity (0.7) for image-to-image comparison
            # Image-to-image similarity is more reliable than text-to-image, so we can use a higher threshold
            sql = """
                SELECT 
                    id,
                    1 - (embedding <=> CAST(:reference_embedding AS vector)) AS similarity_score
                FROM assets
                WHERE user_id = :user_id
                  AND source = :source
                  AND embedding IS NOT NULL
                  AND (1 - (embedding <=> CAST(:reference_embedding AS vector))) >= 0.7
            """
            
            # Use .name for raw SQL - PostgreSQL enum expects label name (USER_UPLOAD), not value (user_upload)
            params = {
                "user_id": reference_asset.user_id,
                "source": AssetSource.USER_UPLOAD.name,
                "reference_embedding": reference_embedding_str
            }
            
            if exclude_self:
                sql += " AND id != :exclude_id"
                params["exclude_id"] = reference_asset_id
            
            sql += " ORDER BY embedding <=> CAST(:reference_embedding AS vector) LIMIT :limit"
            params["limit"] = limit
            
            # Execute query
            result = db.execute(text(sql), params)
            
            # Convert to Asset objects
            assets = []
            for row in result:
                asset = db.query(Asset).filter(Asset.id == row.id).first()
                if asset:
                    asset.similarity_score = float(row.similarity_score)
                    assets.append(asset)
            
            logger.info(f"Found {len(assets)} similar assets for asset {reference_asset_id}")
            return assets
            
        except Exception as e:
            logger.error(f"Error finding similar assets: {str(e)}", exc_info=True)
            raise
    
    def find_assets_for_beat(
        self,
        db: Session,
        user_id: str,
        beat: Dict,
        product_hint: Optional[str] = None,
        limit: int = 3
    ) -> Dict[str, List[Asset]]:
        """
        Find appropriate assets for a specific beat.
        
        Args:
            db: Database session
            user_id: User ID
            beat: Beat dictionary with shot_type, action, mood, etc.
            product_hint: Optional product name hint
            limit: Maximum results per asset type
            
        Returns:
            Dictionary with keys: 'product_refs', 'logo_refs', 'environment_refs'
        """
        try:
            # Compose search query from beat characteristics
            query_parts = []
            if product_hint:
                query_parts.append(product_hint)
            if beat.get('shot_type'):
                query_parts.append(beat['shot_type'])
            if beat.get('action'):
                query_parts.append(beat['action'])
            if beat.get('mood'):
                query_parts.append(beat['mood'])
            
            if not query_parts:
                # Fallback to generic query
                query = "product asset"
            else:
                query = " ".join(query_parts)
            
            # Search for assets
            all_results = self.search_assets_by_text(
                db=db,
                user_id=user_id,
                query=query,
                limit=limit * 3  # Get more results to filter
            )
            
            # Filter by recommended_shot_types if beat has shot_type
            shot_type = beat.get('shot_type')
            if shot_type:
                filtered_results = [
                    asset for asset in all_results
                    if asset.recommended_shot_types and shot_type in asset.recommended_shot_types
                ]
                # If filtering removed all results, use original results
                if filtered_results:
                    all_results = filtered_results[:limit * 3]
            
            # Separate by asset type
            product_refs = []
            logo_refs = []
            environment_refs = []
            
            for asset in all_results[:limit * 3]:
                if asset.reference_asset_type == ReferenceAssetType.PRODUCT.value:
                    if len(product_refs) < limit:
                        product_refs.append(asset)
                elif asset.reference_asset_type == ReferenceAssetType.LOGO.value:
                    if len(logo_refs) < limit:
                        logo_refs.append(asset)
                elif asset.reference_asset_type == ReferenceAssetType.ENVIRONMENT.value:
                    if len(environment_refs) < limit:
                        environment_refs.append(asset)
            
            return {
                'product_refs': product_refs,
                'logo_refs': logo_refs,
                'environment_refs': environment_refs
            }
            
        except Exception as e:
            logger.error(f"Error finding assets for beat: {str(e)}", exc_info=True)
            raise
    
    def check_duplicate_asset(
        self,
        db: Session,
        user_id: str,
        new_image_embedding: List[float],
        similarity_threshold: float = 0.95
    ) -> List[Asset]:
        """
        Check for duplicate assets based on visual similarity.
        
        Args:
            db: Database session
            user_id: User ID
            new_image_embedding: Embedding of the new image to check
            similarity_threshold: Minimum similarity to consider duplicate (0.95 = very similar)
            
        Returns:
            List of potentially duplicate assets with similarity_score attribute
        """
        try:
            embedding_str = '[' + ','.join(str(f) for f in new_image_embedding) + ']'
            
            # Query for similar embeddings
            sql = """
                SELECT 
                    id,
                    1 - (embedding <=> CAST(:new_embedding AS vector)) AS similarity_score
                FROM assets
                WHERE user_id = :user_id
                  AND source = :source
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:new_embedding AS vector)
                LIMIT 5
            """
            
            # Use .name for raw SQL - PostgreSQL enum expects label name (USER_UPLOAD), not value (user_upload)
            params = {
                "user_id": user_id,
                "source": AssetSource.USER_UPLOAD.name,
                "new_embedding": embedding_str
            }
            
            result = db.execute(text(sql), params)
            
            # Filter by threshold and convert to Asset objects
            duplicates = []
            for row in result:
                similarity = float(row.similarity_score)
                if similarity >= similarity_threshold:
                    asset = db.query(Asset).filter(Asset.id == row.id).first()
                    if asset:
                        asset.similarity_score = similarity
                        duplicates.append(asset)
            
            logger.info(f"Found {len(duplicates)} potential duplicates for user {user_id}")
            return duplicates
            
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}", exc_info=True)
            raise
    
    def recommend_style_consistent_assets(
        self,
        db: Session,
        user_id: str,
        selected_asset_ids: List[str],
        limit: int = 10
    ) -> List[Asset]:
        """
        Recommend assets that match the style of already-selected assets.
        
        Args:
            db: Database session
            user_id: User ID
            selected_asset_ids: List of asset IDs that user has selected
            limit: Maximum number of recommendations
            
        Returns:
            List of recommended Asset objects with similarity_score attribute
        """
        try:
            if not selected_asset_ids:
                return []
            
            # Fetch selected assets
            selected_assets = db.query(Asset).filter(
                Asset.id.in_(selected_asset_ids),
                Asset.user_id == user_id
            ).all()
            
            if not selected_assets:
                return []
            
            # Extract embeddings
            embeddings = []
            for asset in selected_assets:
                if asset.embedding:
                    # Get embedding as string from database
                    embedding_result = db.execute(
                        text("SELECT embedding::text FROM assets WHERE id = :asset_id"),
                        {"asset_id": asset.id}
                    ).first()
                    if embedding_result and embedding_result[0]:
                        # Parse embedding string to list
                        # pgvector returns as array format: [0.1,0.2,...]
                        embedding_str = embedding_result[0]
                        # Remove brackets and split, handle whitespace
                        embedding_list = [float(x.strip()) for x in embedding_str.strip('[]').split(',')]
                        embeddings.append(embedding_list)
            
            if not embeddings:
                return []
            
            # Calculate centroid (average embedding)
            embeddings_array = np.array(embeddings)
            centroid = np.mean(embeddings_array, axis=0)
            # Normalize centroid
            centroid = centroid / np.linalg.norm(centroid)
            centroid_str = '[' + ','.join(str(f) for f in centroid.tolist()) + ']'
            
            # Query for assets near centroid
            # Build NOT IN clause dynamically for proper SQL parameterization
            exclude_placeholders = ','.join([f':exclude_id_{i}' for i in range(len(selected_asset_ids))])
            sql = f"""
                SELECT 
                    id,
                    1 - (embedding <=> CAST(:centroid AS vector)) AS similarity_score
                FROM assets
                WHERE user_id = :user_id
                  AND source = :source
                  AND embedding IS NOT NULL
                  AND id NOT IN ({exclude_placeholders})
                ORDER BY embedding <=> CAST(:centroid AS vector)
                LIMIT :limit
            """
            
            # Use .name for raw SQL - PostgreSQL enum expects label name (USER_UPLOAD), not value (user_upload)
            params = {
                "user_id": user_id,
                "source": AssetSource.USER_UPLOAD.name,
                "centroid": centroid_str,
                "limit": limit
            }
            # Add exclude IDs as separate parameters
            for i, asset_id in enumerate(selected_asset_ids):
                params[f"exclude_id_{i}"] = asset_id
            
            result = db.execute(text(sql), params)
            
            # Convert to Asset objects
            recommendations = []
            for row in result:
                asset = db.query(Asset).filter(Asset.id == row.id).first()
                if asset:
                    asset.similarity_score = float(row.similarity_score)
                    recommendations.append(asset)
            
            logger.info(f"Found {len(recommendations)} style-consistent recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"Error recommending style-consistent assets: {str(e)}", exc_info=True)
            raise


# Singleton instance
asset_search_service = AssetSearchService()

