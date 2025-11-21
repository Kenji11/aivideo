"""
CLIP Embedding Service for Reference Asset Analysis

Generates semantic embeddings for images and text using CLIP (ViT-B/32).
Uses Docker volume caching for model persistence across container restarts.
"""
import os
import time
import logging
from functools import lru_cache
from typing import List
import torch
import open_clip
from PIL import Image
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Expected embedding dimensions for ViT-B/32
EMBEDDING_DIM = 512


class CLIPEmbeddingService:
    """Service for generating CLIP embeddings for images and text"""
    
    def __init__(self):
        self.model = None
        self.preprocess = None
        self.device = None
        self._model_loaded = False
        self._load_model()
    
    def _load_model(self):
        """Load CLIP model with volume caching"""
        if self._model_loaded:
            return
        
        start_time = time.time()
        model_name = settings.clip_model  # Default: "ViT-B/32"
        cache_dir = settings.clip_model_cache  # Default: "/mnt/models"
        
        # Ensure cache directory exists
        os.makedirs(cache_dir, exist_ok=True)
        
        # Detect device (GPU if available, else CPU)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading CLIP model '{model_name}' on device: {self.device}")
        logger.info(f"Model cache directory: {cache_dir}")
        
        try:
            # Load model with caching using open_clip
            # open_clip.create_model() will download to cache_dir on first run, load from cache on subsequent runs
            # ViT-B/32 in open_clip is 'ViT-B-32'
            open_clip_model_name = 'ViT-B-32' if model_name == 'ViT-B/32' else model_name
            
            # Set cache directory via environment variable (open_clip respects HF_HOME)
            os.environ['HF_HOME'] = cache_dir
            os.environ['TORCH_HOME'] = cache_dir
            
            self.model, self.preprocess, _ = open_clip.create_model_and_transforms(
                open_clip_model_name,
                pretrained='openai',  # Use OpenAI pretrained weights
                device=self.device
            )
            # Move model to device explicitly
            self.model = self.model.to(self.device)
            self.model.eval()  # Set to evaluation mode
            
            load_time = time.time() - start_time
            self._model_loaded = True
            
            # Check if this was a cold start (download) or warm start (cached)
            # open_clip stores models in HF_HOME or TORCH_HOME
            model_cache_path = os.path.join(cache_dir, 'checkpoints')
            if os.path.exists(model_cache_path) and os.listdir(model_cache_path):
                logger.info(
                    f"✓ CLIP model loaded successfully (warm start, cached) "
                    f"in {load_time:.2f}s"
                )
            else:
                logger.info(
                    f"✓ CLIP model loaded successfully (cold start, downloaded) "
                    f"in {load_time:.2f}s"
                )
                
        except Exception as e:
            logger.error(f"Failed to load CLIP model: {str(e)}", exc_info=True)
            raise RuntimeError(f"CLIP model loading failed: {str(e)}")
    
    def generate_image_embedding(self, image: Image.Image) -> List[float]:
        """
        Generate CLIP embedding for an image
        
        Args:
            image: PIL Image (from memory, not file path)
            
        Returns:
            List of 512 floats (normalized embedding vector)
            
        Raises:
            ValueError: If image is corrupted or invalid
            RuntimeError: If model is not loaded
        """
        if not self._model_loaded or self.model is None:
            raise RuntimeError("CLIP model not loaded. Call _load_model() first.")
        
        try:
            # Preprocess image for CLIP
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # Generate embedding using open_clip
            with torch.no_grad():
                embedding = self.model.encode_image(image_input)
                # Normalize embedding (L2 norm)
                embedding = embedding / embedding.norm(dim=-1, keepdim=True)
            
            # Convert to CPU and return as list
            embedding_list = embedding.cpu().numpy()[0].tolist()
            
            # Verify dimensions
            if len(embedding_list) != EMBEDDING_DIM:
                raise ValueError(
                    f"Expected embedding dimension {EMBEDDING_DIM}, "
                    f"got {len(embedding_list)}"
                )
            
            return embedding_list
            
        except Exception as e:
            if "corrupted" in str(e).lower() or "invalid" in str(e).lower():
                raise ValueError(f"Corrupted or invalid image: {str(e)}")
            logger.error(f"Error generating image embedding: {str(e)}", exc_info=True)
            raise
    
    def generate_text_embedding(self, text: str) -> List[float]:
        """
        Generate CLIP embedding for text
        
        Args:
            text: Text string to embed
            
        Returns:
            List of 512 floats (normalized embedding vector)
            
        Raises:
            RuntimeError: If model is not loaded
        """
        if not self._model_loaded or self.model is None:
            raise RuntimeError("CLIP model not loaded. Call _load_model() first.")
        
        try:
            # Tokenize text using open_clip
            text_input = open_clip.tokenize([text]).to(self.device)
            
            # Generate embedding
            with torch.no_grad():
                embedding = self.model.encode_text(text_input)
                # Normalize embedding (L2 norm)
                embedding = embedding / embedding.norm(dim=-1, keepdim=True)
            
            # Convert to CPU and return as list
            embedding_list = embedding.cpu().numpy()[0].tolist()
            
            # Verify dimensions
            if len(embedding_list) != EMBEDDING_DIM:
                raise ValueError(
                    f"Expected embedding dimension {EMBEDDING_DIM}, "
                    f"got {len(embedding_list)}"
                )
            
            return embedding_list
            
        except Exception as e:
            logger.error(f"Error generating text embedding: {str(e)}", exc_info=True)
            raise


# Singleton instance with lazy loading
# Use @lru_cache to ensure only one instance is created
@lru_cache(maxsize=1)
def get_clip_service() -> CLIPEmbeddingService:
    """
    Get singleton CLIP embedding service instance
    
    Returns:
        CLIPEmbeddingService instance (cached)
    """
    return CLIPEmbeddingService()


# Initialize service with error handling - don't crash on import
try:
    clip_service = get_clip_service()
    logger.debug("CLIP embedding service initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize CLIP embedding service: {e}", exc_info=True)
    # Create a placeholder that will fail on use, but allow import to succeed
    class FailedCLIPService:
        def generate_image_embedding(self, image: Image.Image) -> List[float]:
            raise RuntimeError(f"CLIP service initialization failed: {e}")
        def generate_text_embedding(self, text: str) -> List[float]:
            raise RuntimeError(f"CLIP service initialization failed: {e}")
    clip_service = FailedCLIPService()

