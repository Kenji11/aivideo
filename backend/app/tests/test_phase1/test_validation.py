import pytest
import os
from app.phases.phase1_validate.service import PromptValidationService
from app.phases.phase1_validate.templates import load_template, list_templates, validate_template_choice
from app.common.exceptions import ValidationException


def test_list_templates():
    """Test that all 3 templates are available"""
    templates = list_templates()
    assert len(templates) == 3
    assert "product_showcase" in templates
    assert "lifestyle_ad" in templates
    assert "announcement" in templates


def test_load_template():
    """Test loading product_showcase template"""
    template = load_template("product_showcase")
    assert template["name"] == "Product Showcase"
    assert template["duration"] == 30
    assert template["fps"] == 30
    assert len(template["beats"]) == 5
    assert "audio" in template
    assert "transitions" in template


def test_load_invalid_template():
    """Test that loading invalid template raises ValueError"""
    with pytest.raises(ValueError, match="Template 'nonexistent' not found"):
        load_template("nonexistent")


def test_validate_template_choice():
    """Test template validation"""
    assert validate_template_choice("product_showcase") is True
    assert validate_template_choice("lifestyle_ad") is True
    assert validate_template_choice("announcement") is True
    assert validate_template_choice("invalid") is False


def test_validate_spec_missing_fields():
    """Test that validation catches missing required fields"""
    service = PromptValidationService()
    
    incomplete_spec = {
        "template": "product_showcase",
        "duration": 30
        # Missing: fps, resolution, beats, style, product, audio
    }
    
    with pytest.raises(ValidationException, match="Missing required fields"):
        service._validate_spec(incomplete_spec)


def test_validate_spec_duration_mismatch():
    """Test that validation catches duration mismatches"""
    service = PromptValidationService()
    
    spec = {
        "template": "product_showcase",
        "duration": 30,
        "fps": 30,
        "resolution": "1920x1080",
        "beats": [
            {"name": "test", "start": 0, "duration": 10}  # Only 10s but video is 30s
        ],
        "style": {"aesthetic": "cinematic", "color_palette": ["red"], "mood": "dramatic", "lighting": "soft"},
        "product": {"name": "Test Product", "category": "electronics"},
        "audio": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"}
    }
    
    with pytest.raises(ValidationException, match="don't match video duration"):
        service._validate_spec(spec)


# Tests requiring OpenAI API key
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)
def test_validate_prompt_with_api():
    """Test full prompt validation with real OpenAI API (if key available)"""
    service = PromptValidationService()
    
    test_prompt = "Create a luxury watch commercial with cinematic visuals and elegant music"
    
    result = service.validate_and_extract(test_prompt, assets=[])
    
    assert "template" in result
    assert "product" in result
    assert "style" in result
    assert "beats" in result
    assert len(result["beats"]) > 0

