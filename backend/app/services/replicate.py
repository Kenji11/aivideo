import replicate
from app.config import get_settings

settings = get_settings()

class ReplicateClient:
    def __init__(self):
        self.client = replicate.Client(api_token=settings.replicate_api_token)
    
    def run(self, model: str, input: dict):
        """Run a model on Replicate"""
        return self.client.run(model, input=input)

replicate_client = ReplicateClient()
