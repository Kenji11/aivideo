# Phase 1 & 2 Integration Testing Tasks

**Owner:** Person handling integration testing  
**Goal:** Make Phase 1 and Phase 2 testable end-to-end

---

## PR: Phase 1 & 2 Integration Testing

### Task 1: Connect Video Gen Page to Video Gen Endpoint

**File:** `frontend/src/App.tsx`

- [ ] Update `handleSubmit` function to call `/api/generate` endpoint
- [ ] Send `title`, `description`, `prompt`, and `reference_assets` in request body
- [ ] Handle response with `video_id` and store it in state
- [ ] Update UI to show processing state after successful submission
- [ ] Add error handling for failed API calls
- [ ] Display error messages to user if generation fails to start

**Details:**
- Endpoint: `POST /api/generate`
- Request body should match `GenerateRequest` schema
- Response will contain `video_id` to track progress

---

### Task 2: Create Asset Upload Endpoint

**File:** `backend/app/api/upload.py` (new file)

- [ ] Create new API router for upload endpoints
- [ ] Implement `POST /api/upload` endpoint
- [ ] Accept multipart/form-data with file(s)
- [ ] Validate file types (images, videos, PDFs)
- [ ] Upload files to S3 using S3Client
- [ ] Create Asset record in database with:
  - `id` (UUID)
  - `s3_key` and `s3_url`
  - `asset_type` (IMAGE, VIDEO, AUDIO)
  - `source` (USER_UPLOAD)
  - `file_name`, `file_size_bytes`, `mime_type`
  - `asset_metadata` (dimensions, duration if applicable)
- [ ] Return asset ID(s) in response
- [ ] Add error handling for upload failures
- [ ] Register router in `backend/app/main.py`

**Details:**
- Use FastAPI's `UploadFile` for file handling
- Store files in S3 with path: `assets/{user_id}/{asset_id}/{filename}`
- Return list of asset IDs for multiple file uploads

---

### Task 3: Connect Frontend Asset Upload to Upload Endpoint

**File:** `frontend/src/components/UploadZone.tsx`

- [ ] Update `handleFiles` to upload files to `/api/upload` endpoint
- [ ] Show upload progress indicator
- [ ] Store returned asset IDs in component state
- [ ] Pass asset IDs to parent component via `onFilesSelected` callback
- [ ] Update `onFilesSelected` prop type to include asset IDs
- [ ] Handle upload errors and display to user
- [ ] Update `App.tsx` to collect asset IDs from UploadZone
- [ ] Include asset IDs in video generation request

**Details:**
- Upload files immediately when selected
- Store asset IDs to pass to video generation endpoint
- Show loading state during upload

---

### Task 4: Update Progress in DB When Frames Are Animated

**File:** `backend/app/phases/phase2_animatic/service.py` or `task.py`

- [ ] Update progress after each frame is generated in Phase 2
- [ ] Call `update_progress` with:
  - `video_id`
  - `status="generating_animatic"`
  - `progress` calculated based on frames completed
  - `animatic_urls` updated with each new frame URL
- [ ] Update progress after all frames are complete
- [ ] Ensure progress is queryable via status endpoint

**Details:**
- Track frame generation progress (e.g., 5 frames = 20% per frame)
- Update `animatic_urls` array as frames are generated
- Progress should be visible when checking video status

---

### Task 5: Display Phase 1 Output (Spec)

**File:** `frontend/src/pages/Dashboard.tsx` or new component

- [ ] Create UI component to display Phase 1 spec output
- [ ] Fetch video details including `spec` field from `/api/video/{video_id}`
- [ ] Display spec structure showing:
  - Template selected
  - Beats/scenes planned
  - Style specifications
  - Audio configuration
  - Color grading settings
- [ ] Show spec in a readable format (JSON viewer or structured display)
- [ ] Add section in video detail view to show "Video Specification"
- [ ] Update video status page to show spec when available

**Details:**
- Spec is stored in `video.spec` field (JSON)
- Should be visible after Phase 1 completes
- Helps verify prompt was correctly interpreted

---

### Task 6: Display Phase 2 Output (Animatic Frames)

**File:** `frontend/src/pages/Dashboard.tsx` or new component

- [ ] Create UI component to display Phase 2 animatic frames
- [ ] Fetch video details including `animatic_urls` field from `/api/video/{video_id}`
- [ ] Display animatic frames in a gallery/grid view
- [ ] Show frame thumbnails with ability to view full size
- [ ] Display frame metadata if available (beat name, shot type, etc.)
- [ ] Add section in video detail view to show "Animatic Preview"
- [ ] Update video status page to show animatic when available

**Details:**
- Animatic URLs are stored in `video.animatic_urls` field (JSON array)
- Should be visible after Phase 2 completes
- Each URL should be displayable as an image

---

## ✅ Integration Testing Checklist

Before considering integration complete:

- [ ] Can submit video generation from frontend
- [ ] Can upload assets from frontend and receive asset IDs
- [ ] Asset IDs are included in video generation request
- [ ] Video generation starts and progresses through Phase 1
- [ ] Phase 1 spec is visible in frontend after completion
- [ ] Video generation progresses through Phase 2
- [ ] Progress updates are visible in database during Phase 2
- [ ] Phase 2 animatic frames are visible in frontend after completion
- [ ] All error cases are handled gracefully
- [ ] Status endpoint returns accurate progress information

**Test Commands:**
```bash
# Start backend
cd backend && python -m uvicorn app.main:app --reload

# Start frontend
cd frontend && npm run dev

# Test upload endpoint
curl -X POST http://localhost:8000/api/upload \
  -F "file=@test-image.jpg"

# Test video generation
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "description": "Test video", "prompt": "A test video", "reference_assets": []}'

# Check status
curl http://localhost:8000/api/video/{video_id}
```

**Next:** After integration testing, proceed to Phase 3 implementation

