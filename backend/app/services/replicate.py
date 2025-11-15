import replicate
from app.config import get_settings
import time

settings = get_settings()

class ReplicateClient:
    def __init__(self):
        self.client = replicate.Client(api_token=settings.replicate_api_token)
    
    def run(self, model: str, input: dict, timeout: int = 300):
        """
        Run a model on Replicate with timeout protection.
        
        Args:
            model: Model identifier
            input: Input parameters
            timeout: Maximum time to wait in seconds (default 5 minutes)
            
        Returns:
            Model output (URL or list)
        """
        # Use run() which automatically polls, but add timeout protection
        start_time = time.time()
        
        # Create prediction - use model parameter for model names like "owner/model"
        # The Replicate API accepts either model name or version hash
        try:
            # Try with model parameter first (for model names)
            prediction = self.client.predictions.create(
                model=model,
                input=input
            )
        except Exception:
            # Fallback to version parameter (for version hashes)
            prediction = self.client.predictions.create(
                version=model,
                input=input
            )
        
        # Poll with timeout
        while prediction.status not in ["succeeded", "failed", "canceled"]:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Replicate prediction timed out after {timeout} seconds")
            
            time.sleep(1)  # Poll every second
            prediction.reload()
        
        if prediction.status == "failed":
            error_msg = getattr(prediction, 'error', 'Unknown error')
            raise Exception(f"Replicate prediction failed: {error_msg}")
        
        if prediction.status == "canceled":
            raise Exception("Replicate prediction was canceled")
        
        # Return output
        return prediction.output

replicate_client = ReplicateClient()
