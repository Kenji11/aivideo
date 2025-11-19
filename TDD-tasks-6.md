# TDD Implementation Tasks - Part 6: Delete Route, Storyboard Display Fixes, Preview Bug, and Image Count

**Goal:** Add delete functionality, fix storyboard image display bug, fix preview showing previous video, and reduce storyboard image count for short videos

---

## PR #1: Add Delete Route (Backend and Frontend)

**Goal:** Implement delete route that removes S3 files first, then database entry, then cache entries

**Deletion Order:**
1. Delete S3 files (all files associated with video)
2. Delete database entry
3. Delete cache entries (Redis)

**Rationale:** Delete S3 files first to ensure cleanup even if DB/cache deletion fails. Then remove DB entry, then cache.

**Files to Review:**
- `backend/app/api/video.py` (add DELETE endpoint)
- `backend/app/services/s3.py` (add delete methods if needed)
- `backend/app/services/redis.py` (use existing `delete_video_data` method)
- `frontend/src/lib/api.ts` (add delete API function)
- `frontend/src/App.tsx` or project list component (add delete button/action)

### Task 1.1: Add S3 File Deletion Method

**File:** `backend/app/services/s3.py`

- [ ] Add `delete_file(self, key: str) -> bool` method
  - Delete single file from S3
  - Handle S3 URL format (`s3://bucket/key`) and key format
  - Return True on success, False on failure
  - Log deletion attempts and results

- [ ] Add `delete_directory(self, prefix: str) -> bool` method
  - Delete all files with given prefix (e.g., `user_id/videos/video_id/`)
  - Use `list_files()` to get all files with prefix
  - Delete each file using `delete_file()`
  - Handle pagination if there are more than 1000 objects
  - Return True if all deletions succeed, False otherwise
  - Log number of files deleted

### Task 1.2: Create Delete Video Endpoint (Backend)

**File:** `backend/app/api/video.py`

- [ ] Add `DELETE /api/video/{video_id}` endpoint
  - Use `Depends(get_current_user)` for authentication
  - Verify video belongs to authenticated user
  - Return 404 if video not found
  - Return 403 if user doesn't own video

- [ ] Implement deletion sequence:
  1. Get video record from database
  2. Extract S3 prefix from video (use `get_video_s3_prefix(user_id, video_id)`)
  3. Delete all S3 files with that prefix using `s3_client.delete_directory()`
  4. Delete database entry using `db.delete(video)` and `db.commit()`
  5. Delete Redis cache entries using `redis_client.delete_video_data(video_id)`
  6. Return success response

- [ ] Error handling:
  - If S3 deletion fails: Log error but continue (don't fail entire operation)
  - If DB deletion fails: Rollback and return 500 error
  - If cache deletion fails: Log warning but don't fail (cache will expire)
  - Log each step for debugging

- [ ] Return response:
  - `200 OK` with message: `{"message": "Video deleted successfully"}`
  - Include video_id in response for confirmation

### Task 1.3: Add Delete API Function (Frontend)

**File:** `frontend/src/lib/api.ts`

- [ ] Add `deleteVideo(videoId: string): Promise<void>` function
  - Call `DELETE /api/video/{videoId}`
  - Handle errors (404, 403, 500)
  - Throw error with message for UI to display
  - Return void on success

### Task 1.4: Add Delete Button to Frontend

**File:** `frontend/src/App.tsx` (or appropriate component showing video list)

- [ ] Add delete button to video/project card
  - Show delete button (trash icon) on hover or always visible
  - Add confirmation dialog before deletion
  - Call `deleteVideo()` API function
  - Show loading state during deletion
  - Remove video from local state after successful deletion
  - Show error message if deletion fails

- [ ] Update video list after deletion:
  - Remove deleted video from `projects` state
  - Or refresh video list from API
  - Show success toast/notification

### Task 1.5: Testing

- [ ] Test S3 file deletion:
  - Create test video with files in S3
  - Verify all files are deleted (storyboard, chunks, stitched, final)
  - Verify S3 prefix structure is correct

- [ ] Test database deletion:
  - Verify video record is removed from database
  - Verify foreign key constraints are handled (if any)

- [ ] Test cache deletion:
  - Verify Redis keys are removed
  - Verify status endpoint returns 404 after deletion

- [ ] Test error cases:
  - Video not found (404)
  - User doesn't own video (403)
  - S3 deletion fails (should continue and delete DB)
  - DB deletion fails (should return 500)

- [ ] Test frontend:
  - Delete button appears and works
  - Confirmation dialog appears
  - Video disappears from list after deletion
  - Error messages display correctly

---

## PR #2: Fix Storyboard Image Not Showing on Frontend During Video Generation

**Goal:** Fix bug where storyboard images (animaticUrls) no longer appear on frontend during video generation

**Current Issue:**
- Storyboard images should appear in `VideoStatus.tsx` component
- Images are stored in `animaticUrls` state
- Images should be populated from status endpoint response

**Files to Review:**
- `frontend/src/pages/VideoStatus.tsx` (storyboard image display)
- `backend/app/api/status.py` (status endpoint response)
- `backend/app/services/status_builder.py` (builds status response)

### Task 2.1: Investigate Storyboard Image Data Flow

**Files:** `backend/app/api/status.py`, `backend/app/services/status_builder.py`

- [ ] Check status endpoint response structure
  - Verify `animatic_urls` field is included in response
  - Check if field name matches frontend expectation (`animaticUrls` vs `animatic_urls`)
  - Verify images are extracted from spec or phase_outputs

- [ ] Check how storyboard images are stored:
  - Phase 2 stores images in `spec['beats'][i]['image_url']`
  - Check if status builder extracts these URLs correctly
  - Verify S3 URLs are converted to presigned URLs

- [ ] Check status builder logic:
  - Review `build_status_response_from_redis_video_data()` function
  - Review `build_status_response_from_db()` function
  - Verify both functions extract `animatic_urls` from spec/phase_outputs

### Task 2.2: Fix Status Builder to Include Animatic URLs

**File:** `backend/app/services/status_builder.py`

- [ ] Extract animatic URLs from spec:
  - Get `spec['beats']` array
  - Extract `image_url` from each beat
  - Convert S3 URLs to presigned URLs if needed
  - Return as `animatic_urls` array in status response

- [ ] Handle both Redis and DB sources:
  - If data from Redis: Extract from `spec` field in Redis data
  - If data from DB: Extract from `video.spec` field
  - Ensure both paths return animatic URLs

- [ ] Verify field name matches frontend:
  - Frontend expects `animaticUrls` (camelCase)
  - Backend should return `animatic_urls` (snake_case)
  - Check if frontend converts or if backend should return camelCase

### Task 2.3: Fix Frontend to Display Storyboard Images

**File:** `frontend/src/pages/VideoStatus.tsx`

- [ ] Check how `animaticUrls` state is populated:
  - Verify `fetchStatus()` extracts `animaticUrls` from response
  - Check if field name matches (`animaticUrls` vs `animatic_urls`)
  - Verify state is updated when status response received

- [ ] Check display logic:
  - Verify `animaticUrls && animaticUrls.length > 0` condition
  - Check if images render correctly when URLs are present
  - Verify image error handling (onError handler)

- [ ] Add logging for debugging:
  - Log status response to console
  - Log `animaticUrls` state value
  - Log when images should be displayed

### Task 2.4: Testing

- [ ] Test during video generation:
  - Start video generation
  - Check status endpoint response includes `animatic_urls`
  - Verify frontend displays images immediately after Phase 2 completes
  - Verify images remain visible during Phase 3 and Phase 4

- [ ] Test with different video durations:
  - Short video (10s, 2-3 beats)
  - Medium video (30s, 5-6 beats)
  - Verify correct number of images displayed

- [ ] Test image URLs:
  - Verify presigned URLs are valid
  - Verify images load correctly
  - Test error handling for broken URLs

---

## PR #3: Fix Preview Showing Previous Video

**Goal:** Fix bug where preview page shows previous video if present instead of current video

**Current Issue:**
- Preview route (`/preview`) uses `stitchedVideoUrl` state
- State may persist from previous video generation
- Should clear state or fetch current video's URL

**Files to Review:**
- `frontend/src/App.tsx` (preview route and state)
- `frontend/src/pages/VideoStatus.tsx` (may set stitchedVideoUrl)

### Task 3.1: Investigate Preview State Management

**File:** `frontend/src/App.tsx`

- [ ] Check how `stitchedVideoUrl` state is managed:
  - Where is state initialized?
  - Where is state set/updated?
  - Is state cleared when navigating away?
  - Is state shared between different videos?

- [ ] Check preview route implementation:
  - How is `stitchedVideoUrl` populated?
  - Is it fetched from API or passed via navigation state?
  - Does it persist across navigation?

### Task 3.2: Fix Preview to Use Current Video

**File:** `frontend/src/App.tsx`

- [ ] Option A: Clear state on navigation
  - Clear `stitchedVideoUrl` when navigating to preview
  - Fetch current video's stitched URL from API
  - Use video ID from route params or navigation state

- [ ] Option B: Pass video ID to preview route
  - Add video ID to route: `/preview/:videoId`
  - Fetch video status on preview page load
  - Extract `stitched_video_url` from status response
  - Update state with current video's URL

- [ ] Option C: Use navigation state
  - Pass `stitchedVideoUrl` via navigation state
  - Don't rely on component state
  - Clear state after navigation

**Recommended:** Option B (use route params) - most reliable

### Task 3.3: Update Preview Route

**File:** `frontend/src/App.tsx`

- [ ] Update preview route to accept video ID:
  - Change route from `/preview` to `/preview/:videoId`
  - Extract `videoId` from route params
  - Fetch video status using `videoId`
  - Extract `stitched_video_url` from status response

- [ ] Add loading state:
  - Show loading indicator while fetching video
  - Show error message if video not found
  - Show error message if video has no stitched URL yet

- [ ] Clear previous state:
  - Reset `stitchedVideoUrl` when component mounts
  - Only set state after fetching current video's URL

### Task 3.4: Update Navigation to Preview

**Files:** `frontend/src/App.tsx`, `frontend/src/pages/VideoStatus.tsx`

- [ ] Update navigation calls:
  - Change `navigate('/preview')` to `navigate(`/preview/${videoId}`)`
  - Pass video ID when navigating to preview
  - Remove any code that sets `stitchedVideoUrl` before navigation

### Task 3.5: Testing

- [ ] Test preview with multiple videos:
  - Generate Video A, navigate to preview (should show Video A)
  - Generate Video B, navigate to preview (should show Video B, not Video A)
  - Verify each preview shows correct video

- [ ] Test preview with no video:
  - Navigate to preview with invalid video ID
  - Should show error or loading state
  - Should not show previous video

- [ ] Test preview during generation:
  - Navigate to preview before video is stitched
  - Should show loading or "not ready" message
  - Should not show previous video

---

## PR #4: Reduce Storyboard Image Count for 10s and 15s Videos

**Goal:** Fix issue where too many storyboard images are generated for short videos (10s or 15s)

**Current Issue:**
- Phase 1 may generate too many beats for short videos
- Each beat generates one storyboard image
- 10s video should have max 2 beats (5s each)
- 15s video should have max 3 beats (5s each)

**Files to Review:**
- `backend/app/phases/phase1_validate/validation.py` (beat count validation)
- `backend/app/phases/phase1_validate/service.py` (LLM prompt and beat selection)
- `backend/app/phases/phase2_storyboard/task.py` (image generation)

### Task 4.1: Investigate Current Beat Generation Logic

**File:** `backend/app/phases/phase1_validate/service.py`

- [ ] Check how beats are selected:
  - Review LLM prompt for beat selection
  - Check if duration is considered when selecting beats
  - Verify beat count validation is applied

- [ ] Check beat count validation:
  - Review `validate_and_fix_beat_count()` function
  - Verify it's called after LLM generates beats
  - Check if validation is working correctly

### Task 4.2: Review Beat Count Validation Logic

**File:** `backend/app/phases/phase1_validate/validation.py`

- [ ] Check `validate_and_fix_beat_count()` implementation:
  - Verify `max_beats = ceil(duration / 5)` calculation
  - Check if truncation is working correctly
  - Verify truncated beats have correct start times
  - Check if validation is called in `build_full_spec()`

- [ ] Test validation with short videos:
  - 10s video: Should allow max 2 beats (10/5 = 2)
  - 15s video: Should allow max 3 beats (15/5 = 3)
  - Verify truncation happens if LLM returns more beats

### Task 4.3: Improve LLM Prompt for Short Videos

**File:** `backend/app/phases/phase1_validate/service.py`

- [ ] Update LLM prompt to consider duration:
  - Add explicit instruction: "For videos under 20s, select fewer beats"
  - Add example: "10s video = 2 beats max, 15s video = 3 beats max"
  - Emphasize that beat count should match duration

- [ ] Add duration-based beat count hint:
  - Calculate `max_beats = ceil(duration / 5)` before LLM call
  - Include in prompt: "Select at most {max_beats} beats for this {duration}s video"
  - This helps LLM make better initial selection

### Task 4.4: Strengthen Beat Count Validation

**File:** `backend/app/phases/phase1_validate/validation.py`

- [ ] Ensure validation is always called:
  - Verify `validate_and_fix_beat_count()` is called in `build_full_spec()`
  - Add validation in other code paths if needed
  - Add logging when truncation occurs

- [ ] Improve truncation logic:
  - Ensure truncated beats still sum to correct duration
  - Verify start times are recalculated correctly
  - Check that beat durations are valid after truncation

- [ ] Add stricter validation:
  - Log warning if LLM returns more than `max_beats + 1` beats
  - Consider this a quality issue if it happens frequently
  - May indicate LLM prompt needs improvement

### Task 4.5: Testing

- [ ] Test 10s video:
  - Generate 10s video
  - Verify Phase 1 creates max 2 beats
  - Verify Phase 2 generates max 2 storyboard images
  - Check logs for truncation warnings

- [ ] Test 15s video:
  - Generate 15s video
  - Verify Phase 1 creates max 3 beats
  - Verify Phase 2 generates max 3 storyboard images
  - Check logs for truncation warnings

- [ ] Test edge cases:
  - 5s video: Should have 1 beat
  - 20s video: Should have max 4 beats
  - 30s video: Should have max 6 beats

- [ ] Test truncation:
  - Manually create spec with too many beats for duration
  - Verify truncation occurs
  - Verify truncated beats have correct durations and start times
  - Verify final duration matches requested duration

---

## Summary

**PR Order:**
1. **PR #1**: Add delete route (S3 → DB → Cache)
2. **PR #2**: Fix storyboard images not showing on frontend
3. **PR #3**: Fix preview showing previous video
4. **PR #4**: Reduce storyboard image count for short videos

**Key Files:**
- `backend/app/api/video.py` - Delete endpoint
- `backend/app/services/s3.py` - S3 deletion methods
- `backend/app/services/status_builder.py` - Status response builder
- `frontend/src/pages/VideoStatus.tsx` - Storyboard display
- `frontend/src/App.tsx` - Preview route
- `backend/app/phases/phase1_validate/validation.py` - Beat count validation

