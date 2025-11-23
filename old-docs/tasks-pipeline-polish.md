# Tasks: Pipeline Polish Enhancement

**Goal**: Enhance Phase 1 extraction to capture user intent (music, colors, brand, scene requirements) and let o4-mini compose complete per-beat prompts for better narrative cohesion. Add logo overlay to closing beats automatically.

---

## PR #1: Phase 1 Schema Extensions

**Description**: Add new fields to capture user intent and composed prompts. This enables o4-mini to extract brand names, music themes, color schemes, and scene requirements from prompts, and compose full scene descriptions instead of using templates.

**Context**: Currently, Phase 1 uses simple template substitution (`{product_name}`, `{style_aesthetic}`). We want o4-mini to compose complete 2-3 sentence prompts per beat that create narrative flow.

**Files to modify**:
- `backend/app/phases/phase1_validate/schemas.py`

### Tasks:

1. [x] Add `brand_name` field to `VideoPlanning` schema
   - Type: `Optional[str]`
   - Description: Company/brand name extracted from prompt or None

2. [x] Add `music_theme` field to `VideoPlanning` schema
   - Type: `Optional[str]`
   - Description: Music genre/mood (e.g., "upbeat electronic", "cinematic orchestral")
   - Extract if mentioned, else o4-mini infers based on archetype

3. [x] Add `color_scheme` field to `VideoPlanning` schema
   - Type: `Optional[List[str]]`
   - Description: List of 3-5 color names (e.g., ["gold", "black", "white"])
   - Extract if mentioned, else o4-mini infers based on product category

4. [x] Add `scene_requirements` field to `VideoPlanning` schema
   - Type: `Optional[Dict[str, str]]`
   - Description: Dict mapping beat_ids to specific user requirements
   - Example: `{"hero_shot": "show watch on wrist", "call_to_action": "include storefront"}`

5. [x] Add `composed_prompt` field to `BeatInfo` schema
   - Type: `str`
   - Description: Full scene description composed by o4-mini (2-3 sentences)
   - This replaces the template substitution approach

6. [x] Update schema docstrings and examples
   - Document new fields with clear descriptions
   - Add example JSON output showing new structure

7. [x] Test schema validation
   - Verify optional fields work correctly
   - Test with missing fields (should not break)
   - Verify `composed_prompt` is required in `BeatInfo`

---

## PR #2: Phase 1 Enhanced System Prompt & Spec Builder

**Description**: Update Phase 1 to extract user intent, compose full prompts per beat, and infer missing elements. This is where o4-mini gets instructions on how to use the new schema fields.

**Context**: The system prompt needs to guide o4-mini to:
1. Extract explicit user requirements (brand, music, colors, scene specifics)
2. Compose full scene descriptions (not just use templates)
3. Infer missing elements intelligently
4. Create narrative flow across beats

**Files to modify**:
- `backend/app/phases/phase1_validate/task.py`
- `backend/app/phases/phase1_validate/validation.py`

### Tasks:

1. [x] Add "Extract User Intent" section to system prompt in `build_gpt4_system_prompt()`
   - Instruct o4-mini to extract brand name if mentioned
   - Instruct to extract music genre/mood if mentioned
   - Instruct to extract color scheme if mentioned
   - Instruct to extract scene-specific requirements if mentioned

2. [x] Add "Compose Per-Beat Prompts" section to system prompt
   - Instruct: "Use beat library for structure and shot types"
   - Instruct: "DON'T just use prompt_template - compose FULL scene descriptions"
   - Instruct: "Incorporate product, style, colors, mood, beat's shot_type and camera_movement"
   - Instruct: "Create narrative flow across beats (not isolated scenes)"
   - Instruct: "Each composed_prompt should be 2-3 sentences, highly detailed"

3. [x] Add "Infer Missing Elements" section to system prompt
   - If music not mentioned: infer genre based on archetype and mood
   - If colors not mentioned: infer palette based on product category and style
   - If scenes vague: create compelling compositions that tell a story

4. [x] Update `build_full_spec()` in `validation.py` to use `composed_prompt`
   - Remove OLD code (lines 189-193): `beat['prompt_template'] = beat['prompt_template'].format(...)`
   - Add NEW code: `beat['prompt'] = beat_info.get('composed_prompt', beat_template['prompt_template'])`
   - Keep fallback to template for backward compatibility

5. [x] Add validation for `composed_prompt` in `validate_spec()`
   - Check that `composed_prompt` exists for each beat
   - Check that `composed_prompt` is non-empty (min 10 characters)
   - Log warning if composed_prompt seems too short

6. [x] Add validation for `music_theme` if provided
   - Check that it's a reasonable string (not empty, max 100 chars)
   - Log the extracted/inferred music theme

7. [x] Add validation for `color_scheme` if provided
   - Check that it contains 3-5 colors
   - Log the extracted/inferred color palette

8. [x] Update logging to show new extracted fields
   - Log brand_name if extracted
   - Log music_theme (extracted or inferred)
   - Log color_scheme (extracted or inferred)
   - Log scene_requirements if any

9. [x] Test with explicit prompts
   - "Create a Nike ad with upbeat electronic music and red/black colors"
   - Verify all fields extracted correctly

10. [x] Test with vague prompts
    - "Luxury watch ad"
    - Verify o4-mini infers music and colors appropriately

---

## PR #3: Phase 2 Logo/Brand Overlay for Closing Beats

**Description**: Automatically add logo or brand name to closing beats. If user uploaded a logo asset, use existing ControlNet path. If no logo but brand name extracted, add text overlay to prompt.

**Context**: Closing beats should ALWAYS include brand presence. This is critical for advertising - brand recall requires consistent logo/name placement at the end.

**Files to modify**:
- `backend/app/phases/phase2_storyboard/image_generation.py`

### Tasks:

0. [x] **CRITICAL**: Update Phase 2 & Phase 3 to use composed prompts
   - **Phase 2** (`image_generation.py` line 65):
     - Changed: `base_prompt = beat.get('prompt_template', '')` 
     - To: `base_prompt = beat.get('prompt', beat.get('prompt_template', ''))`
     - Added logging to show which prompt source is being used
   - **Phase 3** (`chunk_generator.py` line 239-243):
     - Changed: `prompt_template = beat.get('prompt_template', '')`
     - To: `prompt = beat.get('prompt', beat.get('prompt_template', ''))`
     - Added template substitution fallback if placeholders exist
     - Added logging for prompt source
   - This makes both Phase 2 (storyboard) and Phase 3 (chunks) use the beautiful LLM-composed prompts from Phase 1!

1. [x] Add closing beat detection in `generate_storyboard_image()`
   - After line 190 (reference_info extraction)
   - Add: `is_closing_beat = beat.get('typical_position') == 'closing'`

2. [x] Extract brand_name from spec
   - Add: `brand_name = spec.get('brand_name') if spec else None`
   - This comes from Phase 1 extraction
   - Added `spec` parameter to function signature

3. [x] Add conditional logic for closing beats
   - If `is_closing_beat` and `recommended_logo` exists:
     - Use existing ControlNet path (already implemented)
     - Ensure `image_to_image_strength = 1.0` for logo preservation
   - Elif `is_closing_beat` and `brand_name` exists:
     - Add brand text overlay to prompt
     - Format: `reference_prompt_parts.append(f"prominent brand text '{brand_name}' overlay")`

4. [x] Add logging for brand/logo overlay
   - Log when using logo asset with ControlNet
   - Log when adding brand name text overlay
   - Log warning if closing beat has neither logo nor brand name

5. [x] Test with logo asset uploaded
   - Upload logo via asset library
   - Generate video
   - Verify closing beat uses ControlNet with logo

6. [x] Test with brand name but no logo
   - Prompt: "Create a Nike ad for running shoes"
   - No logo asset uploaded
   - Verify closing beat prompt includes "Nike" text overlay

7. [x] Test with neither logo nor brand
   - Generic prompt: "Create an ad for running shoes"
   - No logo asset
   - Verify warning logged but video still generates

8. [x] Verify logo preservation strength
   - Check that `image_to_image_strength = 1.0` for logo scenes
   - This ensures logo is clearly visible and not distorted
   - Already implemented at line 258

---

## PR #4: Testing & Validation

**Description**: Comprehensive testing of all enhancements to verify extraction accuracy, prompt composition quality, narrative cohesion, and brand overlay functionality.

**Context**: This PR validates that all previous changes work together correctly and produce higher quality videos with better user control.

### Tasks:

#### Test Extraction Accuracy

1. [x] Test explicit music extraction
   - Prompt: "Create an ad with upbeat electronic music"
   - Verify `music_theme = "upbeat electronic"`

2. [x] Test explicit color extraction
   - Prompt: "Use gold and black color scheme"
   - Verify `color_scheme = ["gold", "black"]`

3. [x] Test explicit scene requirements
   - Prompt: "Show the watch on someone's wrist in the first scene"
   - Verify scene_requirements includes this for appropriate beat

4. [x] Test brand name extraction
   - Prompt: "Create a Nike ad for Air Max shoes"
   - Verify `brand_name = "Nike"`

5. [x] Test vague prompt (inference)
   - Prompt: "Luxury watch ad"
   - Verify o4-mini infers appropriate music and colors
   - Should infer elegant/cinematic music and sophisticated colors

#### Test Prompt Composition

6. [x] Verify composed prompts are 2-3 sentences
   - Check length of `composed_prompt` for each beat
   - Should be detailed and specific (min 100 chars per beat)

7. [x] Verify narrative flow across beats
   - Read all composed_prompts in sequence
   - Check that they reference each other or build on previous beats
   - Should feel like a cohesive story, not isolated scenes

8. [x] Verify color consistency
   - Check that color_scheme appears in multiple beat prompts
   - Colors should be used consistently throughout video

9. [x] Verify style consistency
   - Check that aesthetic style is maintained across all beats
   - Mood and tone should be consistent

#### Test Logo/Brand Overlay

10. [x] Test logo asset path
    - Upload logo via asset library
    - Generate video with closing beat
    - Verify ControlNet used with `image_to_image_strength = 1.0`
    - Verify logo visible in final frame

11. [x] Test brand name text overlay
    - Generate video with brand_name but no logo asset
    - Verify closing beat prompt includes brand text
    - Check final video for text overlay

12. [x] Test no logo and no brand
    - Generic prompt without brand mention
    - Verify warning logged
    - Verify video still generates successfully

#### Integration Testing

13. [x] Test complete flow: explicit prompt with logo
    - Prompt: "Create a Nike ad with energetic music, red and black colors, show shoes in action"
    - Upload Nike logo
    - Verify all extractions work
    - Verify composed prompts use specified elements
    - Verify logo appears in closing

14. [x] Test complete flow: vague prompt without logo
    - Prompt: "Luxury perfume ad"
    - No assets uploaded
    - Verify o4-mini infers music and colors
    - Verify composed prompts are cohesive
    - Verify closing beat doesn't crash without logo

15. [x] Compare before/after video quality
    - Generate same prompt with old system (if possible)
    - Generate with new system
    - Compare narrative flow and polish
    - Document improvements

#### Regression Testing

16. [x] Test backward compatibility
    - Old videos in database should still work
    - System should handle missing new fields gracefully

17. [x] Test error handling
    - Invalid color names
    - Extremely long music_theme strings
    - Empty composed_prompts
    - Verify appropriate errors/warnings

---

## Success Criteria

- ✅ o4-mini extracts brand_name, music_theme, color_scheme when present
- ✅ o4-mini infers missing elements appropriately
- ✅ Per-beat prompts are cohesive and tell a story (2-3 sentences each)
- ✅ Logo/brand appears in closing beats automatically
- ✅ Videos feel more polished and intentional
- ✅ Backward compatibility maintained (old videos still work)
- ✅ All tests pass

---

## Migration Notes

- **Backward compatibility**: Keep template substitution as fallback if `composed_prompt` missing
- **No database changes**: All new fields go in JSON `spec` column
- **Gradual rollout**: Old videos continue working, new videos use enhanced extraction
- **Cost impact**: Minimal - slightly longer prompts but same model (gpt-4o-mini)

---

## Optional Follow-up (Not in this PR set)

### Frontend: Display Extracted Metadata

**Show extracted intent in video status page:**
- Brand name badge
- Music theme tag  
- Color palette swatches
- Scene requirements summary

This can be implemented after core functionality is validated and working.

