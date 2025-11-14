from openai import OpenAI
from app.config import get_settings

settings = get_settings()

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
    
    @property
    def chat(self):
        return self.client.chat

openai_client = OpenAIClient()
