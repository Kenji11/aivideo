import pytest
from app.phases.phase2_animatic.prompts import (
    generate_animatic_prompt,
    create_negative_prompt,
    _simplify_action,
)


def test_simplify_action():
    """Test action simplification with known and unknown actions"""
    # Test known actions
    assert _simplify_action("product_reveal") == "object in center of frame"
    assert _simplify_action("introduce_character") == "person standing"
    assert _simplify_action("establish_environment") == "wide shot of location"
    assert _simplify_action("use_product") == "person interacting with object"
    
    # Test unknown action returns fallback
    assert _simplify_action("unknown_action") == "simple scene composition"
    assert _simplify_action("") == "simple scene composition"


def test_create_negative_prompt():
    """Test that negative prompt contains all required key terms"""
    negative_prompt = create_negative_prompt()
    
    # Verify contains key terms
    assert "detailed" in negative_prompt
    assert "photorealistic" in negative_prompt
    assert "complex" in negative_prompt
    assert "colorful" in negative_prompt
    assert "high quality" in negative_prompt
    assert "rendered" in negative_prompt
    assert "painted" in negative_prompt
    assert "artistic" in negative_prompt
    assert "elaborate" in negative_prompt
    assert "ornate" in negative_prompt
    assert "decorative" in negative_prompt


def test_generate_animatic_prompt():
    """Test full prompt generation with sample beat and style"""
    # Define sample beat and style
    beat = {
        "shot_type": "close_up",
        "action": "product_reveal",
    }
    style = {
        "aesthetic": "luxury",
        "color_palette": "warm",
    }
    
    prompt = generate_animatic_prompt(beat, style)
    
    # Verify prompt contains simplified action
    assert "object in center of frame" in prompt
    
    # Verify prompt contains shot type
    assert "close_up" in prompt
    
    # Verify prompt contains sketch style
    assert "simple sketch" in prompt
    assert "minimal detail" in prompt
    assert "line drawing style" in prompt


def test_generate_animatic_prompt_with_different_actions():
    """Test prompt generation with different action types"""
    beat1 = {"shot_type": "wide", "action": "establish_environment"}
    style = {"aesthetic": "modern"}
    
    prompt1 = generate_animatic_prompt(beat1, style)
    assert "wide shot of location" in prompt1
    assert "wide shot" in prompt1
    
    beat2 = {"shot_type": "medium", "action": "introduce_character"}
    prompt2 = generate_animatic_prompt(beat2, style)
    assert "person standing" in prompt2
    assert "medium shot" in prompt2


def test_generate_animatic_prompt_with_missing_fields():
    """Test prompt generation handles missing fields gracefully"""
    beat = {"shot_type": "close_up"}  # Missing action
    style = {}
    
    prompt = generate_animatic_prompt(beat, style)
    
    # Should still generate a valid prompt with fallback
    assert "simple scene composition" in prompt
    assert "close_up shot" in prompt
    assert "simple sketch" in prompt

