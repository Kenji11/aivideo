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

- [x] Add `delete_file(self, key: str) -> bool` method
  - Delete single file from S3
  - Handle S3 URL format (`s3://bucket/key`) and key format
  - Return True on success, False on failure
  - Log deletion attempts and results

- [x] Add `delete_directory(self, prefix: str) -> bool` method
  - Delete all files with given prefix (e.g., `user_id/videos/video_id/`)
  - Use `list_files()` to get all files with prefix
  - Delete each file using `delete_file()`
  - Handle pagination if there are more than 1000 objects
  - Return True if all deletions succeed, False otherwise
  - Log number of files deleted

### Task 1.2: Create Delete Video Endpoint (Backend)

**File:** `backend/app/api/video.py`

- [x] Add `DELETE /api/video/{video_id}` endpoint
  - Use `Depends(get_current_user)` for authentication
  - Verify video belongs to authenticated user
  - Return 404 if video not found
  - Return 403 if user doesn't own video

- [x] Implement deletion sequence:
  1. Get video record from database
  2. Extract S3 prefix from video (use `get_video_s3_prefix(user_id, video_id)`)
  3. Delete all S3 files with that prefix using `s3_client.delete_directory()`
  4. Delete database entry using `db.delete(video)` and `db.commit()`
  5. Delete Redis cache entries using `redis_client.delete_video_data(video_id)`
  6. Return success response

- [x] Error handling:
  - If S3 deletion fails: Log error but continue (don't fail entire operation)
  - If DB deletion fails: Rollback and return 500 error
  - If cache deletion fails: Log warning but don't fail (cache will expire)
  - Log each step for debugging

- [x] Return response:
  - `200 OK` with message: `{"message": "Video deleted successfully"}`
  - Include video_id in response for confirmation

### Task 1.3: Add Delete API Function (Frontend)

**File:** `frontend/src/lib/api.ts`

- [x] Add `deleteVideo(videoId: string): Promise<void>` function
  - Call `DELETE /api/video/{videoId}`
  - Handle errors (404, 403, 500)
  - Throw error with message for UI to display
  - Return void on success

### Task 1.4: Add Delete Button to Frontend

**File:** `frontend/src/App.tsx` (or appropriate component showing video list)

- [x] Add delete button to video/project card
  - Show delete button (trash icon) on hover or always visible
  - Add confirmation dialog before deletion
  - Call `deleteVideo()` API function
  - Show loading state during deletion
  - Remove video from local state after successful deletion
  - Show error message if deletion fails

- [x] Update video list after deletion:
  - Remove deleted video from `projects` state
  - Or refresh video list from API
  - Show success toast/notification

### Task 1.5: Testing

- [x] Test S3 file deletion:
  - Create test video with files in S3
  - Verify all files are deleted (storyboard, chunks, stitched, final)
  - Verify S3 prefix structure is correct

- [x] Test database deletion:
  - Verify video record is removed from database
  - Verify foreign key constraints are handled (if any)

- [x] Test cache deletion:
  - Verify Redis keys are removed
  - Verify status endpoint returns 404 after deletion

- [x] Test error cases:
  - Video not found (404)
  - User doesn't own video (403)
  - S3 deletion fails (should continue and delete DB)
  - DB deletion fails (should return 500)

- [x] Test frontend:
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

- [x] Check status endpoint response structure
  - Verify `animatic_urls` field is included in response
  - Check if field name matches frontend expectation (`animaticUrls` vs `animatic_urls`)
  - Verify images are extracted from spec or phase_outputs

- [x] Check how storyboard images are stored:
  - Phase 2 stores images in `spec['beats'][i]['image_url']`
  - Check if status builder extracts these URLs correctly
  - Verify S3 URLs are converted to presigned URLs

- [x] Check status builder logic:
  - Review `build_status_response_from_redis_video_data()` function
  - Review `build_status_response_from_db()` function
  - Verify both functions extract `animatic_urls` from spec/phase_outputs

### Task 2.2: Fix Status Builder to Include Animatic URLs

**File:** `backend/app/services/status_builder.py`

- [x] Extract animatic URLs from spec:
  - Get `spec['beats']` array
  - Extract `image_url` from each beat
  - Convert S3 URLs to presigned URLs if needed
  - Return as `animatic_urls` array in status response

- [x] Handle both Redis and DB sources:
  - If data from Redis: Extract from `spec` field in Redis data
  - If data from DB: Extract from `video.spec` field
  - Ensure both paths return animatic URLs

- [x] Verify field name matches frontend:
  - Frontend expects `animaticUrls` (camelCase)
  - Backend should return `animatic_urls` (snake_case)
  - Check if frontend converts or if backend should return camelCase

### Task 2.3: Fix Frontend to Display Storyboard Images

**File:** `frontend/src/pages/VideoStatus.tsx`

- [x] Check how `animaticUrls` state is populated:
  - Verify `fetchStatus()` extracts `animaticUrls` from response
  - Check if field name matches (`animaticUrls` vs `animatic_urls`)
  - Verify state is updated when status response received

- [x] Check display logic:
  - Verify `animaticUrls && animaticUrls.length > 0` condition
  - Check if images render correctly when URLs are present
  - Verify image error handling (onError handler)

- [x] Add logging for debugging:
  - Log status response to console
  - Log `animaticUrls` state value
  - Log when images should be displayed

### Task 2.4: Testing

- [x] Test during video generation:
  - Start video generation
  - Check status endpoint response includes `animatic_urls`
  - Verify frontend displays images immediately after Phase 2 completes
  - Verify images remain visible during Phase 3 and Phase 4

- [x] Test with different video durations:
  - Short video (10s, 2-3 beats)
  - Medium video (30s, 5-6 beats)
  - Verify correct number of images displayed

- [x] Test image URLs:
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

- [x] Check how `stitchedVideoUrl` state is managed:
  - Where is state initialized?
  - Where is state set/updated?
  - Is state cleared when navigating away?
  - Is state shared between different videos?

- [x] Check preview route implementation:
  - How is `stitchedVideoUrl` populated?
  - Is it fetched from API or passed via navigation state?
  - Does it persist across navigation?

### Task 3.2: Fix Preview to Use Current Video

**File:** `frontend/src/App.tsx`

- [x] Option A: Clear state on navigation
  - Clear `stitchedVideoUrl` when navigating to preview
  - Fetch current video's stitched URL from API
  - Use video ID from route params or navigation state

- [x] Option B: Pass video ID to preview route
  - Add video ID to route: `/preview/:videoId`
  - Fetch video status on preview page load
  - Extract `stitched_video_url` from status response
  - Update state with current video's URL

- [x] Option C: Use navigation state
  - Pass `stitchedVideoUrl` via navigation state
  - Don't rely on component state
  - Clear state after navigation

**Recommended:** Option B (use route params) - most reliable

### Task 3.3: Update Preview Route

**File:** `frontend/src/App.tsx`

- [x] Update preview route to accept video ID:
  - Change route from `/preview` to `/preview/:videoId`
  - Extract `videoId` from route params
  - Fetch video status using `videoId`
  - Extract `stitched_video_url` from status response

- [x] Add loading state:
  - Show loading indicator while fetching video
  - Show error message if video not found
  - Show error message if video has no stitched URL yet

- [x] Clear previous state:
  - Reset `stitchedVideoUrl` when component mounts
  - Only set state after fetching current video's URL

### Task 3.4: Update Navigation to Preview

**Files:** `frontend/src/App.tsx`, `frontend/src/pages/VideoStatus.tsx`

- [x] Update navigation calls:
  - Change `navigate('/preview')` to `navigate(`/preview/${videoId}`)`
  - Pass video ID when navigating to preview
  - Remove any code that sets `stitchedVideoUrl` before navigation

### Task 3.5: Testing

- [x] Test preview with multiple videos:
  - Generate Video A, navigate to preview (should show Video A)
  - Generate Video B, navigate to preview (should show Video B, not Video A)
  - Verify each preview shows correct video

- [x] Test preview with no video:
  - Navigate to preview with invalid video ID
  - Should show error or loading state
  - Should not show previous video

- [x] Test preview during generation:
  - Navigate to preview before video is stitched
  - Should show loading or "not ready" message
  - Should not show previous video

---

## PR #4: Reduce Storyboard Image Count for 10s and 15s Videos ✅

**COMPLETED - Root cause fixed:**
- Pipeline was using old template-based system
- Switched to intelligent planning system
- Beat count now adapts to duration correctly
- All beat durations are clean (5s/10s/15s only)

**Files Modified:**
- `backend/app/orchestrator/pipeline.py` - Swapped to intelligent planning
- `backend/app/orchestrator/celery_app.py` - Updated task imports
- `backend/app/api/generate.py` - Updated phase name
- `backend/app/phases/phase1_validate/validation.py` - Added LLM validation
- `backend/app/phases/phase1_validate/task_intelligent.py` - Added validation call
- `backend/app/phases/phase1_validate/prompts.py` - Enhanced for short videos

**Files Deleted:**
- `backend/app/phases/phase1_validate/task.py` - Old template system
- `backend/app/phases/phase1_validate/service.py` - Old validation service

### Task 4.1: Investigate Current Beat Generation Logic ✅

**COMPLETED - Investigation revealed:**
- Pipeline was using OLD template-based system (`task.py`)
- Old system scaled beats with math → fractional durations
- NEW intelligent system (`task_intelligent.py`) exists but wasn't active
- Beat library has proper 5/10/15s constraints

**Files investigated:**
- `backend/app/phases/phase1_validate/task.py` (old)
- `backend/app/phases/phase1_validate/task_intelligent.py` (new)
- `backend/app/phases/phase1_validate/service.py` (template system)
- `backend/app/phases/phase1_validate/prompts.py` (intelligent system)
- `backend/app/common/beat_library.py` (15 beats, 5/10/15s only)

### Task 4.2: Switch to Intelligent Planning System ✅

**COMPLETED - System migration:**
- ✅ Swapped pipeline to use `plan_video_intelligent` task
- ✅ Updated Celery imports to use `task_intelligent` module
- ✅ Added `validate_llm_beat_durations()` function
  - Validates LLM output BEFORE building spec
  - Fixes invalid durations to nearest 5/10/15s
  - Logs warnings when LLM returns bad values
- ✅ Removed `validate_and_fix_beat_count()` (no longer needed)
- ✅ Cleaned up unused imports (math, datetime, Path)
- ✅ Updated phase name from `phase1_validate` to `phase1_planning`

**Files modified:**
- `backend/app/orchestrator/pipeline.py`
- `backend/app/orchestrator/celery_app.py`
- `backend/app/api/generate.py`
- `backend/app/phases/phase1_validate/validation.py`
- `backend/app/phases/phase1_validate/task_intelligent.py`
- `backend/app/phases/phase1_validate/prompts.py`

### Task 4.3: Enhanced LLM Prompt for Short Videos ✅

**COMPLETED - Prompt improvements:**
- ✅ Added explicit short video examples:
  - 5s video = 1 beat
  - 10s video = 2 beats (5s + 5s)
  - 15s video = 3 beats
- ✅ Emphasized NO decimals, NO fractions, NO math
- ✅ Added stronger validation checklist
- ✅ Warned that system will reject invalid durations

**File:** `backend/app/phases/phase1_validate/prompts.py`

### Task 4.4: Multi-Stage Beat Validation ✅

**COMPLETED - Validation strategy:**
- ✅ Stage 1: `validate_llm_beat_durations()` after LLM call
  - Checks all durations are 5/10/15s
  - Fixes to nearest valid if needed
  - Logs warnings
- ✅ Stage 2: `build_full_spec()` during construction
  - Uses beat library durations
  - Validates beat_ids exist
- ✅ Stage 3: `validate_spec()` final check
  - Strict duration validation
  - Duration sum validation
  - No auto-fixing (fails if invalid)

**Files:** `backend/app/phases/phase1_validate/validation.py`, `task_intelligent.py`

### Task 4.5: Testing ✅

**COMPLETED - All tests passed:**
- ✅ 10s video generates 2 beats with clean 5s durations
- ✅ 15s video generates 3 beats with clean 5s/10s durations
- ✅ Beat count adapts correctly to video duration
- ✅ All beat durations are exactly 5s, 10s, or 15s
- ✅ Storyboard image count matches beat count
- ✅ No fractional durations
- ✅ LLM validation catches invalid durations
- ✅ Old template system removed (task.py, service.py deleted)

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

