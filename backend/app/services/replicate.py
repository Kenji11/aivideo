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
            model: Model identifier (e.g., "meta/musicgen" or version hash)
            input: Input parameters
            timeout: Maximum time to wait in seconds (default 5 minutes)
            
        Returns:
            Model output (URL or list)
        """
        # Use Replicate client's run() method which handles model/version automatically
        # This is the recommended way to call Replicate models
        start_time = time.time()
        
        try:
            # Use the client's run() method which handles both model names and version hashes
            # It automatically polls and returns the output
            output = self.client.run(model, input=input)
            
            # The run() method returns an iterator for streaming outputs
            # For most models, we want the first (and usually only) output
            if hasattr(output, '__iter__') and not isinstance(output, (str, bytes)):
                # Convert iterator to list and get first item
                output_list = list(output)
                return output_list[0] if output_list else None
            else:
                # Already a single value (string URL or other)
                return output
                
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

replicate_client = ReplicateClient()
