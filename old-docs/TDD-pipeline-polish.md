# Pipeline Polish: Enhanced Extraction & Composition

## Overview

Improve Phase 1 extraction to capture user intent more precisely (music, colors, brand, scene requirements) and let o4-mini compose complete per-beat prompts for better narrative cohesion. Add logo overlay to closing beats automatically.

## Changes Needed

### 1. Phase 1 Schema Extensions (`backend/app/phases/phase1_validate/schemas.py`)

**Add new extraction fields to `VideoPlanning` schema:**

- `brand_name`: Optional string extracted from prompt
- `music_theme`: Optional string (genre/mood) - extract if mentioned, else o4-mini infers
- `color_scheme`: Optional list of colors - extract if mentioned, else o4-mini infers  
- `scene_requirements`: Optional dict mapping beat_ids to specific user requirements

**Update `BeatInfo` schema:**

- Replace simple `beat_id` + `duration` with full `composed_prompt` field
- Keep `beat_id` and `duration` for structure
- Add `composed_prompt`: Full scene description composed by o4-mini (not template)

### 2. Phase 1 System Prompt (`backend/app/phases/phase1_validate/task.py`)

**Update `build_gpt4_system_prompt()` to instruct o4-mini:**

```
1. **Extract User Intent** (new section)
   - Brand name: Extract company/brand if mentioned
   - Music: Extract genre/mood if mentioned (e.g., "upbeat electronic", "cinematic orchestral")
   - Colors: Extract color scheme if mentioned (e.g., ["gold", "black"], ["pastel pink", "white"])
   - Scene requirements: Extract any specific scene descriptions user provided
   
2. **Compose Per-Beat Prompts** (enhanced section)
   - Use beat library for structure and shot types
   - DON'T just use prompt_template - compose FULL scene descriptions
   - Incorporate: product, style, colors, mood, beat's shot_type and camera_movement
   - Create narrative flow across beats (not isolated scenes)
   - Each composed_prompt should be 2-3 sentences, highly detailed
   
3. **Infer Missing Elements**
   - If music not mentioned: infer appropriate genre based on archetype and mood
   - If colors not mentioned: infer palette based on product category and style
   - If scenes vague: create compelling scene compositions that tell a story
```

**Key changes:**
- Stop doing `.format()` substitution in `build_full_spec()` 
- Let o4-mini output `composed_prompt` directly in `BeatInfo`
- Keep beat library for structure/metadata but not for prompt templates

### 3. Phase 1 Spec Builder (`backend/app/phases/phase1_validate/validation.py`)

**Update `build_full_spec()`:**

```python
# OLD (line 189-193):
beat['prompt_template'] = beat['prompt_template'].format(
    product_name=intent['product']['name'],
    style_aesthetic=style['aesthetic'],
    setting=f"{style['mood']} setting"
)

# NEW:
# Use composed_prompt directly from LLM output
beat['prompt'] = beat_info.get('composed_prompt', beat_template['prompt_template'])
# Fallback to template if composed_prompt missing (backward compatibility)
```

**Add validation:**
- Validate `composed_prompt` exists and is non-empty for each beat
- Validate `music_theme` is reasonable if provided
- Validate `color_scheme` contains valid color names

### 4. Phase 2 Logo Overlay (`backend/app/phases/phase2_storyboard/image_generation.py`)

**Update `generate_storyboard_image()` for closing beats:**

```python
# After line 190 (reference_info extraction)
is_closing_beat = beat_info.get('typical_position') == 'closing'
brand_name = spec.get('brand_name')  # From Phase 1 extraction

# If closing beat and (has logo asset OR brand_name extracted):
if is_closing_beat:
    if recommended_logo:
        # Existing ControlNet path with logo asset
        # Ensure image_to_image_strength = 1.0 for logo preservation
    elif brand_name:
        # Add brand name to prompt for text overlay
        full_prompt += f", prominent brand text '{brand_name}' overlay, professional typography"
        logger.info(f"   Added brand name '{brand_name}' to closing beat prompt")
```

**Key changes:**
- Check `typical_position == 'closing'` for last beat detection
- If logo asset exists: use existing ControlNet path (already implemented)
- If no logo but brand_name extracted: add text overlay to prompt
- Ensure logo/brand always appears in closing

### 5. Frontend: Display Extracted Metadata (Optional Enhancement)

**Show extracted intent in video status page:**
- Brand name badge
- Music theme tag  
- Color palette swatches
- Scene requirements summary

(This can be a follow-up - not critical for core functionality)

## Files to Modify

1. `backend/app/phases/phase1_validate/schemas.py` - Add new fields
2. `backend/app/phases/phase1_validate/task.py` - Update system prompt
3. `backend/app/phases/phase1_validate/validation.py` - Remove template substitution, use composed_prompt
4. `backend/app/phases/phase2_storyboard/image_generation.py` - Add brand name overlay for closing beats
5. `backend/app/common/schemas.py` - Update spec type hints if needed

## Testing Strategy

1. **Test prompt variations:**
   - Explicit music: "Create an ad with upbeat electronic music"
   - Explicit colors: "Use gold and black color scheme"
   - Explicit scenes: "Show the watch on someone's wrist in the first scene"
   - Vague prompt: "Luxury watch ad" (let o4-mini infer everything)

2. **Test logo/brand:**
   - With logo asset uploaded → should use ControlNet
   - No logo but brand mentioned → should add text overlay
   - Neither logo nor brand → no closing overlay

3. **Verify narrative cohesion:**
   - Check if beats flow together naturally
   - Verify composed prompts reference each other
   - Ensure color scheme is consistent across beats

## Migration Notes

- **Backward compatibility**: Keep template substitution as fallback if `composed_prompt` missing
- **No database changes**: All new fields go in JSON `spec` column
- **Gradual rollout**: Old videos continue working, new videos use enhanced extraction

## Success Criteria

- ✅ o4-mini extracts brand_name, music_theme, color_scheme when present
- ✅ o4-mini infers missing elements appropriately
- ✅ Per-beat prompts are cohesive and tell a story
- ✅ Logo/brand appears in closing beats automatically
- ✅ Videos feel more polished and intentional

## Implementation Checklist

- [ ] Add brand_name, music_theme, color_scheme, scene_requirements to VideoPlanning schema
- [ ] Add composed_prompt field to BeatInfo schema for full LLM-generated prompts
- [ ] Enhance Phase 1 system prompt with extraction and composition instructions
- [ ] Update build_full_spec() to use composed_prompt instead of template.format()
- [ ] Add brand name text overlay for closing beats when no logo asset exists
- [ ] Test with explicit vs vague prompts to verify extraction and inference
- [ ] Verify logo/brand overlay works in closing beats

