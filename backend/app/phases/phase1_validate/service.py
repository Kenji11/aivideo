import json
from typing import Dict, List
from app.services.openai import openai_client
from app.phases.phase1_validate.templates import load_template, validate_template_choice
from app.phases.phase1_validate.schemas import VideoSpec
from app.common.exceptions import ValidationException


class PromptValidationService:
    """Service for validating user prompts and creating video specifications"""
    
    def __init__(self):
        """Initialize the validation service"""
        self.openai = openai_client
        # Try to use OpenRouter if available, fallback to OpenAI
        try:
            from app.services.openrouter import openrouter_client
            if openrouter_client.api_key:
                self.use_openrouter = True
                self.openrouter = openrouter_client
            else:
                self.use_openrouter = False
        except Exception:
            self.use_openrouter = False
    
    def validate_and_extract(self, prompt: str, assets: List[Dict] = None) -> Dict:
        """
        Validate user prompt and extract structured video specification.
        
        Args:
            prompt: User's video description
            assets: Optional list of uploaded assets
            
        Returns:
            Complete video specification dictionary
            
        Raises:
            ValidationException: If validation fails
        """
        if assets is None:
            assets = []
        
        # Step 1: Extract intent from prompt using GPT-4
        extracted = self._extract_intent(prompt)
        # Store original prompt for duration optimization
        extracted['original_prompt'] = prompt
        
        # Step 2: Get template name with fallback
        template_name = extracted.get('template', 'product_showcase')
        
        # Step 3: Validate template choice
        if not validate_template_choice(template_name):
            template_name = 'product_showcase'
        
        # Step 4: Load template
        template = load_template(template_name)
        
        # Step 5: Merge extracted data with template
        full_spec = self._merge_with_template(extracted, template)
        
        # Step 6: Add uploaded assets
        full_spec['uploaded_assets'] = assets
        
        # Step 7: Validate the final spec
        self._validate_spec(full_spec)
        
        return full_spec
    
    def _extract_intent(self, prompt: str) -> Dict:
        """
        Extract structured intent from user prompt using GPT-4.
        
        Args:
            prompt: User's video description
            
        Returns:
            Extracted data dictionary
            
        Raises:
            ValidationException: If extraction fails
        """
        system_prompt = """You are an AI that extracts video specifications from natural language descriptions.

Available templates:
1. product_showcase - Professional product reveal with cinematic quality
2. lifestyle_ad - Energetic lifestyle advertisement with real-world usage
3. announcement - Dramatic announcement video with cinematic impact

Extract the following information from the user's prompt and return as JSON:

{
    "template": "product_showcase|lifestyle_ad|announcement",
    "product": {
        "name": "product name",
        "category": "product category"
    },
    "style": {
        "aesthetic": "description of visual style",
        "color_palette": ["color1", "color2", "color3"],
        "mood": "overall mood/feeling",
        "lighting": "lighting description"
    },
    "audio": {
        "music_style": "music genre/style",
        "tempo": "slow|moderate|fast",
        "mood": "audio mood"
    }
}

Choose the template that best matches the user's intent. Extract all available information, using reasonable defaults if information is missing."""
        
        try:
            # Use OpenRouter if available, otherwise OpenAI
            if self.use_openrouter:
                # OpenRouter API call (OpenAI-compatible format)
                response_data = self.openrouter.chat_completion(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    model="openai/gpt-4-turbo",  # Can use any model: "anthropic/claude-3-opus", "google/gemini-pro", etc.
                    temperature=0.3,
                    max_tokens=1000,
                    response_format={"type": "json_object"}  # Ensure JSON response
                )
                # Extract content from OpenRouter response (same format as OpenAI)
                content = response_data['choices'][0]['message']['content']
            else:
                # OpenAI API call
                response = self.openai.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                content = response.choices[0].message.content
            
            extracted = json.loads(content)
            return extracted
            
        except Exception as e:
            raise ValidationException(f"Failed to extract intent from prompt: {str(e)}")
    
    def _merge_with_template(self, extracted: Dict, template: Dict) -> Dict:
        """
        Merge extracted data with template structure.
        
        Args:
            extracted: Extracted data from GPT-4
            template: Template dictionary
            
        Returns:
            Merged specification
        """
        # Start with template as base
        spec = template.copy()
        
        # Optimize duration for ads - start with shorter videos (5-10s) that can be extended
        prompt_lower = extracted.get('original_prompt', '').lower() if 'original_prompt' in extracted else ''
        is_ad = 'ad' in prompt_lower or 'advertisement' in prompt_lower or 'commercial' in prompt_lower
        
        if is_ad:
            # For ads, start with 5-10 seconds (can be extended later)
            # Use 5 seconds for quick ads, 10 seconds for standard ads
            target_duration = 5 if 'quick' in prompt_lower or 'short' in prompt_lower else 10
            original_duration = spec.get('duration', 30)
            
            if original_duration > target_duration:
                spec['duration'] = target_duration
                # Scale down beat durations proportionally, but keep at least 1 second per beat
                total_beat_duration = sum(beat.get('duration', 0) for beat in spec.get('beats', []))
                if total_beat_duration > 0:
                    scale_factor = target_duration / original_duration
                    for beat in spec.get('beats', []):
                        new_duration = max(1, int(beat.get('duration', 0) * scale_factor))
                        beat['duration'] = new_duration
                    # Recalculate start times
                    current_start = 0
                    for beat in spec.get('beats', []):
                        beat['start'] = current_start
                        current_start += beat.get('duration', 0)
                
                # Mark as ad for potential extension
                spec['is_ad'] = True
                spec['original_duration'] = original_duration
        
        # Update template field
        spec['template'] = extracted.get('template', template.get('name', 'product_showcase'))
        
        # Merge style if present
        if 'style' in extracted:
            spec['style'] = extracted['style']
        
        # Merge product if present
        if 'product' in extracted:
            spec['product'] = extracted['product']
        
        # Merge audio if present
        if 'audio' in extracted:
            spec['audio'] = extracted['audio']
        
        # Enrich beat prompts with extracted data
        product_name = extracted.get('product', {}).get('name', 'product')
        style_aesthetic = extracted.get('style', {}).get('aesthetic', 'cinematic')
        
        for beat in spec['beats']:
            # Format prompt template with actual values
            beat['prompt_template'] = beat['prompt_template'].format(
                product_name=product_name,
                style_aesthetic=style_aesthetic
            )
        
        return spec
    
    def _validate_spec(self, spec: Dict) -> None:
        """
        Validate the final video specification.
        
        Args:
            spec: Video specification dictionary
            
        Raises:
            ValidationException: If validation fails
        """
        # Check required fields
        required_fields = ['template', 'duration', 'fps', 'resolution', 'beats', 'style', 'product', 'audio']
        missing = [f for f in required_fields if f not in spec]
        
        if missing:
            raise ValidationException(f"Missing required fields: {', '.join(missing)}")
        
        # Validate beats
        if not spec['beats']:
            raise ValidationException("Video must have at least one beat/scene")
        
        # Validate duration
        total_duration = sum(beat['duration'] for beat in spec['beats'])
        expected_duration = spec['duration']
        
        if abs(total_duration - expected_duration) > 1:  # Allow 1 second tolerance
            raise ValidationException(
                f"Beat durations ({total_duration}s) don't match video duration ({expected_duration}s)"
            )
