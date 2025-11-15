"""
OpenRouter API client for LLM access
OpenRouter provides access to multiple LLMs (GPT-4, Claude, etc.) through a single API
"""
import requests
from app.config import get_settings
from typing import Dict, Optional

settings = get_settings()

class OpenRouterClient:
    """Client for OpenRouter API"""
    
    def __init__(self):
        # Get API key from settings (optional, won't fail if not set)
        self.api_key = getattr(settings, 'openrouter_api_key', None) or None
        if self.api_key == "":
            self.api_key = None
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = "openai/gpt-4-turbo"  # Can use any model via OpenRouter
    
    def chat_completion(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict] = None
    ) -> Dict:
        """
        Create a chat completion using OpenRouter.
        
        Args:
            messages: List of message dicts (same format as OpenAI)
            model: Model identifier (e.g., "openai/gpt-4-turbo", "anthropic/claude-3-opus")
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., {"type": "json_object"})
            
        Returns:
            Response dict with 'choices' containing completion (OpenAI-compatible format)
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")
        
        model = model or self.default_model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional: for analytics
            "X-Title": "VideoAI Studio"  # Optional: for analytics
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if response_format:
            payload["response_format"] = response_format
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        return response.json()
    
    def get_available_models(self) -> list:
        """Get list of available models from OpenRouter"""
        if not self.api_key:
            return []
        
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/models",
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception:
            return []

openrouter_client = OpenRouterClient()

