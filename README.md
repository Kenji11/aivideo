# AI Video Generation Pipeline

An end-to-end AI-powered system that transforms natural language prompts into professional video advertisements through a 4-phase pipeline with interactive checkpoints.

## 🎯 Overview

This system generates 30-second video advertisements from text prompts using:
- **GPT-4** for intelligent planning and beat composition
- **FLUX Dev** for storyboard image generation
- **Hailuo/Kling/Veo** for video chunk generation
- **MusicGen** for background music
- **FFmpeg** for video stitching and audio integration

### Key Features
- ✅ **Interactive Checkpoints**: Pause and review at each phase
- ✅ **Artifact Editing**: Edit specs, regenerate images, modify chunks
- ✅ **Creative Branching**: Explore different directions with branch trees
- ✅ **YOLO Mode**: Auto-continue for hands-free generation
- ✅ **Dynamic Storyboard Mapping**: Adapts to any number of storyboard images
- ✅ **Temporal Coherence**: Last-frame continuation ensures smooth transitions
- ✅ **Multiple Models**: Support for Hailuo, Kling, Veo, and other video models
- ✅ **Real-time Updates**: Live progress tracking via SSE streaming
- ✅ **Cost Tracking**: Per-phase and per-artifact cost monitoring
- ✅ **Version Control**: Artifact versioning with parent-child tracking

## 🏗️ Architecture

### System Components

```
Frontend (React) ← SSE Stream ← FastAPI ← Redis (Cache)
        ↓                          ↓           ↓
    HTTP API  →  Checkpoint API → PostgreSQL (Checkpoints, Artifacts)
                      ↓                        ↓
               Celery Workers  ←  Phase Context & Branching
                      ↓
              AI Services (GPT-4, FLUX, Hailuo/Kling/Veo)
                      ↓
              S3 Storage (Versioned Artifacts)
```

### Pipeline Flow

#### Manual Mode (auto_continue=false)
Pipeline pauses after each phase for user review and editing.

1. **Phase 1: Planning** (~7s)
   - GPT-4 analyzes prompt
   - Composes beat sequence from 15-beat library
   - Creates complete video specification
   - **Checkpoint created** → Status: `PAUSED_AT_PHASE1`
   - User can edit spec before continuing

2. **Phase 2: Storyboard** (~8s per image)
   - Generates 1 FLUX Dev image per beat
   - Uploads to S3 with versioned paths
   - Creates artifact records in database
   - **Checkpoint created** → Status: `PAUSED_AT_PHASE2`
   - User can upload custom images or regenerate beats

3. **Phase 3: Chunks** (~45s per chunk)
   - Dynamically maps beats to chunks
   - Uses storyboard images at beat boundaries
   - Uses last-frame continuation within beats
   - Stitches chunks with FFmpeg
   - **Checkpoint created** → Status: `PAUSED_AT_PHASE3`
   - User can regenerate individual chunks

4. **Phase 4: Refinement** (~2 min, or skipped for Veo)
   - Generates background music
   - Combines video + audio
   - Uploads final video
   - **Checkpoint created** → Status: `COMPLETE`

#### YOLO Mode (auto_continue=true)
Pipeline runs straight through without pausing. All checkpoints are auto-approved.

### Checkpoint System

**Database Tables:**
- `video_checkpoints`: Checkpoint metadata with branching relationships
- `checkpoint_artifacts`: Individual artifacts with version tracking

**S3 Structure:**
```
{user_id}/videos/{video_id}/
  ├── beat_00_v1.png      # Storyboard images
  ├── beat_00_v2.png      # Edited version
  ├── chunk_00_v1.mp4     # Video chunks
  ├── stitched_v1.mp4     # Combined chunks
  ├── music_v1.mp3        # Background music
  └── final_v1.mp4        # Final video with audio
```

**Branching:**
- Editing artifacts creates new branches (main → main-1 → main-1-1)
- Tree structure tracks all creative explorations
- Each branch maintains independent artifact versions

### Generation Time

**30-second video (Manual Mode):**
- **Total**: ~8-10 minutes (hailuo) or ~6-8 minutes (Veo)
- **Breakdown**:
  - Phase 1: ~7 seconds → **Pause for review**
  - Phase 2: ~40 seconds (5 images × 8s) → **Pause for review**
  - Phase 3: ~5.5 minutes (5 chunks × 45s + stitching) → **Pause for review**
  - Phase 4: ~2 minutes (music + audio integration) → **Complete**

**30-second video (YOLO Mode):**
Same as Manual Mode but runs continuously without pauses.

### Cost per Video

**30-second video (Manual Mode - No Edits):**
- Phase 1 (Planning): ~$0.001 (GPT-4o-mini)
- Phase 2 (Storyboard): ~$0.125 (5 images × $0.025 FLUX Dev)
- Phase 3 (Chunks): ~$1.00 (5 chunks × $0.20 Hailuo)
- Phase 4 (Refinement): ~$0.10 (music generation)
- **Total**: ~$1.23 per video

**Additional Costs for Editing:**
- Regenerate beat image: ~$0.025 per image
- Regenerate video chunk: ~$0.20 per chunk (Hailuo)
- Branching: Same costs as original generation for new branch

## 🚀 Quick Start

### Prerequisites

```bash
# Required software
- Docker Desktop
- Python 3.11+
- Node.js 18+
- AWS CLI (for S3 access)
```

### Local Development

```bash
# Clone repository
git clone <repo-url>
cd aivideo

# Backend setup
cd backend
cp .env.example .env
# Edit .env with your API keys:
# - REPLICATE_API_TOKEN
# - OPENAI_API_KEY
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - S3_BUCKET
# - DATABASE_URL
# - REDIS_URL

# Start services with Docker Compose
docker-compose up -d

# Frontend setup
cd ../frontend
npm install
npm run dev

# Access services
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:5173
```

### Generate Your First Video

```bash
# Via API - Manual Mode (with checkpoints)
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {firebase_token}" \
  -d '{
    "prompt": "Create a 30-second Nike sneaker ad, energetic style",
    "title": "Nike Ad",
    "model": "hailuo",
    "auto_continue": false
  }'

# Response: {"video_id": "...", "status": "queued"}

# Check status (includes checkpoint info)
curl -H "Authorization: Bearer {firebase_token}" \
  http://localhost:8000/api/status/{video_id}

# Continue from checkpoint after review
curl -X POST http://localhost:8000/api/video/{video_id}/continue \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {firebase_token}" \
  -d '{"checkpoint_id": "cp-..."}'

# Via API - YOLO Mode (auto-continue)
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {firebase_token}" \
  -d '{
    "prompt": "Create a 30-second Nike sneaker ad, energetic style",
    "title": "Nike Ad",
    "model": "hailuo",
    "auto_continue": true
  }'
```

## 📁 Project Structure

```
aivideo/
├── backend/
│   ├── app/
│   │   ├── api/              # REST API endpoints
│   │   │   ├── generate.py
│   │   │   ├── status.py
│   │   │   ├── checkpoints.py     # NEW: Checkpoint API
│   │   │   └── upload.py
│   │   ├── orchestrator/      # Pipeline orchestration
│   │   ├── phases/           # Phase implementations
│   │   │   ├── phase1_validate/
│   │   │   ├── phase2_storyboard/
│   │   │   ├── phase3_chunks/
│   │   │   └── phase4_refine/
│   │   ├── database/         # Database queries
│   │   │   └── checkpoint_queries.py  # NEW: Checkpoint DB ops
│   │   ├── services/         # External service clients
│   │   └── common/           # Shared code
│   ├── migrations/
│   │   └── 004_add_checkpoints.sql   # NEW: Checkpoint schema
│   ├── docker-compose.yml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   │   ├── CheckpointCard.tsx      # NEW
│   │   │   ├── CheckpointTree.tsx      # NEW
│   │   │   ├── ArtifactEditor.tsx      # NEW
│   │   │   └── BranchSelector.tsx      # NEW
│   │   ├── pages/           # Page components
│   │   │   ├── VideoStatus.tsx    # Updated with checkpoints
│   │   │   └── UploadVideo.tsx    # Updated with YOLO toggle
│   │   └── lib/             # Utilities
│   │       ├── api.ts             # Updated with checkpoint methods
│   │       └── useVideoStatusStream.ts  # SSE with checkpoint events
│   └── package.json
├── ARCHITECTURE.md           # Detailed architecture docs
├── user-flow.md             # NEW: Complete checkpoint user flow
├── implementation-summary-frontend-checkpoints.md  # NEW
├── thoughts/shared/plans/   # Implementation plans
│   └── 2025-11-20-checkpoint-feature.md
└── README.md
```

## 🔧 Configuration

### Environment Variables

```bash
# Backend (.env)
DATABASE_URL=postgresql://user:pass@localhost:5432/videogen
REDIS_URL=redis://localhost:6379/0
REPLICATE_API_TOKEN=r8_...
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=ai-video-assets-dev
AWS_REGION=us-east-2
```

### Model Selection

Default model is `hailuo`. To change:

```python
# backend/app/phases/phase3_chunks/model_config.py
DEFAULT_MODEL = 'hailuo'  # Change to 'veo_fast', 'veo', etc.
```

Available models:
- `hailuo`: Hailuo 2.3 Fast (default, 5s chunks, $0.04/chunk)
- `veo_fast`: Google Veo 3.1 Fast (5s chunks, native audio)
- `veo`: Google Veo 3.1 (5s chunks, native audio)
- `wan`: Wan 2.1 (5s chunks, $0.45/chunk)
- And more...

## 📊 API Endpoints

### Video Generation

#### Generate Video
```http
POST /api/generate
Authorization: Bearer {firebase_token}
Content-Type: application/json

{
  "prompt": "Create a 30-second Nike ad",
  "title": "Nike Ad",
  "description": "Energetic lifestyle ad",
  "model": "hailuo",
  "auto_continue": false,
  "reference_assets": ["asset_id_1", "asset_id_2"]
}

Response: {
  "video_id": "uuid",
  "status": "queued",
  "message": "Video generation started"
}
```

#### Get Status (with Checkpoint Info)
```http
GET /api/status/{video_id}
Authorization: Bearer {firebase_token}

Response: {
  "video_id": "uuid",
  "status": "paused_at_phase2",
  "progress": 50.0,
  "current_phase": "phase2",
  "current_checkpoint": {
    "checkpoint_id": "cp-...",
    "branch_name": "main",
    "phase_number": 2,
    "version": 1,
    "status": "pending",
    "artifacts": {
      "beat_0": {"s3_url": "...", "version": 1},
      "beat_1": {"s3_url": "...", "version": 1}
    }
  },
  "checkpoint_tree": [...],
  "active_branches": [...],
  "final_video_url": null,
  "cost_usd": 0.13
}
```

#### Stream Status (SSE)
```http
GET /api/status/{video_id}/stream
Authorization: Bearer {firebase_token}

Events:
  event: status_update
  data: {...status response...}

  event: checkpoint_created
  data: {"checkpoint_id": "...", "phase": 2, "branch": "main"}
```

### Checkpoint Management

#### List Checkpoints
```http
GET /api/video/{video_id}/checkpoints
Authorization: Bearer {firebase_token}

Response: {
  "checkpoints": [...],
  "tree": [...]
}
```

#### Get Checkpoint Details
```http
GET /api/video/{video_id}/checkpoints/{checkpoint_id}
Authorization: Bearer {firebase_token}

Response: {
  "checkpoint": {...},
  "artifacts": [...]
}
```

#### Continue Pipeline
```http
POST /api/video/{video_id}/continue
Authorization: Bearer {firebase_token}
Content-Type: application/json

{
  "checkpoint_id": "cp-..."
}

Response: {
  "message": "Pipeline continued",
  "next_phase": 3,
  "branch_name": "main",
  "created_new_branch": false
}
```

#### Get Checkpoint Tree
```http
GET /api/video/{video_id}/checkpoints/tree
Authorization: Bearer {firebase_token}

Response: {
  "tree": [
    {
      "checkpoint": {"id": "cp-1", "phase_number": 1, ...},
      "children": [
        {"checkpoint": {"id": "cp-2", "phase_number": 2, ...}, "children": []}
      ]
    }
  ]
}
```

### Artifact Editing

#### Edit Spec (Phase 1)
```http
PATCH /api/video/{video_id}/checkpoints/{checkpoint_id}/spec
Authorization: Bearer {firebase_token}
Content-Type: application/json

{
  "beats": [...],
  "style": {...}
}

Response: {
  "artifact_id": "art-...",
  "version": 2
}
```

#### Upload Replacement Image (Phase 2)
```http
POST /api/video/{video_id}/checkpoints/{checkpoint_id}/upload-image
Authorization: Bearer {firebase_token}
Content-Type: multipart/form-data

beat_index: 2
image: [file]

Response: {
  "artifact_id": "art-...",
  "s3_url": "https://...",
  "version": 2
}
```

#### Regenerate Beat (Phase 2)
```http
POST /api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-beat
Authorization: Bearer {firebase_token}
Content-Type: application/json

{
  "beat_index": 2,
  "prompt_override": "optional custom prompt"
}

Response: {
  "artifact_id": "art-...",
  "s3_url": "https://...",
  "version": 2
}
```

#### Regenerate Chunk (Phase 3)
```http
POST /api/video/{video_id}/checkpoints/{checkpoint_id}/regenerate-chunk
Authorization: Bearer {firebase_token}
Content-Type: application/json

{
  "chunk_index": 3,
  "model_override": "kling"
}

Response: {
  "artifact_id": "art-...",
  "s3_url": "https://...",
  "version": 2
}
```

### Upload Assets
```http
POST /api/upload
Authorization: Bearer {firebase_token}
Content-Type: multipart/form-data

files: [file1, file2, ...]

Response: {
  "asset_ids": ["uuid1", "uuid2", ...]
}
```

## 🎬 Checkpoint System Features

### Visual Flow

```
┌─────────────────────────────────────────────────────────────┐
│  User: "Create a luxury watch commercial"                  │
│  Mode: Manual (auto_continue = false)                      │
└─────────────────────────────────────────────────────────────┘
                         ↓
         ┌───────────────────────────┐
         │   Phase 1: Planning       │
         │   GPT-4 generates spec    │
         │   Cost: $0.001            │
         └───────────────────────────┘
                         ↓
              🚦 CHECKPOINT 1 (PAUSED)
                 User Reviews:
                 ✓ 5 beats defined
                 ✓ Luxury style
                 ✓ 30-second duration

         Options: [Edit Spec] [Continue]
                         ↓
                   [Continue]
                         ↓
         ┌───────────────────────────┐
         │   Phase 2: Storyboard     │
         │   FLUX generates 5 images │
         │   Cost: $0.125            │
         └───────────────────────────┘
                         ↓
              🚦 CHECKPOINT 2 (PAUSED)
                 User Reviews:
                 🖼️ beat_00_v1.png
                 🖼️ beat_01_v1.png
                 🖼️ beat_02_v1.png ← Wants to regenerate
                 🖼️ beat_03_v1.png
                 🖼️ beat_04_v1.png

         User: [Regenerate Beat 2]
                         ↓
         New: beat_02_v2.png created
         Branch: main → main-1
                         ↓
                   [Continue]
                         ↓
         ┌───────────────────────────┐
         │   Phase 3: Chunks         │
         │   Hailuo generates video  │
         │   Cost: $1.00             │
         │   Branch: main-1          │
         └───────────────────────────┘
                         ↓
              🚦 CHECKPOINT 3 (PAUSED)
                 User Reviews:
                 🎬 stitched_v1.mp4

         Options: [Regenerate Chunks] [Continue]
                         ↓
                   [Continue]
                         ↓
         ┌───────────────────────────┐
         │   Phase 4: Refinement     │
         │   Add music & finalize    │
         │   Cost: $0.10             │
         └───────────────────────────┘
                         ↓
                   ✅ COMPLETE
              final_v1.mp4 ready!
              Total cost: $1.23
```

### Manual Mode Workflow

1. **Phase 1: Review Video Specification**
   - View AI-generated beats, style, and product details
   - Edit spec if needed (creates new branch)
   - Click "Continue" to proceed to Phase 2

2. **Phase 2: Review Storyboard**
   - View AI-generated images in grid layout
   - Upload custom images for specific beats
   - Regenerate individual beats with custom prompts
   - Click "Continue" to proceed to Phase 3 (creates branch if edited)

3. **Phase 3: Review Video Chunks**
   - View stitched video preview
   - Regenerate individual chunks with different models
   - Click "Continue" to proceed to Phase 4 (creates branch if edited)

4. **Phase 4: Final Video**
   - View final video with music
   - Download and share

### Branching System

**Automatic Branch Creation:**
- Continuing from an edited checkpoint creates a new branch
- Branch naming: `main` → `main-1` → `main-1-1` → `main-1-2`
- Tree visualization shows all branches and their relationships
- Each branch maintains independent artifact versions

**Example Workflow:**
```
main (Phase 1, original spec)
 ├─ main (Phase 2, 5 images)
 │   ├─ main (Phase 3, 5 chunks) → Complete
 │   └─ main-1 (Phase 3, regenerated chunk 2)
 │       └─ main-1 (Phase 4) → Complete
 └─ main-2 (Phase 2, edited spec + new images)
     └─ main-2 (Phase 3) → In Progress
```

### Frontend Components

- **CheckpointCard**: Displays checkpoint with phase-specific artifacts
- **CheckpointTree**: Recursive tree visualization with indentation
- **ArtifactEditor**: Modal dialog for editing artifacts at each phase
- **BranchSelector**: Dropdown for viewing/switching branches (future feature)

### Real-time Updates

- **SSE Streaming**: Live status updates and checkpoint events
- **Automatic UI Refresh**: No manual polling required
- **Toast Notifications**: Success/error feedback for all operations
- **Loading States**: Clear indication during async operations

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Test checkpoint system
pytest backend/tests/test_checkpoints_db.py -v
pytest backend/tests/test_checkpoint_creation.py -v
pytest backend/tests/test_checkpoint_api.py -v
pytest backend/tests/test_artifact_editing.py -v
pytest backend/tests/test_yolo_mode.py -v

# Test individual phases
python test_phase1.py
python test_phase2_storyboard.py
python test_phase4_with_storyboard.py
python test_phase5.py

# End-to-end test
python test_pipeline_end_to_end.py
```

## 📈 Monitoring

### Real-time Monitoring

```bash
# Monitor video generation
python monitor.py {video_id}

# Monitor latest video
python monitor.py
```

### Logs

```bash
# View Celery worker logs
docker-compose logs -f worker

# View API logs
docker-compose logs -f api
```

## 🐛 Known Issues & Fixes

### Recent Updates (Latest)

1. **✅ Complete: Checkpoint System (2025-11-21)**
   - Implemented 4-phase pipeline with interactive checkpoints
   - Added artifact editing and creative branching
   - Frontend: 4 new components, 9 new API methods
   - Backend: 6 phases complete, all 65 tests passing
   - Status: Production-ready

2. **✅ Fixed: Undefined `generation_time` when Phase 5 succeeds**
   - Issue: Variable not calculated in success path
   - Fix: Calculate `generation_time` before Phase 5 success check

3. **✅ Fixed: Missing database updates when Phase 5 succeeds**
   - Issue: Phase 5 output not stored in database
   - Fix: Added complete database update logic in success path

4. **✅ Fixed: Duplicate exception handling**
   - Issue: Duplicate exception blocks in `generate_from_storyboard.py`
   - Fix: Removed duplicate handler

5. **✅ Fixed: Hardcoded Phase 4 storyboard threshold**
   - Issue: Only used storyboard logic if `> 1` images
   - Fix: Always use storyboard logic, dynamically adapts to any count

6. **✅ Fixed: Beat-to-chunk mapping calculation**
   - Issue: Recalculated start times instead of using actual values
   - Fix: Uses actual `beat['start']` values from Phase 1

### Known Limitations

1. **Spec Editing**: Only placeholder UI in frontend, full editor coming soon
2. **Branch Switching**: BranchSelector disabled, can only view current branch
3. **Mobile Layout**: Not optimized for small screens
4. **Checkpoint Comparison**: Side-by-side artifact comparison not yet implemented

## 🚀 Deployment

### AWS Deployment

See `ARCHITECTURE.md` for detailed deployment architecture.

**Infrastructure:**
- **Web Tier**: Elastic Beanstalk (FastAPI)
- **Worker Tier**: Elastic Beanstalk (Celery)
- **Database**: RDS PostgreSQL
- **Cache**: ElastiCache Redis
- **Storage**: S3
- **CDN**: CloudFront
- **Region**: us-east-2

### Production Checklist

**Infrastructure:**
- [ ] Set environment variables in Elastic Beanstalk
- [ ] Configure S3 bucket CORS
- [ ] Set up CloudFront distribution
- [ ] Configure auto-scaling
- [ ] Set up monitoring and alerts
- [ ] Configure rate limiting
- [ ] Set up user authentication

**Checkpoint System:**
- [ ] Run database migration: `004_add_checkpoints.sql`
- [ ] Verify checkpoint tables created: `video_checkpoints`, `checkpoint_artifacts`
- [ ] Test SSE streaming in production environment
- [ ] Verify S3 versioned artifact paths working correctly
- [ ] Test Firebase authentication with checkpoint endpoints
- [ ] Verify Redis checkpoint caching (60-min TTL)

## 📚 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Complete architecture documentation
- **[user-flow.md](./user-flow.md)**: Complete checkpoint system user flow
- **[implementation-summary-frontend-checkpoints.md](./implementation-summary-frontend-checkpoints.md)**: Frontend implementation details
- **[Backend Plan](./thoughts/shared/plans/2025-11-20-checkpoint-feature.md)**: Backend checkpoint implementation plan
- **[API Docs](http://localhost:8000/docs)**: Interactive API documentation

## 🤝 Contributing

This is a solo development project. For questions or issues, please open a GitHub issue.

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- OpenAI for GPT-4
- Replicate for video/image generation APIs
- AWS for infrastructure services

---

**Last Updated**: November 21, 2025
**Version**: 3.0 (Checkpoint System with Interactive Branching)
**Major Features**:
- 4-phase pipeline with checkpoints
- Artifact editing and regeneration
- Creative branching system
- YOLO mode for auto-continue
- Real-time SSE streaming
- Complete frontend integration
