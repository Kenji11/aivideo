#!/usr/bin/env python3
"""
Manual test script for Phase 3 reference generation.
Tests style guide and product reference generation with Replicate API.
"""

import sys
import json
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.phases.phase3_references.service import ReferenceAssetService
from app.common.constants import MOCK_USER_ID


def test_references():
    """Test the reference generation service with various specs"""
    
    # Initialize service
    service = ReferenceAssetService()
    
    # Test spec 1: Luxury product with style
    test_spec_1 = {
        'style': {
            'aesthetic': 'cinematic',
            'color_palette': ['gold', 'black', 'white'],
            'mood': 'elegant',
            'lighting': 'dramatic soft'
        },
        'product': {
            'name': 'Chronos Elite Watch',
            'category': 'luxury timepiece'
        },
        'uploaded_assets': []
    }
    
    # Test spec 2: Lifestyle product
    test_spec_2 = {
        'style': {
            'aesthetic': 'modern vibrant',
            'color_palette': ['blue', 'green', 'orange'],
            'mood': 'energetic',
            'lighting': 'bright natural'
        },
        'product': {
            'name': 'AeroRun Pro Shoes',
            'category': 'athletic footwear'
        },
        'uploaded_assets': []
    }
    
    # Test spec 3: No product (style guide only)
    test_spec_3 = {
        'style': {
            'aesthetic': 'minimalist',
            'color_palette': ['gray', 'white'],
            'mood': 'calm',
            'lighting': 'soft diffused'
        },
        'product': None,
        'uploaded_assets': []
    }
    
    test_specs = [
        {'name': 'Luxury Product', 'spec': test_spec_1, 'video_id': 'test_video_1'},
        {'name': 'Lifestyle Product', 'spec': test_spec_2, 'video_id': 'test_video_2'},
        {'name': 'Style Guide Only', 'spec': test_spec_3, 'video_id': 'test_video_3'}
    ]
    
    print("=" * 70)
    print("PHASE 3 REFERENCE GENERATION TEST")
    print("=" * 70)
    print()
    
    results = []
    
    for i, test in enumerate(test_specs, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}: {test['name']}")
        print(f"{'='*70}")
        print(f"Video ID: {test['video_id']}")
        print(f"Style: {test['spec']['style']['aesthetic']}")
        if test['spec']['product']:
            print(f"Product: {test['spec']['product']['name']}")
        print()
        
        try:
            # Generate references (using mock user ID for testing)
            output = service.generate_all_references(test['video_id'], test['spec'], MOCK_USER_ID)
            
            # Print results
            print(f"✅ SUCCESS!")
            print(f"Style Guide URL: {output.get('style_guide_url', 'N/A')}")
            if output.get('product_reference_url'):
                print(f"Product Reference URL: {output.get('product_reference_url')}")
            else:
                print(f"Product Reference: None (no product specified)")
            print(f"Total Cost: ${output.get('total_cost', 0):.4f}")
            print(f"Uploaded Assets: {len(output.get('uploaded_assets', []))}")
            
            # Save result
            results.append({
                'test_name': test['name'],
                'video_id': test['video_id'],
                'output': output
            })
            
        except Exception as e:
            print(f"❌ FAILED: {str(e)}")
            results.append({
                'test_name': test['name'],
                'video_id': test['video_id'],
                'error': str(e)
            })
    
    # Save all results
    output_file = "test_references_output.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print()
    print(f"💾 Saved results to: {output_file}")
    
    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_references()

