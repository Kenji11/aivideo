# TDD Implementation Tasks - Part 4: Phase 4 Stitching & Phase 5 Music

**Goal:** Implement stitching and music generation to complete pipeline

---

## PR #10: Phase 4 Stitching Implementation

### Task 10.1: Create Phase 4 Directory Structure

- [ ] Create directory `backend/app/phases/phase4_stitching/`
- [ ] Create `__init__.py` in phase4_stitching
- [ ] Create `task.py` in phase4_stitching

### Task 10.2: Implement Phase 4 Task

**File:** `backend/app/phases/phase4_stitching/task.py`

- [ ] Import celery_app
- [ ] Import PhaseOutput from common.schemas
- [ ] Import ffmpeg_service, s3_client from services
- [ ] Import download_from_s3 (can reuse from phase3)
- [ ] Import tempfile, time, logging
- [ ] Create logger instance
- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `stitch_chunks(self, video_id, chunks)` function
- [ ] Add docstring with Args and Returns
- [ ] Record start_time
- [ ] Log start with video_id and chunk count

### Task 10.3: Implement Chunk Download & Concat File Creation

**File:** `backend/app/phases/phase4_stitching/task.py` (continued)

- [ ] Wrap in try/except block
- [ ] Initialize empty chunk_paths list
- [ ] Loop through chunks:
  - [ ] Call download_from_s3(chunk['url'])
  - [ ] Append path to chunk_paths
- [ ] Create temp concat file (.txt)
- [ ] Open concat file for writing
- [ ] Write each chunk path as: `file '{path}'`
- [ ] Close concat file

### Task 10.4: Implement FFmpeg Stitching

**File:** `backend/app/phases/phase4_stitching/task.py` (continued)

- [ ] Create temp output path (.mp4)
- [ ] Call ffmpeg_service.run_command with:
  - [ ] '-f', 'concat'
  - [ ] '-safe', '0'
  - [ ] '-i', concat_file
  - [ ] '-c', 'copy' (no re-encode)
  - [ ] output_path
- [ ] Log stitching success
- [ ] Construct s3_key: `videos/{video_id}/stitched.mp4`
- [ ] Upload to S3
- [ ] Calculate total_duration = len(chunks) * 5.0
- [ ] Log completion with URL

### Task 10.5: Implement Success/Failure Paths

**File:** `backend/app/phases/phase4_stitching/task.py` (continued)

- [ ] Create PhaseOutput with:
  - [ ] video_id
  - [ ] phase="phase4_stitching"
  - [ ] status="success"
  - [ ] output_data={stitched_url, total_duration, resolution, fps}
  - [ ] cost_usd=0.0 (no API cost)
  - [ ] duration_seconds
  - [ ] error_message=None
- [ ] Return output.dict()
- [ ] In except block:
  - [ ] Log error
  - [ ] Create PhaseOutput with status="failed"
  - [ ] Set error_message
  - [ ] Return output.dict()

---

## PR #11: Phase 5 Music Generation Implementation

### Task 11.1: Create Phase 5 Directory Structure

- [ ] Create directory `backend/app/phases/phase5_music/`
- [ ] Create `__init__.py` in phase5_music
- [ ] Create `task.py` in phase5_music
- [ ] Create `music_prompts.py` in phase5_music

### Task 11.2: Implement Music Prompt Builder

**File:** `backend/app/phases/phase5_music/music_prompts.py`

- [ ] Create `build_music_prompt(spec: dict) -> str` function
- [ ] Extract style from spec
- [ ] Extract mood from style
- [ ] Extract aesthetic from style
- [ ] Create mood_to_music mapping dict:
  - [ ] "energetic": "upbeat electronic music, fast tempo, motivational"
  - [ ] "elegant": "sophisticated orchestral music, elegant strings, refined"
  - [ ] "minimalist": "minimal ambient music, clean tones, modern"
  - [ ] "emotional": "emotional piano music, heartfelt, warm"
  - [ ] "informative": "corporate background music, professional, steady"
- [ ] Get music description from mapping (fallback to "modern background music")
- [ ] Return formatted prompt: `{music_desc}, {aesthetic} style, instrumental only, no vocals`

### Task 11.3: Implement Phase 5 Task

**File:** `backend/app/phases/phase5_music/task.py`

- [ ] Import celery_app
- [ ] Import PhaseOutput from common.schemas
- [ ] Import replicate_client, ffmpeg_service, s3_client
- [ ] Import download_from_s3
- [ ] Import build_music_prompt from .music_prompts
- [ ] Import COST_MUSICGEN from constants
- [ ] Import tempfile, requests, time, logging
- [ ] Create logger instance
- [ ] Create `@celery_app.task(bind=True)` decorator
- [ ] Define `generate_music(self, video_id, spec, stitched_url)` function
- [ ] Add docstring
- [ ] Record start_time
- [ ] Log start message

### Task 11.4: Implement Music Generation

**File:** `backend/app/phases/phase5_music/task.py` (continued)

- [ ] Wrap in try/except block
- [ ] Call build_music_prompt(spec)
- [ ] Get duration from spec
- [ ] Log music prompt and duration
- [ ] Call replicate_client.run with:
  - [ ] model="meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
  - [ ] input.prompt = music_prompt
  - [ ] input.duration = duration
  - [ ] input.model_version = "stereo-melody-large"
- [ ] Extract music URL from output
- [ ] Download music with requests.get
- [ ] Save to temp file (.mp3)
- [ ] Upload to S3: `videos/{video_id}/music.mp3`
- [ ] Log music upload success

### Task 11.5: Implement Video + Music Merge

**File:** `backend/app/phases/phase5_music/task.py` (continued)

- [ ] Download stitched video from S3
- [ ] Create temp output path (.mp4)
- [ ] Call ffmpeg_service.run_command with:
  - [ ] '-i', video_path
  - [ ] '-i', music_path
  - [ ] '-c:v', 'copy'
  - [ ] '-c:a', 'aac'
  - [ ] '-shortest' (cut to shortest input)
  - [ ] output_path
- [ ] Log merge success
- [ ] Upload final video to S3: `videos/{video_id}/final.mp4`
- [ ] Log completion with final URL

### Task 11.6: Implement Success/Failure Paths

**File:** `backend/app/phases/phase5_music/task.py` (continued)

- [ ] Create PhaseOutput with:
  - [ ] video_id
  - [ ] phase="phase5_music"
  - [ ] status="success"
  - [ ] output_data={final_video_url, music_url}
  - [ ] cost_usd=COST_MUSICGEN
  - [ ] duration_seconds
  - [ ] error_message=None
- [ ] Return output.dict()
- [ ] In except block:
  - [ ] Log error
  - [ ] Create PhaseOutput with status="failed"
  - [ ] Set error_message
  - [ ] cost_usd=0.0
  - [ ] Return output.dict()

---

## PR #12: Phase 4 & 5 Tests

### Task 12.1: Create Phase 4 Tests

**File:** `backend/app/tests/test_phase4/test_stitching.py`

- [ ] Import pytest
- [ ] Import stitch_chunks from phase4_stitching.task
- [ ] Create mock chunks list (3 chunks)
- [ ] Create `test_stitch_basic()`:
  - [ ] Mock chunk downloads
  - [ ] Call stitch_chunks
  - [ ] Assert stitched_url returned
- [ ] Create `test_stitch_duration_calculation()`:
  - [ ] 3 chunks
  - [ ] Assert total_duration == 15.0
- [ ] Create `test_stitch_no_cost()`:
  - [ ] Assert cost_usd == 0.0

### Task 12.2: Create Phase 5 Tests

**File:** `backend/app/tests/test_phase5/test_music.py`

- [ ] Import pytest
- [ ] Import build_music_prompt, generate_music
- [ ] Create `test_music_prompt_energetic()`:
  - [ ] Spec with mood="energetic"
  - [ ] Assert "upbeat electronic" in prompt
- [ ] Create `test_music_prompt_elegant()`:
  - [ ] Spec with mood="elegant"
  - [ ] Assert "orchestral" in prompt
- [ ] Create `test_music_prompt_instrumental()`:
  - [ ] All prompts should contain "instrumental only"
- [ ] Create `@pytest.mark.integration` test for full music generation (if API key)

### Task 12.3: Create Full Pipeline Integration Test

**File:** `backend/app/tests/test_integration/test_full_pipeline.py`

- [ ] Import pytest, os
- [ ] Import all 5 phase tasks
- [ ] Create `@pytest.mark.integration` decorator
- [ ] Create `@pytest.mark.skipif` for API keys
- [ ] Create `test_full_pipeline_15s()`:
  - [ ] Phase 1: Plan with "15s Nike sneakers energetic"
  - [ ] Assert success, extract spec
  - [ ] Phase 2: Generate storyboard
  - [ ] Assert success, extract storyboard
  - [ ] Phase 3: Generate chunks
  - [ ] Assert success, extract chunks
  - [ ] Phase 4: Stitch chunks
  - [ ] Assert success, extract stitched_url
  - [ ] Phase 5: Generate music
  - [ ] Assert success, extract final_video_url
  - [ ] Verify final video exists in S3
  - [ ] Calculate total cost
  - [ ] Assert total cost < $0.50
  - [ ] Assert total time < 300s (5 minutes)

---

## ✅ PR #10, #11, #12 Checklist

Before merging:
- [ ] FFmpeg stitching works correctly
- [ ] Concat file format is correct
- [ ] Music prompt builder works for all moods
- [ ] MusicGen generates appropriate music
- [ ] Video + music merge works
- [ ] Full pipeline integration test passes
- [ ] Total cost for 15s video < $0.50
- [ ] Total time for 15s video < 5 minutes

**Next:** Move to `TDD-tasks-5.md` for orchestration and API endpoints