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
    
    def _merge_nested_dict(self, base: Dict, override: Dict, keys: List[str]) -> Dict:
        """
        Merge nested dictionary, only overwriting base values with non-null override values.
        
        Args:
            base: Base dictionary (template defaults)
            override: Override dictionary (extracted from GPT)
            keys: List of keys to merge
            
        Returns:
            Merged dictionary
        """
        result = base.copy() if base else {}
        if override:
            for key in keys:
                if key in override and override[key] is not None:
                    result[key] = override[key]
        return result
    
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
        
        # Optimize duration for ads or short videos - check for explicit duration requests
        prompt_lower = extracted.get('original_prompt', '').lower() if 'original_prompt' in extracted else ''
        is_ad = 'ad' in prompt_lower or 'advertisement' in prompt_lower or 'commercial' in prompt_lower
        
        # Check for explicit duration requests (e.g., "10 second", "10s", "10 seconds")
        import re
        duration_match = re.search(r'(\d+)\s*(?:second|sec|s)', prompt_lower)
        if duration_match:
            requested_duration = int(duration_match.group(1))
            # Limit to reasonable range (5-60 seconds)
            requested_duration = max(5, min(60, requested_duration))
            original_duration = spec.get('duration', 30)
            
            # FORCE the requested duration if user explicitly specified it (always apply, not just if less)
            if requested_duration != original_duration:
                spec['duration'] = requested_duration
                # Scale down beat durations proportionally, but keep at least 1 second per beat
                total_beat_duration = sum(beat.get('duration', 0) for beat in spec.get('beats', []))
                if total_beat_duration > 0:
                    scale_factor = requested_duration / original_duration
                    for beat in spec.get('beats', []):
                        new_duration = max(1, int(beat.get('duration', 0) * scale_factor))
                        beat['duration'] = new_duration
                    # Recalculate start times
                    current_start = 0
                    for beat in spec.get('beats', []):
                        beat['start'] = current_start
                        current_start += beat.get('duration', 0)
                
                print(f"   📏 Duration FORCED: {original_duration}s → {requested_duration}s (user explicitly requested)")
        elif is_ad:
            # For ads without explicit duration, FORCE to 10-15 seconds (default 12 seconds)
            # Use 10 seconds for quick ads, 15 seconds for standard ads
            if 'quick' in prompt_lower or 'short' in prompt_lower:
                target_duration = 10
            elif 'long' in prompt_lower or 'extended' in prompt_lower:
                target_duration = 15
            else:
                target_duration = 12  # Default for ads: 12 seconds
            original_duration = spec.get('duration', 30)
            
            # FORCE ad duration (always apply, not just if longer)
            if original_duration != target_duration:
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
                print(f"   📏 Ad duration FORCED: {original_duration}s → {target_duration}s (ad detected)")
        
        # Update template field
        spec['template'] = extracted.get('template', template.get('name', 'product_showcase'))
        
        # Merge style if present (preserve template defaults, only override non-null values)
        if 'style' in extracted:
            template_style = spec.get('style', {})
            extracted_style = extracted.get('style', {})
            spec['style'] = self._merge_nested_dict(
                template_style,
                extracted_style,
                ['aesthetic', 'color_palette', 'mood', 'lighting']
            )
        
        # Merge product if present (preserve template defaults, only override non-null values)
        if 'product' in extracted:
            template_product = spec.get('product', {})
            extracted_product = extracted.get('product', {})
            spec['product'] = self._merge_nested_dict(
                template_product,
                extracted_product,
                ['name', 'category']
            )
        
        # Merge audio if present (preserve template defaults, only override non-null values)
        # Always ensure audio is in spec (from template if not in extracted)
        if 'audio' in extracted:
            template_audio = spec.get('audio', {})
            extracted_audio = extracted.get('audio', {})
            spec['audio'] = self._merge_nested_dict(
                template_audio,
                extracted_audio,
                ['music_style', 'tempo', 'mood']
            )
        # Ensure audio exists even if not in extracted (use template default)
        if 'audio' not in spec or not spec.get('audio'):
            spec['audio'] = template.get('audio', {
                'music_style': 'orchestral',
                'tempo': 'moderate',
                'mood': 'sophisticated'
            })
        
        # Enrich beat prompts with merged data (use spec values, fallback to extracted, then defaults)
        product_name = spec.get('product', {}).get('name') or extracted.get('product', {}).get('name', 'product')
        style_aesthetic = spec.get('style', {}).get('aesthetic') or extracted.get('style', {}).get('aesthetic', 'cinematic')
        
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
        
        # Validate and auto-fix duration mismatch
        total_duration = sum(beat['duration'] for beat in spec['beats'])
        expected_duration = spec['duration']
        
        if abs(total_duration - expected_duration) > 1:  # Allow 1 second tolerance
            # Auto-fix: Scale beat durations proportionally to match expected duration
            if total_duration > 0:
                scale_factor = expected_duration / total_duration
                print(f"   ⚠️  Beat durations ({total_duration}s) don't match video duration ({expected_duration}s)")
                print(f"   🔧 Auto-fixing: Scaling beats by factor {scale_factor:.2f}")
                
                for beat in spec['beats']:
                    beat['duration'] = max(1.0, beat['duration'] * scale_factor)  # Minimum 1 second per beat
                    # Update start time based on previous beats
                    beat_index = spec['beats'].index(beat)
                    if beat_index == 0:
                        beat['start'] = 0.0
                    else:
                        beat['start'] = sum(b['duration'] for b in spec['beats'][:beat_index])
                
                # Verify fix
                new_total = sum(beat['duration'] for beat in spec['beats'])
                if abs(new_total - expected_duration) > 1:
                    raise ValidationException(
                        f"Failed to fix beat durations: {new_total}s vs {expected_duration}s"
                    )
                print(f"   ✅ Fixed: Beat durations now total {new_total:.1f}s (target: {expected_duration}s)")
            else:
                raise ValidationException(
                    f"Beat durations ({total_duration}s) don't match video duration ({expected_duration}s)"
                )
