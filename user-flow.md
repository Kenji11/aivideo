# Video Generation with Checkpoints - User Flow

**Last Updated:** 2025-11-21
**Status:** Phase 6 Complete - Production Ready

This document describes the complete user flow for video generation with the checkpoint system, including all API endpoints, database states, and S3 storage locations.

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Manual Mode Flow (auto_continue=false)](#manual-mode-flow)
4. [YOLO Mode Flow (auto_continue=true)](#yolo-mode-flow)
5. [Editing Artifacts & Branching](#editing-artifacts--branching)
6. [API Reference](#api-reference)
7. [Database Schema](#database-schema)
8. [S3 Storage Structure](#s3-storage-structure)

---

## Overview

The checkpoint system allows users to:
- **Pause** the video generation pipeline at 4 key phases
- **Review** intermediate artifacts (spec, storyboard images, video chunks)
- **Edit** artifacts and create branches to explore different creative directions
- **Continue** from any checkpoint to the next phase
- **YOLO Mode** to run straight through without pausing

### Pipeline Phases

1. **Phase 1: Planning** - GPT-4 generates video specification (beats, style, product)
2. **Phase 2: Storyboard** - FLUX generates images for each beat
3. **Phase 3: Chunks** - Hailuo/Kling generates video chunks from images
4. **Phase 4: Refinement** - Combines chunks, adds music, exports final video

---

## Authentication

All API requests require Firebase JWT authentication.

**Login Flow:**
```bash
# User logs in via Firebase
POST https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}

# Response includes idToken
{
  "idToken": "eyJhbGci...",
  "email": "user@example.com",
  "refreshToken": "...",
  "expiresIn": "3600"
}

# Use idToken in all subsequent requests
Authorization: Bearer {idToken}
```

**User ID Extraction:**
- Backend extracts `user_id` from JWT token
- Format: `ZsYJBAsr58dmcUSykPsDsuMOv8h2`
- Used for S3 paths: `{user_id}/videos/{video_id}/...`

---

## Manual Mode Flow

User has full control at each checkpoint. Pipeline pauses after each phase.

### Step 1: Create Video Generation

**Endpoint:** `POST /api/generate`

**Request:**
```json
{
  "prompt": "luxury watch commercial with elegant transitions",
  "title": "My Video",
  "auto_continue": false,
  "model": "hailuo"
}
```

**Response:**
```json
{
  "video_id": "795c123a-359f-4d00-b1bb-6e30e187ac88",
  "status": "queued",
  "message": "Video generation started"
}
```

**Database State (video_generations):**
```sql
SELECT id, status, auto_continue, progress
FROM video_generations
WHERE id = '795c123a-359f-4d00-b1bb-6e30e187ac88';
```
```
id                                   | status  | auto_continue | progress
-------------------------------------|---------|---------------|----------
795c123a-359f-4d00-b1bb-6e30e187ac88 | queued  | false         | 0.0
```

**Redis Cache:**
```bash
GET video:{video_id}:status      # "queued"
GET video:{video_id}:progress    # "0.0"
```

---

### Step 2: Phase 1 Completes - Checkpoint Created

**Status Changes:**
- `queued` → `validating` → `PAUSED_AT_PHASE1`

**Database State (video_checkpoints):**
```sql
SELECT id, branch_name, phase_number, version, status, cost_usd
FROM video_checkpoints
WHERE video_id = '795c123a-359f-4d00-b1bb-6e30e187ac88';
```
```
id                                   | branch_name | phase_number | version | status  | cost_usd
-------------------------------------|-------------|--------------|---------|---------|----------
cp-7a231977-1ebe-44a9-98e2-a971e791 | main        | 1            | 1       | pending | 0.0008
```

**Database State (checkpoint_artifacts):**
```sql
SELECT artifact_type, artifact_key, version, s3_url
FROM checkpoint_artifacts
WHERE checkpoint_id = 'cp-7a231977-1ebe-44a9-98e2-a971e791';
```
```
artifact_type | artifact_key | version | s3_url
--------------|--------------|---------|--------
spec          | spec         | 1       | (empty - stored in metadata)
```

**S3 Storage:**
- **Nothing yet** - Phase 1 spec is stored in database metadata

---

### Step 3: Get Status (Frontend Polling)

**Endpoint:** `GET /api/status/{video_id}`

**Response:**
```json
{
  "video_id": "795c123a-359f-4d00-b1bb-6e30e187ac88",
  "status": "paused_at_phase1",
  "progress": 25.0,
  "current_phase": "phase1",
  "current_checkpoint": {
    "checkpoint_id": "cp-7a231977-1ebe-44a9-98e2-a971e791",
    "branch_name": "main",
    "phase_number": 1,
    "version": 1,
    "status": "pending",
    "created_at": "2025-11-21T08:40:18.791522Z",
    "artifacts": {
      "spec": {
        "id": "art-593ea1be-e523-42e4-bc72-0775f6c9057e",
        "artifact_type": "spec",
        "artifact_key": "spec",
        "version": 1,
        "metadata": {
          "spec": {
            "template": "luxury_showcase",
            "duration": 30,
            "beats": [
              {
                "beat_id": "hero_shot",
                "duration": 5,
                "shot_type": "close_up",
                "prompt_template": "Cinematic close-up of luxury watch..."
              },
              {
                "beat_id": "detail_showcase",
                "duration": 5,
                "shot_type": "macro",
                "prompt_template": "Extreme macro shot..."
              }
              // ... more beats
            ],
            "style": {
              "mood": "elegant",
              "lighting": "soft and dramatic",
              "aesthetic": "elegant and sophisticated",
              "color_palette": ["gold", "black", "white"]
            },
            "product": {
              "name": "luxury watch",
              "category": "premium_tech"
            }
          }
        }
      }
    }
  },
  "checkpoint_tree": [
    {
      "checkpoint": {
        "id": "cp-7a231977-1ebe-44a9-98e2-a971e791",
        "phase_number": 1,
        "branch_name": "main",
        "status": "pending"
      },
      "children": []
    }
  ],
  "active_branches": [
    {
      "branch_name": "main",
      "latest_checkpoint_id": "cp-7a231977-1ebe-44a9-98e2-a971e791",
      "phase_number": 1,
      "status": "pending",
      "can_continue": false
    }
  ]
}
```

**Frontend Actions:**
- Display spec to user (beats, style, product)
- Show "Edit Spec" button
- Show "Continue to Phase 2" button
- Display checkpoint tree visualization

---

### Step 4: Continue to Phase 2

**Endpoint:** `POST /api/video/{video_id}/continue`

**Request:**
```json
{
  "checkpoint_id": "cp-7a231977-1ebe-44a9-98e2-a971e791"
}
```

**Response:**
```json
{
  "message": "Pipeline continued",
  "next_phase": 2,
  "branch_name": "main",
  "created_new_branch": false
}
```

**Database Changes:**
```sql
-- Checkpoint approved
SELECT status, approved_at
FROM video_checkpoints
WHERE id = 'cp-7a231977-1ebe-44a9-98e2-a971e791';
```
```
status   | approved_at
---------|---------------------------
approved | 2025-11-21 08:45:29.080594+00
```

**Video Status:**
- `PAUSED_AT_PHASE1` → `GENERATING_REFERENCES` → `PAUSED_AT_PHASE2`

---

### Step 5: Phase 2 Completes - Storyboard Images

**Database State (video_checkpoints):**
```sql
SELECT id, phase_number, status, cost_usd
FROM video_checkpoints
WHERE video_id = '795c123a-359f-4d00-b1bb-6e30e187ac88'
ORDER BY phase_number;
```
```
id                                   | phase_number | status   | cost_usd
-------------------------------------|--------------|----------|----------
cp-7a231977-1ebe-44a9-98e2-a971e791 | 1            | approved | 0.0008
cp-8b342088-2fcf-55ba-a9f3-ba82f8a2 | 2            | pending  | 0.125
```

**Database State (checkpoint_artifacts):**
```sql
SELECT artifact_type, artifact_key, version, s3_key
FROM checkpoint_artifacts
WHERE checkpoint_id = 'cp-8b342088-2fcf-55ba-a9f3-ba82f8a2'
ORDER BY artifact_key;
```
```
artifact_type | artifact_key | version | s3_key
--------------|--------------|---------|------------------------------------------
beat_image    | beat_0       | 1       | {user_id}/videos/{video_id}/beat_00_v1.png
beat_image    | beat_1       | 1       | {user_id}/videos/{video_id}/beat_01_v1.png
beat_image    | beat_2       | 1       | {user_id}/videos/{video_id}/beat_02_v1.png
beat_image    | beat_3       | 1       | {user_id}/videos/{video_id}/beat_03_v1.png
beat_image    | beat_4       | 1       | {user_id}/videos/{video_id}/beat_04_v1.png
```

**S3 Storage:**
```
s3://vincent-ai-vid-storage/
  └── {user_id}/
      └── videos/
          └── {video_id}/
              ├── beat_00_v1.png  ← Storyboard images
              ├── beat_01_v1.png
              ├── beat_02_v1.png
              ├── beat_03_v1.png
              └── beat_04_v1.png
```

**Status Endpoint Response:**
```json
{
  "status": "paused_at_phase2",
  "current_checkpoint": {
    "checkpoint_id": "cp-8b342088-2fcf-55ba-a9f3-ba82f8a2",
    "phase_number": 2,
    "artifacts": {
      "beat_0": {
        "artifact_type": "beat_image",
        "s3_url": "https://vincent-ai-vid-storage.s3.amazonaws.com/.../beat_00_v1.png",
        "version": 1
      }
      // ... more beat images
    }
  }
}
```

**Frontend Actions:**
- Display storyboard images in grid
- Show "Edit Image" button for each beat
- Show "Regenerate Beat" button
- Show "Continue to Phase 3" button

---

### Step 6: Phase 3 Completes - Video Chunks

**Database State (checkpoint_artifacts):**
```
artifact_type | artifact_key | version | s3_key
--------------|--------------|---------|------------------------------------------
video_chunk   | chunk_0      | 1       | {user_id}/videos/{video_id}/chunk_00_v1.mp4
video_chunk   | chunk_1      | 1       | {user_id}/videos/{video_id}/chunk_01_v1.mp4
video_chunk   | chunk_2      | 1       | {user_id}/videos/{video_id}/chunk_02_v1.mp4
video_chunk   | chunk_3      | 1       | {user_id}/videos/{video_id}/chunk_03_v1.mp4
video_chunk   | chunk_4      | 1       | {user_id}/videos/{video_id}/chunk_04_v1.mp4
stitched      | stitched     | 1       | {user_id}/videos/{video_id}/stitched_v1.mp4
```

**S3 Storage:**
```
s3://vincent-ai-vid-storage/
  └── {user_id}/
      └── videos/
          └── {video_id}/
              ├── beat_00_v1.png
              ├── beat_01_v1.png
              ├── beat_02_v1.png
              ├── beat_03_v1.png
              ├── beat_04_v1.png
              ├── chunk_00_v1.mp4  ← Video chunks
              ├── chunk_01_v1.mp4
              ├── chunk_02_v1.mp4
              ├── chunk_03_v1.mp4
              ├── chunk_04_v1.mp4
              └── stitched_v1.mp4  ← Stitched video (no audio)
```

**Frontend Actions:**
- Display video preview (stitched video)
- Show "Regenerate Chunk" buttons
- Show "Continue to Phase 4" button

---

### Step 7: Phase 4 Completes - Final Video

**Database State:**
```
artifact_type | artifact_key | version | s3_key
--------------|--------------|---------|------------------------------------------
final_video   | final        | 1       | {user_id}/videos/{video_id}/final_v1.mp4
music         | music        | 1       | {user_id}/videos/{video_id}/music_v1.mp3
```

**S3 Storage:**
```
s3://vincent-ai-vid-storage/
  └── {user_id}/
      └── videos/
          └── {video_id}/
              ├── ... (all previous files)
              ├── final_v1.mp4    ← Final video with music
              └── music_v1.mp3    ← Background music
```

**Video Status:**
- `PAUSED_AT_PHASE4` → `COMPLETE`

**Status Endpoint Response:**
```json
{
  "status": "complete",
  "progress": 100.0,
  "final_video_url": "https://...{video_id}/final_v1.mp4"
}
```

---

## YOLO Mode Flow

User wants video to complete automatically without pausing.

### Step 1: Create Video with auto_continue=true

**Request:**
```json
{
  "prompt": "luxury watch commercial",
  "title": "My Video",
  "auto_continue": true
}
```

**Response:**
```json
{
  "video_id": "abc-123",
  "status": "queued",
  "message": "Video generation started"
}
```

### Step 2: Pipeline Runs Automatically

**Flow:**
1. Phase 1 completes → Checkpoint created → **Auto-approved** → Phase 2 dispatches
2. Phase 2 completes → Checkpoint created → **Auto-approved** → Phase 3 dispatches
3. Phase 3 completes → Checkpoint created → **Auto-approved** → Phase 4 dispatches
4. Phase 4 completes → Checkpoint created → **Auto-approved** → Status: `COMPLETE`

**Database State:**
```sql
SELECT id, phase_number, status, approved_at
FROM video_checkpoints
WHERE video_id = 'abc-123'
ORDER BY phase_number;
```
```
id      | phase_number | status   | approved_at
--------|--------------|----------|---------------------------
cp-1... | 1            | approved | 2025-11-21 08:40:18.791522
cp-2... | 2            | approved | 2025-11-21 08:42:35.123456
cp-3... | 3            | approved | 2025-11-21 08:45:12.987654
cp-4... | 4            | approved | 2025-11-21 08:48:45.654321
```

**All checkpoints:**
- Created on `main` branch (no branching in YOLO mode)
- Approved immediately with `approved_at` timestamps
- All artifacts stored in S3

**Frontend Actions:**
- Poll status endpoint
- Show progress bar
- Display final video when complete
- User can still view checkpoint tree afterwards

---

## Editing Artifacts & Branching

Users can edit artifacts at any checkpoint, which creates a new branch.

### Example: Edit Spec at Phase 1

**Endpoint:** `PATCH /api/video/{video_id}/checkpoints/{checkpoint_id}/spec`

**Request:**
```json
{
  "beats": [
    {
      "beat_id": "hero_shot",
      "duration": 10,
      "shot_type": "wide"
    }
  ],
  "style": {
    "mood": "dramatic"
  }
}
```

**Response:**
```json
{
  "artifact_id": "art-593ea1be-...",
  "version": 2
}
```

**Database State:**
```sql
SELECT artifact_type, version, metadata
FROM checkpoint_artifacts
WHERE checkpoint_id = 'cp-7a231977-...'
ORDER BY version DESC;
```
```
artifact_type | version | metadata
--------------|---------|------------------
spec          | 2       | { updated spec }
spec          | 1       | { original spec }
```

**Note:** Artifacts are versioned **in-place**. Only one record per (checkpoint_id, artifact_type, artifact_key), but version increments.

---

### Continue After Edit - Branching

**Endpoint:** `POST /api/video/{video_id}/continue`

**Request:**
```json
{
  "checkpoint_id": "cp-7a231977-1ebe-44a9-98e2-a971e791"
}
```

**Response:**
```json
{
  "message": "Pipeline continued",
  "next_phase": 2,
  "branch_name": "main-1",
  "created_new_branch": true
}
```

**Database State:**
```sql
SELECT id, branch_name, phase_number, parent_checkpoint_id
FROM video_checkpoints
WHERE video_id = '795c123a-...'
ORDER BY created_at;
```
```
id         | branch_name | phase_number | parent_checkpoint_id
-----------|-------------|--------------|---------------------
cp-1...    | main        | 1            | NULL
cp-2...    | main-1      | 2            | cp-1...
```

**Branch Naming:**
- `main` → `main-1` (first branch from main)
- `main-1` → `main-1-1` (branch from main-1)
- `main-1` → `main-1-2` (second branch from main-1)
- Hierarchical structure for exploring different creative directions

---

### Upload Replacement Image (Phase 2)

**Endpoint:** `POST /api/video/{video_id}/checkpoints/{checkpoint_id}/upload-image`

**Request (multipart/form-data):**
```
beat_index: 3
image: [file upload]
```

**Response:**
```json
{
  "artifact_id": "art-new-...",
  "s3_url": "https://.../beat_03_v2.png",
  "version": 2
}
```

**S3 Storage:**
```
s3://vincent-ai-vid-storage/
  └── {user_id}/
      └── videos/
          └── {video_id}/
              ├── beat_03_v1.png  ← Original
              └── beat_03_v2.png  ← User uploaded
```

---

### Regenerate Beat Image (Phase 2)

**Endpoint:** `POST /api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-beat`

**Request:**
```json
{
  "beat_index": 2,
  "prompt_override": "dramatic close-up with moody lighting"
}
```

**Response:**
```json
{
  "artifact_id": "art-new-...",
  "s3_url": "https://.../beat_02_v2.png",
  "version": 2
}
```

**Cost:** ~$0.025 per image (FLUX Dev)

---

### Regenerate Video Chunk (Phase 3)

**Endpoint:** `POST /api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-chunk`

**Request:**
```json
{
  "chunk_index": 1,
  "model_override": "kling"
}
```

**Response:**
```json
{
  "artifact_id": "art-new-...",
  "s3_url": "https://.../chunk_01_v2.mp4",
  "version": 2
}
```

---

## API Reference

### Video Generation

#### Create Video
```http
POST /api/generate
Authorization: Bearer {idToken}
Content-Type: application/json

{
  "prompt": string (required, 10-1000 chars),
  "title": string (optional, max 200 chars),
  "description": string (optional, max 2000 chars),
  "reference_assets": string[] (optional, asset IDs),
  "model": string (optional, default: "hailuo"),
  "auto_continue": boolean (optional, default: false)
}

Response: 200 OK
{
  "video_id": string,
  "status": "queued",
  "message": string
}
```

#### Get Video Status
```http
GET /api/status/{video_id}
Authorization: Bearer {idToken}

Response: 200 OK
{
  "video_id": string,
  "status": VideoStatus,
  "progress": float,
  "current_phase": string,
  "current_checkpoint": CheckpointInfo | null,
  "checkpoint_tree": CheckpointTreeNode[],
  "active_branches": BranchInfo[],
  "final_video_url": string | null,
  "error": string | null
}
```

#### Stream Video Status (SSE)
```http
GET /api/status/{video_id}/stream
Authorization: Bearer {idToken}

Response: text/event-stream
event: status_update
data: { ...StatusResponse }

event: checkpoint_created
data: {
  "checkpoint_id": string,
  "phase": number,
  "branch": string
}
```

### Checkpoints

#### List Video Checkpoints
```http
GET /api/video/{video_id}/checkpoints
Authorization: Bearer {idToken}

Response: 200 OK
{
  "checkpoints": CheckpointResponse[],
  "tree": CheckpointTreeNode[]
}
```

#### Get Checkpoint Details
```http
GET /api/video/{video_id}/checkpoints/{checkpoint_id}
Authorization: Bearer {idToken}

Response: 200 OK
{
  "checkpoint": CheckpointResponse,
  "artifacts": ArtifactResponse[]
}
```

#### Get Current Checkpoint
```http
GET /api/video/{video_id}/checkpoints/current
Authorization: Bearer {idToken}

Response: 200 OK
{
  "checkpoint": CheckpointResponse | null
}
```

#### List Active Branches
```http
GET /api/video/{video_id}/branches
Authorization: Bearer {idToken}

Response: 200 OK
{
  "branches": BranchInfo[]
}
```

#### Continue Pipeline
```http
POST /api/video/{video_id}/continue
Authorization: Bearer {idToken}
Content-Type: application/json

{
  "checkpoint_id": string
}

Response: 200 OK
{
  "message": string,
  "next_phase": number,
  "branch_name": string,
  "created_new_branch": boolean
}
```

#### Get Checkpoint Tree
```http
GET /api/video/{video_id}/checkpoints/tree
Authorization: Bearer {idToken}

Response: 200 OK
{
  "tree": CheckpointTreeNode[]
}
```

### Artifact Editing

#### Edit Spec (Phase 1)
```http
PATCH /api/video/{video_id}/checkpoints/{checkpoint_id}/spec
Authorization: Bearer {idToken}
Content-Type: application/json

{
  "beats": Beat[] (optional),
  "style": Style (optional),
  "product": Product (optional),
  "audio": Audio (optional)
}

Response: 200 OK
{
  "artifact_id": string,
  "version": number
}
```

#### Upload Replacement Image (Phase 2)
```http
POST /api/video/{video_id}/checkpoints/{checkpoint_id}/upload-image
Authorization: Bearer {idToken}
Content-Type: multipart/form-data

beat_index: number
image: File

Response: 200 OK
{
  "artifact_id": string,
  "s3_url": string,
  "version": number
}
```

#### Regenerate Beat Image (Phase 2)
```http
POST /api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-beat
Authorization: Bearer {idToken}
Content-Type: application/json

{
  "beat_index": number,
  "prompt_override": string (optional)
}

Response: 200 OK
{
  "artifact_id": string,
  "s3_url": string,
  "version": number
}
```

#### Regenerate Video Chunk (Phase 3)
```http
POST /api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-chunk
Authorization: Bearer {idToken}
Content-Type: application/json

{
  "chunk_index": number,
  "model_override": string (optional, "hailuo"|"kling"|"veo")
}

Response: 200 OK
{
  "artifact_id": string,
  "s3_url": string,
  "version": number
}
```

---

## Database Schema

### video_generations
```sql
CREATE TABLE video_generations (
  id VARCHAR PRIMARY KEY,
  user_id VARCHAR NOT NULL,
  title VARCHAR NOT NULL,
  description VARCHAR,
  prompt VARCHAR NOT NULL,
  prompt_validated VARCHAR,
  reference_assets JSON DEFAULT '[]',
  spec JSON,
  template VARCHAR,
  status VideoStatus DEFAULT 'queued',
  progress FLOAT DEFAULT 0.0,
  current_phase VARCHAR,
  error_message VARCHAR,
  auto_continue BOOLEAN DEFAULT FALSE,  -- YOLO mode
  cost_usd FLOAT DEFAULT 0.0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);
```

### video_checkpoints
```sql
CREATE TABLE video_checkpoints (
  id VARCHAR PRIMARY KEY,
  video_id VARCHAR NOT NULL REFERENCES video_generations(id) ON DELETE CASCADE,
  branch_name VARCHAR NOT NULL,
  phase_number INTEGER NOT NULL CHECK (phase_number IN (1, 2, 3, 4)),
  version INTEGER NOT NULL CHECK (version > 0),
  parent_checkpoint_id VARCHAR REFERENCES video_checkpoints(id) ON DELETE SET NULL,
  status VARCHAR NOT NULL CHECK (status IN ('pending', 'approved', 'abandoned')),
  approved_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  phase_output JSONB NOT NULL,
  cost_usd DECIMAL(10, 4) NOT NULL DEFAULT 0,
  user_id VARCHAR NOT NULL,
  edit_description TEXT,
  UNIQUE(video_id, branch_name, phase_number, version)
);
```

### checkpoint_artifacts
```sql
CREATE TABLE checkpoint_artifacts (
  id VARCHAR PRIMARY KEY,
  checkpoint_id VARCHAR NOT NULL REFERENCES video_checkpoints(id) ON DELETE CASCADE,
  artifact_type VARCHAR NOT NULL,
  artifact_key VARCHAR NOT NULL,
  s3_url VARCHAR NOT NULL,
  s3_key VARCHAR NOT NULL,
  version INTEGER NOT NULL CHECK (version > 0),
  parent_artifact_id VARCHAR REFERENCES checkpoint_artifacts(id) ON DELETE SET NULL,
  metadata JSONB,
  file_size_bytes BIGINT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(checkpoint_id, artifact_type, artifact_key)
);
```

---

## S3 Storage Structure

### Bucket: `vincent-ai-vid-storage`

```
{user_id}/
  └── videos/
      └── {video_id}/
          ├── beat_00_v1.png       # Phase 2: Storyboard images
          ├── beat_01_v1.png
          ├── beat_02_v1.png
          ├── beat_02_v2.png       # Edited/regenerated version
          ├── beat_03_v1.png
          ├── beat_04_v1.png
          ├── chunk_00_v1.mp4      # Phase 3: Video chunks
          ├── chunk_01_v1.mp4
          ├── chunk_02_v1.mp4
          ├── chunk_03_v1.mp4
          ├── chunk_04_v1.mp4
          ├── stitched_v1.mp4      # Phase 3: Combined chunks (no audio)
          ├── music_v1.mp3         # Phase 4: Background music
          └── final_v1.mp4         # Phase 4: Final video with audio
```

### File Naming Convention

- **Format:** `{artifact_type}_{index}_v{version}.{ext}`
- **Examples:**
  - `beat_00_v1.png` - First storyboard image, version 1
  - `beat_00_v2.png` - First storyboard image, version 2 (edited)
  - `chunk_03_v1.mp4` - Fourth video chunk, version 1
  - `stitched_v1.mp4` - Stitched video, version 1
  - `final_v1.mp4` - Final video, version 1

### Versioning Strategy

- **Application-level versioning** (not S3 native versioning)
- Version increments when artifact is edited/regenerated
- Old versions remain in S3 (no deletion)
- Database tracks which version is current for each checkpoint

---

## Error Handling

### Common Error Responses

```json
// 401 Unauthorized
{
  "detail": "Invalid authentication credentials"
}

// 403 Forbidden
{
  "detail": "Not authorized to access this resource"
}

// 404 Not Found
{
  "detail": "Video not found"
}

// 400 Bad Request
{
  "detail": "Can only edit spec at Phase 1"
}

// 500 Internal Server Error
{
  "detail": "Failed to generate storyboard: Replicate API error"
}
```

### Status Values

```typescript
type VideoStatus =
  | "queued"
  | "validating"
  | "PAUSED_AT_PHASE1"
  | "generating_animatic"
  | "generating_references"
  | "PAUSED_AT_PHASE2"
  | "generating_chunks"
  | "PAUSED_AT_PHASE3"
  | "refining"
  | "PAUSED_AT_PHASE4"
  | "exporting"
  | "COMPLETE"
  | "FAILED";
```

---

## Cost Estimates

### Per Video (Manual Mode - No Edits)

- **Phase 1 (Planning):** ~$0.001 (GPT-4o-mini)
- **Phase 2 (Storyboard):** ~$0.125 (FLUX Dev: $0.025 × 5 images)
- **Phase 3 (Chunks):** ~$1.00 (Hailuo: ~$0.20 × 5 chunks)
- **Phase 4 (Refinement):** ~$0.10 (Music generation + processing)

**Total:** ~$1.23 per 30-second video

### Additional Costs

- **Regenerate Beat Image:** ~$0.025 per image
- **Regenerate Video Chunk:** ~$0.20 per chunk
- **Branching:** Same costs as original generation for new branch

---

## Frontend Integration Checklist

### Phase 1 (Planning)
- [ ] Display spec to user (beats, style, product)
- [ ] Show "Edit Spec" modal
- [ ] Show "Continue to Phase 2" button
- [ ] Display cost estimate

### Phase 2 (Storyboard)
- [ ] Display storyboard images in grid layout
- [ ] Show "Upload Replacement" button per beat
- [ ] Show "Regenerate Beat" button per beat
- [ ] Show image version history
- [ ] Show "Continue to Phase 3" button

### Phase 3 (Chunks)
- [ ] Display video preview (stitched video)
- [ ] Show "Regenerate Chunk" button per chunk
- [ ] Show chunk version history
- [ ] Show "Continue to Phase 4" button

### Phase 4 (Final)
- [ ] Display final video player
- [ ] Show download button
- [ ] Show share options
- [ ] Display total cost

### Checkpoint Tree
- [ ] Visualize branching structure
- [ ] Show checkpoint status (pending/approved)
- [ ] Allow navigation between branches
- [ ] Highlight current branch

### Real-time Updates
- [ ] Implement SSE connection for live status updates
- [ ] Show progress bar during generation
- [ ] Display notifications for checkpoint creation
- [ ] Handle reconnection on disconnect

---

## Notes

- **Redis TTL:** 60 minutes (status, progress, metadata)
- **S3 Presigned URLs:** Generated on-demand, expire after 1 hour
- **Database Indexes:** Optimized for video_id, branch_name, checkpoint_id queries
- **Concurrency:** Sequential phase execution (no parallel branches)
- **Testing:** All 65 tests passing (Phases 1-6 complete)

---

**End of User Flow Documentation**
