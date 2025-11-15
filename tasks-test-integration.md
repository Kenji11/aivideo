# Phase 1 & 2 Integration Testing Tasks

**Owner:** Person handling integration testing  
**Goal:** Make Phase 1 and Phase 2 testable end-to-end

---

## PR: Phase 1 & 2 Integration Testing

### Task 1: Connect Video Gen Page to Video Gen Endpoint

**File:** `frontend/src/App.tsx`

- [x] Update `handleSubmit` function to call `/api/generate` endpoint
- [x] Send `title`, `description`, `prompt`, and `reference_assets` in request body
- [x] Handle response with `video_id` and store it in state
- [x] Update UI to show processing state after successful submission
- [x] Add error handling for failed API calls
- [x] Display error messages to user if generation fails to start

**Details:**
- Endpoint: `POST /api/generate`
- Request body should match `GenerateRequest` schema
- Response will contain `video_id` to track progress

---

### Task 2: Create Asset Upload Endpoint

**File:** `backend/app/api/upload.py` (new file)

- [x] Create new API router for upload endpoints
- [x] Implement `POST /api/upload` endpoint
- [x] Accept multipart/form-data with file(s)
- [x] Validate file types (images, videos, PDFs)
- [x] Upload files to S3 using S3Client
- [x] Create Asset record in database with:
  - `id` (UUID)
  - `s3_key` and `s3_url`
  - `asset_type` (IMAGE, VIDEO, AUDIO)
  - `source` (USER_UPLOAD)
  - `file_name`, `file_size_bytes`, `mime_type`
  - `asset_metadata` (dimensions, duration if applicable)
- [x] Return asset ID(s) in response
- [x] Add error handling for upload failures
- [x] Register router in `backend/app/main.py`

**Details:**
- Use FastAPI's `UploadFile` for file handling
- Store files in S3 with path: `assets/{user_id}/{asset_id}/{filename}`
- Return list of asset IDs for multiple file uploads

---

### Task 3: Connect Frontend Asset Upload to Upload Endpoint

**File:** `frontend/src/components/UploadZone.tsx`

- [x] Update `handleFiles` to upload files to `/api/upload` endpoint
- [x] Show upload progress indicator
- [x] Store returned asset IDs in component state
- [x] Pass asset IDs to parent component via `onAssetsUploaded` callback
- [x] Update callback prop type to include asset IDs
- [x] Handle upload errors and display to user
- [x] Update `App.tsx` to collect asset IDs from UploadZone
- [x] Include asset IDs in video generation request
- [x] Create `GET /api/assets` endpoint in backend
- [x] Accept optional `user_id` query parameter (defaults to MOCK_USER_ID)
- [x] Query Asset table filtered by user_id
- [x] Return list of assets with metadata (asset_id, filename, asset_type, file_size_bytes, s3_url, created_at)
- [x] Add API function to fetch assets in `frontend/src/lib/api.ts`
- [x] Create component or section to display uploaded assets on video gen page
- [x] Fetch assets on page load using GET `/api/assets`
- [x] Display assets in a list/table format with checkboxes
- [x] Allow selecting/deselecting assets via checkboxes
- [x] Store selected asset IDs in state
- [x] Include selected asset IDs in video generation request
- [x] Add "Refresh Assets" button to reload list
- [x] Show loading state while fetching assets
- [x] Handle empty state (no assets uploaded yet)

**Details:**
- Upload files immediately when selected
- Store asset IDs to pass to video generation endpoint
- Show loading state during upload
- Backend endpoint: `GET /api/assets?user_id={user_id}`
- Frontend should display previously uploaded assets with selection checkboxes

---

### Task 4: Update Progress in DB When Frames Are Animated

**File:** `backend/app/phases/phase2_animatic/service.py` or `task.py`

- [x] Update progress after each frame is generated in Phase 2
- [x] Call `update_progress` with:
  - `video_id`
  - `status="generating_animatic"`
  - `progress` calculated based on frames completed
  - `animatic_urls` updated with each new frame URL
- [x] Update progress after all frames are complete
- [x] Ensure progress is queryable via status endpoint
- [x] Add logging for Phase 1 completion
- [x] Add logging for Phase 2 completion

**Details:**
- Track frame generation progress (e.g., 5 frames = 20% per frame)
- Update `animatic_urls` array as frames are generated
- Progress should be visible when checking video status
- Progress updates from 25% to 50% during Phase 2 (distributed across frames)
- Phase completion logs include template/beats info, cost, and duration

---

## ✅ Integration Testing Checklist

Before considering integration complete:

- [x] Can submit video generation from frontend
- [x] Can upload assets from frontend and receive asset IDs
- [x] Asset IDs are included in video generation request
- [x] Video generation starts and progresses through Phase 1
- [x] Video generation progresses through Phase 2
- [x] Progress updates are visible in database during Phase 2
- [x] All error cases are handled gracefully
- [x] Status endpoint returns accurate progress information

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

---

### Task 9: My Projects Page Should Fetch All Videos

**File:** `frontend/src/App.tsx`

- [x] Add API function to fetch all videos in `frontend/src/lib/api.ts`
- [x] Fetch videos from `/api/videos` endpoint when "My Projects" page loads
- [x] Map backend video data to Project format (or update Project type)
- [x] Display videos in the projects grid using ProjectCard component
- [x] Show loading state while fetching videos
- [x] Handle error state if fetch fails
- [x] Update projects state with fetched videos
- [x] Refresh projects list when returning to "My Projects" page

**Details:**
- Endpoint: `GET /api/videos` (already exists)
- Returns list of videos with: video_id, title, status, progress, final_video_url, cost_usd, created_at, completed_at
- Should filter by user_id (using MOCK_USER_ID for now)
- Replace or supplement existing Supabase projects data
- Status mapping: backend statuses are mapped to Project status enum (pending/processing/completed/failed)
- Added refresh button to manually reload projects
- Videos are automatically fetched when navigating to "My Projects" page

