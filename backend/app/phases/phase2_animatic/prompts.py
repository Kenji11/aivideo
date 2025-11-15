from typing import Dict


def _simplify_action(action: str) -> str:
    """
    Convert complex action types into simple, sketch-friendly descriptions.
    
    Args:
        action: The action type from the beat (e.g., "product_reveal", "introduce_character")
        
    Returns:
        Simplified action description suitable for animatic generation
    """
    action_map = {
        "product_reveal": "object in center of frame",
        "feature_highlight": "close-up of object details",
        "usage_scenario": "person holding object",
        "brand_story": "object in environment",
        "final_impression": "object with logo",
        "establish_environment": "wide shot of location",
        "introduce_character": "person standing",
        "use_product": "person interacting with object",
        "show_benefit": "person happy gesture",
        "product_branding": "object with text",
        "dramatic_intro": "bold geometric shapes",
        "show_message": "text centered",
        "visual_emphasis": "object prominent",
        "final_message": "logo and text",
    }
    
    return action_map.get(action, "simple scene composition")


def generate_animatic_prompt(beat: Dict, style: Dict) -> str:
    """
    Generate a simple, structural prompt for animatic frame generation.
    
    Animatic prompts should focus on composition and basic structure rather than
    detail. They are used to create low-fidelity reference frames that guide
    the final video generation process.
    
    Args:
        beat: Dictionary containing beat information with 'shot_type' and 'action' keys
        style: Dictionary containing style information (aesthetic, color_palette, etc.)
        
    Returns:
        A simplified prompt string suitable for generating sketch-style animatic frames
    """
    base_style = "simple sketch, minimal detail, line drawing style"
    
    shot_type = beat.get("shot_type", "medium")
    action = beat.get("action", "")
    
    simplified_action = _simplify_action(action)
    
    prompt = f"{simplified_action}, {shot_type} shot, {base_style}"
    
    return prompt


def create_negative_prompt() -> str:
    """
    Create a negative prompt to discourage detailed, photorealistic output.
    
    Returns:
        A comma-separated string of negative keywords to guide the model
        away from high-detail, rendered, or artistic styles
    """
    return "detailed, photorealistic, complex, colorful, high quality, rendered, painted, artistic, elaborate, ornate, decorative"
