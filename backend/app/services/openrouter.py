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
        # Support both OPENROUTER_API_KEY and OPENROUTER_1_KEY
        self.api_key = getattr(settings, 'openrouter_api_key', None) or None
        if not self.api_key or self.api_key == "":
            # Try alternative name
            self.api_key = getattr(settings, 'openrouter_1_key', None) or None
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
    
    def generate_image(
        self,
        prompt: str,
        model: str = "google/gemini-2.5-flash-image",
        size: str = "1280x720",
        n: int = 1,
        quality: str = "standard"
    ) -> Dict:
        """
        Generate an image using OpenRouter image generation models.
        
        OpenRouter image generation models use the chat/completions endpoint
        with special formatting. The model returns image data in the response.
        
        Args:
            prompt: Text prompt describing the image to generate
            model: Model identifier (e.g., "google/gemini-2.5-flash-image")
            size: Image size (e.g., "1280x720", "1024x1024") - may be ignored by model
            n: Number of images to generate (default: 1) - may be ignored by model
            quality: Image quality ("standard" or "hd") - may be ignored by model
            
        Returns:
            Response dict with image URLs or base64 data
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",
            "X-Title": "VideoAI Studio"
        }
        
        # OpenRouter image generation models use chat/completions endpoint
        # Format: Send prompt as a message, model returns image URL or base64
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1000  # Some models need this
        }
        
        # Try chat/completions endpoint first (most OpenRouter image models use this)
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120  # Image generation can take longer
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract image URL from response
            # Format varies by model - check choices[0].message.content
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0].get('message', {}).get('content', '')
                # If content is a URL, return it in DALL-E format
                if content.startswith('http'):
                    return {
                        "data": [{"url": content}]
                    }
                # If content is base64, we'd need to handle that differently
                # For now, return the raw response
                return result
            
            return result
            
        except requests.exceptions.HTTPError as e:
            # If chat/completions fails, try /images/generations endpoint (OpenAI DALL-E format)
            try:
                payload_img = {
                    "model": model,
                    "prompt": prompt,
                    "size": size,
                    "n": n,
                    "quality": quality
                }
                response = requests.post(
                    f"{self.base_url}/images/generations",
                    headers=headers,
                    json=payload_img,
                    timeout=120
                )
                response.raise_for_status()
                return response.json()
            except Exception:
                # Re-raise original error
                raise e
    
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

