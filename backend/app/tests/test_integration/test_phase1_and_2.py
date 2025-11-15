"""
Integration test for Phase 1 and Phase 2 working together.

This test verifies that:
1. Phase 1 (validate_prompt) successfully creates a spec
2. Phase 2 (generate_animatic) successfully generates frames from that spec
3. Both phases work together end-to-end
"""
import pytest
import uuid
import os
from app.phases.phase1_validate.task import validate_prompt
from app.phases.phase2_animatic.task import generate_animatic
from app.config import get_settings


# Check if API keys are available
def has_api_keys():
    """Check if required API keys are present"""
    settings = get_settings()
    return bool(
        settings.openai_api_key and
        settings.replicate_api_token and
        settings.aws_access_key_id and
        settings.aws_secret_access_key
    )


@pytest.mark.integration
@pytest.mark.skipif(
    not has_api_keys(),
    reason="API keys not available - skipping integration test"
)
def test_phase1_and_phase2_integration():
    """Test Phase 1 and Phase 2 integration end-to-end"""
    # Generate test video_id
    test_video_id = str(uuid.uuid4())
    
    # Define test prompt and empty assets list
    test_prompt = "Create a luxury watch advertisement showcasing elegance and sophistication"
    test_assets = []
    
    # Test Phase 1: Validate Prompt
    print("\n" + "="*60)
    print("Testing Phase 1: Prompt Validation")
    print("="*60)
    
    result1 = validate_prompt(test_video_id, test_prompt, test_assets)
    
    # Assert Phase 1 success
    assert result1['status'] == 'success', f"Phase 1 failed: {result1.get('error_message')}"
    assert 'spec' in result1['output_data'], "Phase 1 output missing 'spec'"
    
    # Extract spec from output_data
    spec = result1['output_data']['spec']
    print(f"\n✓ Phase 1 completed successfully")
    print(f"  Template: {spec.get('template', 'unknown')}")
    print(f"  Beats: {len(spec.get('beats', []))}")
    
    # Test Phase 2: Generate Animatic
    print("\n" + "="*60)
    print("Testing Phase 2: Animatic Generation")
    print("="*60)
    
    result2 = generate_animatic(test_video_id, spec)
    
    # Assert Phase 2 success
    assert result2['status'] == 'success', f"Phase 2 failed: {result2.get('error_message')}"
    assert 'animatic_urls' in result2['output_data'], "Phase 2 output missing 'animatic_urls'"
    
    # Extract frame_urls from output_data
    frame_urls = result2['output_data']['animatic_urls']
    print(f"\n✓ Phase 2 completed successfully")
    print(f"  Frames generated: {len(frame_urls)}")
    print(f"  Phase 1 cost: ${result1['cost_usd']:.4f}")
    print(f"  Phase 2 cost: ${result2['cost_usd']:.4f}")
    print(f"  Total cost: ${result1['cost_usd'] + result2['cost_usd']:.4f}")
    
    # Verify Integration Results
    print("\n" + "="*60)
    print("Verifying Integration Results")
    print("="*60)
    
    # Assert frame count matches beat count
    assert len(frame_urls) == len(spec['beats']), \
        f"Frame count ({len(frame_urls)}) doesn't match beat count ({len(spec['beats'])})"
    
    # Assert each URL starts with 's3://'
    for i, url in enumerate(frame_urls):
        assert url.startswith('s3://'), \
            f"Frame {i+1} URL doesn't start with 's3://': {url}"
        print(f"  Frame {i+1}: {url}")
    
    print("\n✓ All integration checks passed!")
    print("="*60)

