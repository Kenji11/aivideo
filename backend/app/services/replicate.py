import replicate
from app.config import get_settings
import time
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

class ReplicateClient:
    def __init__(self):
        self.client = replicate.Client(api_token=settings.replicate_api_token)
    
    def run(self, model: str, input: dict, timeout: int = 300):
        """
        Run a model on Replicate with timeout protection.
        
        Args:
            model: Model identifier (e.g., "meta/musicgen" or "model:version_hash")
            input: Input parameters
            timeout: Maximum time to wait in seconds (default 5 minutes)
            
        Returns:
            Model output (URL or list)
        """
        start_time = time.time()
        
        try:
            # Check if model is in format "model:version_hash" (version hash format)
            if ':' in model:
                # Extract version hash (part after colon)
                version_hash = model.split(':', 1)[1]
                # Use version parameter directly via replicate client
                prediction = self.client.predictions.create(
                    version=version_hash,
                    input=input
                )
                
                # Poll for completion
                while prediction.status not in ["succeeded", "failed", "canceled"]:
                    if time.time() - start_time > timeout:
                        raise TimeoutError(f"Replicate prediction timed out after {timeout} seconds")
                    time.sleep(1)
                    prediction.reload()
                
                if prediction.status == "failed":
                    error_msg = getattr(prediction, 'error', 'Unknown error')
                    raise Exception(f"Replicate prediction failed: {error_msg}")
                
                if prediction.status == "canceled":
                    raise Exception("Replicate prediction was canceled")
                
                output = prediction.output
            else:
                # Use the client's run() method for model names (handles polling automatically)
                output = self.client.run(model, input=input)
            
            # Handle output format (can be string URL, iterator, or list)
            if isinstance(output, str):
                return output
            elif hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
                # Convert iterator/list to list and get first item
                output_list = list(output)
                return output_list[0] if output_list else None
            elif isinstance(output, dict):
                # Try common keys for output
                return output.get('output') or output.get('url') or output.get('audio')
            else:
                return str(output) if output else None
                
        except Exception as e:
            # If run() fails, provide detailed error
            error_msg = str(e)
            if "version" in error_msg.lower() or "does not exist" in error_msg.lower():
                raise Exception(
                    f"Replicate model '{model}' not found or invalid. "
                    f"Error: {error_msg}. "
                    f"Check if the model name is correct or if you need a version hash."
                )
            raise Exception(f"Replicate API error: {error_msg}")

# Initialize with error handling - don't crash on import
try:
    replicate_client = ReplicateClient()
    logger.debug("Replicate client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Replicate client: {e}", exc_info=True)
    # Create a placeholder that will fail on use, but allow import to succeed
    class FailedClient:
        def __getattr__(self, name):
            raise RuntimeError(f"Replicate client initialization failed: {e}")
        def run(self, *args, **kwargs):
            raise RuntimeError(f"Replicate client initialization failed: {e}")
    replicate_client = FailedClient()
