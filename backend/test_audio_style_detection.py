#!/usr/bin/env python3
"""
Audio Style Detection Test
Tests intelligent audio style detection from video content/prompts
"""
import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Content to audio mapping
CONTENT_TO_AUDIO_MAP = {
    # Sports & Action
    "sport": {"music_style": "upbeat_pop", "tempo": "fast", "mood": "energetic"},
    "basketball": {"music_style": "upbeat_pop", "tempo": "fast", "mood": "energetic"},
    "football": {"music_style": "upbeat_pop", "tempo": "fast", "mood": "energetic"},
    "action": {"music_style": "cinematic_epic", "tempo": "fast", "mood": "inspiring"},
    "extreme": {"music_style": "cinematic_epic", "tempo": "fast", "mood": "inspiring"},
    
    # Luxury & Premium
    "luxury": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "premium": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "elegant": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "sophisticated": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    
    # Tech & Modern
    "tech": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    "modern": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    "innovation": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    
    # Lifestyle & Travel
    "lifestyle": {"music_style": "upbeat_pop", "tempo": "moderate", "mood": "energetic"},
    "travel": {"music_style": "cinematic_epic", "tempo": "moderate", "mood": "inspiring"},
    "adventure": {"music_style": "cinematic_epic", "tempo": "moderate", "mood": "inspiring"},
    
    # Corporate & Professional
    "corporate": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "professional": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
    "announcement": {"music_style": "orchestral", "tempo": "moderate", "mood": "sophisticated"},
}

def detect_audio_style(content: str) -> dict:
    """Detect audio style from content keywords"""
    content_lower = content.lower()
    
    for keyword, audio_config in CONTENT_TO_AUDIO_MAP.items():
        if keyword in content_lower:
            return audio_config.copy()
    
    return {
        "music_style": "orchestral",
        "tempo": "moderate",
        "mood": "sophisticated"
    }

# Test cases
TEST_CASES = [
    ("Nike Basketball Highlights", "upbeat_pop"),
    ("Luxury Watch Showcase", "orchestral"),
    ("Tech Product Launch", "upbeat_pop"),
    ("Travel Adventure Video", "cinematic_epic"),
    ("Corporate Announcement", "orchestral"),
    ("Extreme Sports Compilation", "cinematic_epic"),
    ("Fashion Brand Campaign", "orchestral"),
    ("Gaming Content Highlights", "upbeat_pop"),
]

print("="*80)
print("🎵 AUDIO STYLE DETECTION TEST")
print("="*80)
print()

for prompt, expected_style in TEST_CASES:
    detected = detect_audio_style(prompt)
    match = "✅" if detected["music_style"] == expected_style else "❌"
    print(f"{match} '{prompt}'")
    print(f"   Detected: {detected['music_style']} ({detected['tempo']}, {detected['mood']})")
    print(f"   Expected: {expected_style}")
    print()

