# AI Video Generation Pipeline

An end-to-end AI-powered system that transforms natural language prompts into professional video advertisements through a 5-phase sequential pipeline.

## 🎯 Overview

This system generates 30-second video advertisements from text prompts using:
- **GPT-4** for intelligent planning and beat composition
- **FLUX Dev** for storyboard image generation
- **Hailuo/Veo** for video chunk generation
- **MusicGen** for background music
- **FFmpeg** for video stitching and audio integration

### Key Features
- ✅ **Dynamic Storyboard Mapping**: Adapts to any number of storyboard images
- ✅ **Temporal Coherence**: Last-frame continuation ensures smooth transitions
- ✅ **Multiple Models**: Support for Hailuo, Veo, and other video models
- ✅ **Real-time Progress**: Live progress tracking via polling
- ✅ **Cost Tracking**: Per-phase cost monitoring
- ✅ **Sequential Pipeline**: 5 phases executed in order

## 🏗️ Architecture

### System Components

```
Frontend (React) → FastAPI → Celery Workers → AI Services → S3 Storage
                                    ↓
                              PostgreSQL (Status)
```

### Pipeline Flow

1. **Phase 1: Validation & Planning** (5-10s)
   - GPT-4 analyzes prompt
   - Composes beat sequence from 15-beat library
   - Creates complete video specification

2. **Phase 2: Storyboard Generation** (~8s per image)
   - Generates 1 FLUX Dev image per beat
   - Uploads to S3
   - Stores image URLs in spec

3. **Phase 3: References** (DISABLED)
   - Skipped - Phase 2 storyboard images replace this

4. **Phase 4: Video Chunk Generation** (~45s per chunk)
   - Dynamically maps beats to chunks
   - Uses storyboard images at beat boundaries
   - Uses last-frame continuation within beats
   - Stitches chunks with FFmpeg

5. **Phase 5: Refinement & Audio** (~2 min, or skipped for Veo)
   - Generates background music
   - Combines video + audio
   - Uploads final video

### Generation Time

**30-second video:**
- **With Phase 5**: ~8.4 minutes (hailuo_fast) or ~6.4 minutes (Veo)
- **Breakdown**:
  - Phase 1: ~7 seconds
  - Phase 2: ~32 seconds (4 images)
  - Phase 4: ~5.5 minutes (6 chunks × 45s + stitching)
  - Phase 5: ~2 minutes (or skipped)

### Cost per Video

**30-second video:**
- Phase 1: $0.02 (GPT-4)
- Phase 2: $0.10 (4 images × $0.025)
- Phase 4: $0.24 (6 chunks × $0.04 for hailuo_fast)
- Phase 5: $0.15 (MusicGen)
- **Total**: ~$0.51 (hailuo_fast) or ~$0.36 (Veo, no Phase 5)

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
# Via API
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a 30-second Nike sneaker ad, energetic style",
    "title": "Nike Ad",
    "model": "hailuo_fast"
  }'

# Response: {"video_id": "...", "status": "queued"}

# Check status
curl http://localhost:8000/api/status/{video_id}
```

## 📁 Project Structure

```
aivideo/
├── backend/
│   ├── app/
│   │   ├── api/              # REST API endpoints
│   │   ├── orchestrator/      # Pipeline orchestration
│   │   ├── phases/           # Phase implementations
│   │   │   ├── phase1_validate/
│   │   │   ├── phase2_storyboard/
│   │   │   ├── phase3_chunks/
│   │   │   └── phase4_refine/
│   │   ├── services/         # External service clients
│   │   └── common/           # Shared code
│   ├── docker-compose.yml
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   └── lib/             # Utilities
│   └── package.json
├── ARCHITECTURE.md           # Detailed architecture docs
├── memory-bank/             # Project documentation
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

Default model is `hailuo_fast`. To change:

```python
# backend/app/phases/phase3_chunks/model_config.py
DEFAULT_MODEL = 'hailuo_fast'  # Change to 'veo_fast', 'veo', etc.
```

Available models:
- `hailuo_fast`: Hailuo 2.3 Fast (default, 5s chunks, $0.04/chunk)
- `veo_fast`: Google Veo 3.1 Fast (5s chunks, native audio)
- `veo`: Google Veo 3.1 (5s chunks, native audio)
- `wan`: Wan 2.1 (5s chunks, $0.45/chunk)
- And more...

## 📊 API Endpoints

### Generate Video
```http
POST /api/generate
Content-Type: application/json

{
  "prompt": "Create a 30-second Nike ad",
  "title": "Nike Ad",
  "description": "Energetic lifestyle ad",
  "model": "hailuo_fast",
  "reference_assets": ["asset_id_1", "asset_id_2"]
}

Response: {
  "video_id": "uuid",
  "status": "queued",
  "message": "Video generation started"
}
```

### Get Status
```http
GET /api/status/{video_id}

Response: {
  "video_id": "uuid",
  "status": "generating_chunks",
  "progress": 65.5,
  "current_phase": "phase4_chunks",
  "animatic_urls": ["presigned_url_1", ...],
  "stitched_video_url": "presigned_url",
  "final_video_url": "presigned_url",
  "current_chunk_index": 3,
  "total_chunks": 6,
  "cost_usd": 0.36
}
```

### Upload Assets
```http
POST /api/upload
Content-Type: multipart/form-data

files: [file1, file2, ...]

Response: {
  "asset_ids": ["uuid1", "uuid2", ...]
}
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

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

### Recent Bug Fixes (Latest)

1. **✅ Fixed: Undefined `generation_time` when Phase 5 succeeds**
   - Issue: Variable not calculated in success path
   - Fix: Calculate `generation_time` before Phase 5 success check

2. **✅ Fixed: Missing database updates when Phase 5 succeeds**
   - Issue: Phase 5 output not stored in database
   - Fix: Added complete database update logic in success path

3. **✅ Fixed: Duplicate exception handling**
   - Issue: Duplicate exception blocks in `generate_from_storyboard.py`
   - Fix: Removed duplicate handler

4. **✅ Fixed: Hardcoded Phase 4 storyboard threshold**
   - Issue: Only used storyboard logic if `> 1` images
   - Fix: Always use storyboard logic, dynamically adapts to any count

5. **✅ Fixed: Beat-to-chunk mapping calculation**
   - Issue: Recalculated start times instead of using actual values
   - Fix: Uses actual `beat['start']` values from Phase 1

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

- [ ] Set environment variables in Elastic Beanstalk
- [ ] Configure S3 bucket CORS
- [ ] Set up CloudFront distribution
- [ ] Configure auto-scaling
- [ ] Set up monitoring and alerts
- [ ] Configure rate limiting
- [ ] Set up user authentication

## 📚 Documentation

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: Complete architecture documentation
- **[memory-bank/](./memory-bank/)**: Project context and patterns
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

**Last Updated**: December 2024  
**Version**: 2.0 (Beat-Based Architecture)
