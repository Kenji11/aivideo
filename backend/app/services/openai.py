from openai import OpenAI
from app.config import get_settings
import httpx
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

class OpenAIClient:
    def __init__(self):
        # Initialize OpenAI client with compatible http_client
        # Fix for httpx version incompatibility
        try:
            # Try with explicit http_client to avoid proxies issue
            http_client = httpx.Client(timeout=60.0)
            self.client = OpenAI(
                api_key=settings.openai_api_key,
                http_client=http_client
            )
        except Exception as e:
            # Fallback: try without http_client
            try:
                self.client = OpenAI(api_key=settings.openai_api_key)
            except Exception:
                # Last resort: create a minimal client
                import openai
                self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    @property
    def chat(self):
        return self.client.chat

# Initialize with error handling - don't crash on import
try:
    openai_client = OpenAIClient()
    logger.debug("OpenAI client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
    # Create a placeholder that will fail on use, but allow import to succeed
    class FailedClient:
        def __getattr__(self, name):
            raise RuntimeError(f"OpenAI client initialization failed: {e}")
    openai_client = FailedClient()
