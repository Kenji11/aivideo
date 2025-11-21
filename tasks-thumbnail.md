# PR: Video Thumbnail Generation

**Goal:** Add thumbnail generation for videos to improve My Projects page performance and user experience.

**Estimated Time:** 1-2 days  
**Dependencies:** None

---

## Task 1: Database Migration - Add thumbnail_url Column

**File:** `backend/migrations/005_add_thumbnail_url.sql`

- [ ] Create migration file `005_add_thumbnail_url.sql`
- [ ] Add `thumbnail_url` column to `video_generations` table
  - [ ] Type: `VARCHAR` (nullable)
  - [ ] Default: `NULL`
- [ ] Use `IF NOT EXISTS` check to make migration idempotent
- [ ] Test migration runs successfully on existing database

---

## Task 2: Thumbnail Generation Service

**File:** `backend/app/services/thumbnail.py` (NEW)

- [ ] Create `ThumbnailService` class
- [ ] Implement `extract_first_frame(video_path: str) -> str`
  - [ ] Use FFmpeg to extract first frame from video
  - [ ] Command: `ffmpeg -i {video_path} -vframes 1 -q:v 2 {output_path}`
  - [ ] Return path to extracted frame image
  - [ ] Handle errors gracefully
- [ ] Implement `resize_to_thumbnail(image_path: str, width: int = 640, height: int = 360) -> str`
  - [ ] Use PIL/Pillow to resize image
  - [ ] Maintain 16:9 aspect ratio (640x360)
  - [ ] Use high-quality resize (LANCZOS)
  - [ ] Save as JPEG with quality 85
  - [ ] Return path to resized thumbnail
- [ ] Implement `generate_video_thumbnail(video_path: str, user_id: str, video_id: str) -> str`
  - [ ] Extract first frame
  - [ ] Resize to 640x360 (16:9)
  - [ ] Upload to S3 using `get_video_s3_key(user_id, video_id, "thumbnail.jpg")`
  - [ ] Return S3 URL
  - [ ] Cleanup temp files
  - [ ] Wrap in try/catch to prevent failures

---

## Task 3: Phase 3 Integration - Generate Thumbnail After First Chunk

**File:** `backend/app/phases/phase3_chunks/task.py`

- [ ] Import `ThumbnailService`
- [ ] After first chunk is generated and uploaded to S3:
  - [ ] Download first chunk video from S3 (or use local temp file if available)
  - [ ] Call `thumbnail_service.generate_video_thumbnail()`
  - [ ] Wrap in try/catch block (don't fail Phase 3 if thumbnail generation fails)
  - [ ] Log warning if thumbnail generation fails, but continue
- [ ] Store thumbnail_url in database after successful generation
  - [ ] Update `video_generations` table with `thumbnail_url`
  - [ ] Use existing database session or create new one
- [ ] Add thumbnail_url to Phase 3 output data (optional, for debugging)

---

## Task 4: Migration Script for Existing Videos

**File:** `backend/scripts/generate_video_thumbnails.py`

- [ ] Create migration script
- [ ] Query all videos from `video_generations` table
- [ ] For each video:
  - [ ] Skip if `thumbnail_url` already exists
  - [ ] Check if first chunk exists in S3 (`chunk_00.mp4`)
  - [ ] If chunk exists:
    - [ ] Download chunk from S3
    - [ ] Generate thumbnail using `ThumbnailService`
    - [ ] Update database with `thumbnail_url`
    - [ ] Log success
  - [ ] If chunk doesn't exist:
    - [ ] Log warning and skip
  - [ ] Handle errors gracefully (continue to next video)
- [ ] Add progress logging (e.g., "Processing 5/100 videos...")
- [ ] Add summary at end (e.g., "Generated 95 thumbnails, skipped 5")
- [ ] Add command-line argument support:
  - [ ] `--dry-run`: Show what would be processed without making changes
  - [ ] `--limit N`: Process only first N videos (for testing)

---

## Task 5: Frontend - Use thumbnail_url in ProjectCard

**File:** `frontend/src/components/ProjectCard.tsx`

- [ ] Update `VideoListItem` interface to include `thumbnail_url` (if not already)
- [ ] Update ProjectCard component:
  - [ ] Check if `project.thumbnail_url` exists
  - [ ] If thumbnail_url exists:
    - [ ] Display thumbnail image instead of video element
    - [ ] Use `<img>` tag with `src={project.thumbnail_url}`
    - [ ] Keep hover behavior (video preview on hover) - this already works
  - [ ] If thumbnail_url doesn't exist:
    - [ ] Fallback to current behavior (video element or placeholder)
- [ ] Add loading state for thumbnail image
- [ ] Add error handling (fallback to video if thumbnail fails to load)
- [ ] Test with videos that have thumbnails and videos that don't

---

## Task 6: API Response - Include thumbnail_url

**File:** `backend/app/api/video.py`

- [ ] Update `list_videos()` endpoint response
  - [ ] Include `thumbnail_url` in `VideoListItem` schema
  - [ ] Query `thumbnail_url` from database
- [ ] Update `get_video()` endpoint response
  - [ ] Include `thumbnail_url` in `VideoResponse` schema
- [ ] Verify frontend receives `thumbnail_url` in API responses

---

## Task 7: Testing & Validation

**Unit Tests:**
- [ ] Test `extract_first_frame()` with valid video file
- [ ] Test `resize_to_thumbnail()` with various image sizes
- [ ] Test `generate_video_thumbnail()` end-to-end
- [ ] Test error handling (invalid video, missing file, etc.)

**Integration Tests:**
- [ ] Generate new video and verify thumbnail is created
- [ ] Verify thumbnail_url is saved to database
- [ ] Verify thumbnail is accessible via S3 URL
- [ ] Test migration script with sample videos

**Manual QA:**
- [ ] Generate new video → verify thumbnail appears in My Projects
- [ ] Run migration script → verify existing videos get thumbnails
- [ ] Verify hover preview still works with thumbnails
- [ ] Test with videos that have no chunks (should gracefully skip)
- [ ] Verify thumbnail aspect ratio matches video preview area (16:9)

---

## Acceptance Criteria

- [ ] `thumbnail_url` column exists in `video_generations` table (nullable)
- [ ] New videos automatically get thumbnails after Phase 3 completes
- [ ] Thumbnail generation doesn't fail Phase 3 if it errors
- [ ] Migration script successfully generates thumbnails for all existing videos
- [ ] Frontend displays thumbnails in My Projects page
- [ ] Hover preview still works (video plays on hover)
- [ ] Thumbnails are 640x360 (16:9 aspect ratio)
- [ ] Thumbnails are stored in S3 at `{user_id}/videos/{video_id}/thumbnail.jpg`
- [ ] API responses include `thumbnail_url` field
- [ ] All tests pass

---

**Note:** Thumbnail generation is non-blocking - if it fails, Phase 3 continues successfully. This ensures video generation isn't impacted by thumbnail issues.

