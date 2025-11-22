"""
Asset Analysis Service using GPT-4o Vision

Analyzes reference assets with a single comprehensive GPT-4o API call
that returns all analysis fields in JSON format.
"""
import json
import time
import logging
from typing import Dict, Optional
from app.services.openai import openai_client

logger = logging.getLogger(__name__)

# Cost tracking (GPT-4o vision pricing as of 2024)
# Input: $2.50 per 1M tokens, Output: $10.00 per 1M tokens
COST_PER_INPUT_TOKEN = 2.50 / 1_000_000
COST_PER_OUTPUT_TOKEN = 10.00 / 1_000_000


class AssetAnalysisService:
    """Service for analyzing reference assets using GPT-4o Vision"""
    
    def __init__(self):
        self.max_retries = 3
        self.retry_delay_base = 1.0  # Base delay in seconds for exponential backoff
    
    def analyze_reference_asset(
        self,
        image_url: str,
        user_provided_name: Optional[str] = None,
        user_provided_description: Optional[str] = None
    ) -> Dict:
        """
        Analyze reference asset using GPT-4o Vision (single comprehensive call)
        
        Args:
            image_url: Presigned S3 URL for the image
            user_provided_name: Optional user-provided name for context
            user_provided_description: Optional user-provided description for context
            
        Returns:
            Dictionary with all analysis fields:
            {
                "asset_type": "product|logo|person|environment|texture|prop",
                "primary_object": "detailed description",
                "colors": ["color1", "color2", ...],
                "dominant_colors_rgb": [[R,G,B], [R,G,B], ...],
                "style_tags": ["tag1", "tag2", ...],
                "recommended_shot_types": ["shot_type1", ...],
                "usage_contexts": ["context1", ...],
                "is_logo": bool,
                "logo_position_preference": "bottom-right" | None,
                "confidence": 0.0-1.0
            }
            
        Raises:
            RuntimeError: If analysis fails after retries
            ValueError: If response is invalid
        """
        system_prompt = """You are an expert visual analyst for advertising and video production. 
Analyze the provided image and extract detailed information for video generation use cases.

Focus on:
- What is the PRIMARY object/subject?
- What TYPE of asset is this? (product, logo, person, environment, texture, prop)
- What are the dominant COLORS? (both color names and RGB values)
- What STYLE/AESTHETIC does it convey?
- What SHOT TYPES would work well with this asset?
- In what CONTEXTS would this be used in video?
- Is this a LOGO? (high contrast, simple shapes, brand identifier, often transparent background)
- If it's a logo, what position preference? (bottom-right, top-left, center, etc.)

Return a structured JSON response with all fields."""

        user_prompt = f"""Analyze this image for video production.

User-provided context:
- Name: {user_provided_name or 'Not provided'}
- Description: {user_provided_description or 'Not provided'}

Return JSON with this EXACT structure:
{{
    "asset_type": "product|logo|person|environment|texture|prop",
    "primary_object": "detailed description of main subject",
    "colors": ["color1", "color2", "color3"],
    "dominant_colors_rgb": [[R,G,B], [R,G,B], [R,G,B]],
    "style_tags": ["tag1", "tag2", "tag3"],
    "recommended_shot_types": ["shot_type1", "shot_type2"],
    "usage_contexts": ["context1", "context2"],
    "is_logo": true/false,
    "logo_position_preference": "bottom-right" or null,
    "confidence": 0.0-1.0
}}

Shot types vocabulary: close_up, medium, wide, extreme_close_up, hero_shot, detail_showcase, 
lifestyle_context, action_shot, overhead, dramatic_angle, product_in_motion

For dominant_colors_rgb, extract the top 5 most prominent colors as RGB arrays (0-255 range).
If is_logo is true, provide logo_position_preference (e.g., "bottom-right", "top-left", "center").
Be specific and detailed in descriptions."""

        # Retry logic with exponential backoff
        last_error = None
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                
                logger.info(f"Calling GPT-4o for asset analysis (attempt {attempt + 1}/{self.max_retries})...")
                
                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt},
                                {"type": "image_url", "image_url": {"url": image_url}}
                            ]
                        }
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=1000,
                    temperature=0.3
                )
                
                # Extract JSON from response
                content = response.choices[0].message.content
                analysis = json.loads(content)
                
                # Validate required fields
                required_fields = [
                    "asset_type", "primary_object", "colors", "dominant_colors_rgb",
                    "style_tags", "recommended_shot_types", "usage_contexts", "is_logo", "confidence"
                ]
                missing_fields = [field for field in required_fields if field not in analysis]
                if missing_fields:
                    raise ValueError(f"Missing required fields in analysis: {missing_fields}")
                
                # Validate data types
                if not isinstance(analysis["asset_type"], str):
                    raise ValueError("asset_type must be a string")
                if not isinstance(analysis["colors"], list):
                    raise ValueError("colors must be a list")
                if not isinstance(analysis["dominant_colors_rgb"], list):
                    raise ValueError("dominant_colors_rgb must be a list")
                if not isinstance(analysis["is_logo"], bool):
                    raise ValueError("is_logo must be a boolean")
                if not isinstance(analysis["confidence"], (int, float)):
                    raise ValueError("confidence must be a number")
                
                # Validate RGB arrays
                for rgb in analysis["dominant_colors_rgb"]:
                    if not isinstance(rgb, list) or len(rgb) != 3:
                        raise ValueError("dominant_colors_rgb must contain arrays of 3 integers")
                    if not all(isinstance(c, int) and 0 <= c <= 255 for c in rgb):
                        raise ValueError("RGB values must be integers between 0 and 255")
                
                # Handle logo_position_preference
                if analysis.get("is_logo") and not analysis.get("logo_position_preference"):
                    # Set default if logo detected but no preference provided
                    analysis["logo_position_preference"] = "bottom-right"
                elif not analysis.get("is_logo"):
                    analysis["logo_position_preference"] = None
                
                # Calculate cost
                usage = response.usage
                input_cost = usage.prompt_tokens * COST_PER_INPUT_TOKEN
                output_cost = usage.completion_tokens * COST_PER_OUTPUT_TOKEN
                total_cost = input_cost + output_cost
                
                elapsed_time = time.time() - start_time
                
                logger.info(
                    f"✓ GPT-4o analysis complete in {elapsed_time:.2f}s "
                    f"(tokens: {usage.total_tokens}, cost: ${total_cost:.4f})"
                )
                
                # Store full analysis in a nested field for reference
                analysis["_full_response"] = {
                    "tokens_used": usage.total_tokens,
                    "input_tokens": usage.prompt_tokens,
                    "output_tokens": usage.completion_tokens,
                    "cost": total_cost,
                    "processing_time": elapsed_time
                }
                
                return analysis
                
            except json.JSONDecodeError as e:
                last_error = f"Failed to parse JSON response: {str(e)}"
                logger.warning(f"Attempt {attempt + 1} failed: {last_error}")
            except ValueError as e:
                # Validation errors - don't retry, return error immediately
                logger.error(f"Analysis validation error: {str(e)}")
                raise ValueError(f"Invalid analysis response: {str(e)}")
            except Exception as e:
                last_error = f"API error: {str(e)}"
                logger.warning(f"Attempt {attempt + 1} failed: {last_error}")
                
                # Exponential backoff before retry
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    logger.info(f"Retrying in {delay:.1f}s...")
                    time.sleep(delay)
        
        # All retries failed
        raise RuntimeError(
            f"Failed to analyze asset after {self.max_retries} attempts. Last error: {last_error}"
        )


# Singleton instance
asset_analysis_service = AssetAnalysisService()

