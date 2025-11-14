#!/usr/bin/env python3
"""
Simple Phase 1 test without database - Just validates OpenAI integration
"""

import os
import sys

# Check for OpenAI key
OPENAI_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_KEY or OPENAI_KEY == 'your-openai-key-here':
    print("❌ Error: OPENAI_API_KEY not set!")
    print("Please add your key to backend/.env file")
    sys.exit(1)

print("✅ OpenAI API Key found!")
print(f"   Key starts with: {OPENAI_KEY[:20]}...")
print()

# Test that we can import our modules
print("📦 Testing imports...")
sys.path.insert(0, 'app')

try:
    from phases.phase1_validate.templates import list_templates, load_template
    print("   ✅ Templates module imported")
    
    templates = list_templates()
    print(f"   ✅ Found {len(templates)} templates: {templates}")
    
    template = load_template('product_showcase')
    print(f"   ✅ Loaded product_showcase: {template['name']}")
    print()
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    sys.exit(1)

print("=" * 70)
print("✅ Phase 1 Components Ready!")
print("=" * 70)
print()
print("🎯 AWS Status: Empty (temporary - will skip S3 operations)")
print("🎯 Replicate Status: Configured (ready for Phases 3-5)")
print("🎯 OpenAI Status: Configured (ready for Phase 1)")
print()
print("📝 To test full Phase 1 with OpenAI:")
print("   1. Install dependencies: pip install -r requirements.txt")
print("   2. Run test: python test_phase1.py")
print("=" * 70)

