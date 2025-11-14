# Technical Context

## Technology Stack

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite (fast dev server, optimized builds)
- **Styling**: Tailwind CSS + shadcn/ui components
- **UI Primitives**: Radix UI
- **Deployment**: S3 + CloudFront (static hosting + CDN)
- **Package Manager**: npm

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Task Queue**: Celery 5.x
- **Job Broker**: Redis (ElastiCache)
- **Result Backend**: Redis (same instance)
- **Database**: PostgreSQL 15 (RDS)
- **ORM**: SQLAlchemy 2.x
- **Migrations**: Alembic
- **Deployment**: Elastic Beanstalk (Docker containers)

### AI/ML Services
- **OpenAI**: GPT-4 Turbo (prompt validation)
- **Replicate API**:
  - SDXL: Image generation (animatic + references)
  - Zeroscope v2 XL: Video generation (development)
  - AnimateDiff: Video generation (final/high-quality)
  - MusicGen: Background music generation

### Infrastructure (AWS)
- **Compute**: Elastic Beanstalk (Web + Worker tiers)
- **Database**: RDS PostgreSQL (db.t4g.micro)
- **Cache**: ElastiCache Redis (t4g.micro)
- **Storage**: S3 (video outputs)
- **CDN**: CloudFront (frontend + video delivery)
- **Load Balancer**: Application Load Balancer

### Development Tools
- **Containerization**: Docker + Docker Compose
- **Dependency Management**: Poetry (Python), npm (JavaScript)
- **Testing**: Pytest (backend), Vitest (frontend)
- **Linting**: Ruff (Python), ESLint (JavaScript)
- **Formatting**: Black (Python), Prettier (JavaScript)
- **Video Processing**: FFmpeg (installed in Docker image)

## Development Environment

### Prerequisites
```bash
# Required software
- Docker Desktop
- Python 3.11+
- Node.js 18+
- AWS CLI
- Git

# API Keys needed
- REPLICATE_API_TOKEN
- OPENAI_API_KEY
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
```

### Local Setup (Docker Compose)
```bash
# Clone and setup
git clone <repo>
cd aivideo

# Create .env file
cp .env.example .env
# Edit .env with API keys

# Start all services
docker-compose up -d

# Services will be available at:
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Frontend: http://localhost:5173 (Vite dev server)
# - PostgreSQL: localhost:5432
# - Redis: localhost:6379
```

### Project Structure
```
aivideo/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment config
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # Database models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── api/                 # API endpoints
│   │   ├── tasks/               # Celery tasks (pipeline phases)
│   │   ├── services/            # External API clients
│   │   └── templates/           # Video templates (JSON)
│   ├── tests/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── hooks/               # Custom hooks
│   │   ├── lib/                 # Utilities, API client
│   │   └── types/               # TypeScript types
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── PRD.md
├── memory-bank/
└── README.md
```

## Key Dependencies

### Backend (Python)
```
fastapi[all]==0.104.1          # Web framework
celery[redis]==5.3.4           # Task queue
redis==5.0.1                   # Redis client
sqlalchemy==2.0.23             # ORM
alembic==1.12.1                # Migrations
psycopg2-binary==2.9.9         # PostgreSQL driver
boto3==1.29.7                  # AWS SDK
replicate==0.15.4              # Replicate API client
openai==1.3.5                  # OpenAI API client
pydantic==2.5.0                # Data validation
python-multipart==0.0.6        # File uploads
```

### Frontend (JavaScript/TypeScript)
```json
{
  "react": "^18.2.0",
  "react-dom": "^18.2.0",
  "typescript": "^5.2.2",
  "vite": "^5.0.0",
  "tailwindcss": "^3.3.0",
  "@radix-ui/react-*": "^1.0.0",  // UI primitives
  "axios": "^1.6.0",                // HTTP client
  "zustand": "^4.4.0"               // State management (optional)
}
```

## External API Limits & Costs

### Replicate API
- **Rate Limits**: 50 concurrent predictions per account
- **SDXL**: $0.0055 per image
- **Zeroscope**: ~$0.10 per 2s video chunk
- **AnimateDiff**: ~$0.20 per 2s video chunk
- **MusicGen**: ~$0.15 per 30s audio

### OpenAI API
- **GPT-4 Turbo**: $0.01/1K input tokens, $0.03/1K output tokens
- **Typical prompt validation**: ~$0.01 per video

### AWS Service Quotas
- **RDS**: 40 connections max (db.t4g.micro)
- **ElastiCache**: 0.5 GB memory (t4g.micro)
- **S3**: Unlimited storage, but costs $0.023/GB-month
- **Data Transfer**: First 100 GB/month = $0.09/GB

## Technical Constraints

### Video Generation
- **Resolution**: Generate at 1024×576, upscale to 1920×1080
- **Frame Rate**: Generate at 24fps, interpolate to 30fps
- **Chunk Size**: 2 seconds (48 frames at 24fps)
- **Chunk Count**: 15 chunks for 30s video
- **Overlap**: 0.5s overlap between chunks for smooth transitions

### Performance Targets
- **Generation Time**: <10 minutes per 30s video
- **Success Rate**: >90%
- **Cost**: <$2 per video (MVP)
- **Concurrent Users**: 1 per user (MVP)

### Database Schema
```python
# Key tables
- video_generations: Main video records
  - id (UUID), prompt, spec, status, progress
  - animatic_frames, reference_assets, chunk_urls
  - final_video_url, cost_usd, generation_time_seconds
  
# Status enum
- queued, validating, generating_animatic
- generating_references, generating_chunks
- refining, complete, failed
```

## Deployment Considerations

### Elastic Beanstalk
- **Web Tier**: t3.small (2 GB RAM) - Runs FastAPI
- **Worker Tier**: t3.medium (4 GB RAM) - Runs Celery workers
- **Auto-scaling**: Based on CPU (Web) and queue depth (Worker)
- **Health Checks**: /health endpoint on Web tier

### Docker Images
- **Base**: python:3.11-slim
- **Adds**: FFmpeg, libsm6, libxext6 (for video processing)
- **Size**: ~500 MB after optimization

### Environment Variables
```bash
# Required in production
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
REPLICATE_API_TOKEN=r8_...
OPENAI_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET=videogen-outputs-prod
S3_REGION=us-east-1
```

## Known Technical Challenges

### 1. Temporal Consistency
- **Problem**: AI video models create frame-to-frame drift
- **Solution**: Use animatic as ControlNet reference
- **Fallback**: Motion-first pipeline alternative

### 2. API Rate Limits
- **Problem**: Replicate limits 50 concurrent predictions
- **Solution**: Throttle requests, queue excess
- **Mitigation**: Retry with exponential backoff

### 3. Long Processing Times
- **Problem**: Video generation is inherently slow (5-8 min)
- **Solution**: Parallel chunk generation, real-time progress updates
- **UX**: Clear progress indicators, estimated time remaining

### 4. Cost Control
- **Problem**: Easy to overspend during development
- **Solution**: Use Zeroscope (cheap) for dev, AnimateDiff (expensive) for final
- **Tracking**: Log costs per phase in database

### 5. FFmpeg Complexity
- **Problem**: Video stitching, transitions, audio sync require complex FFmpeg commands
- **Solution**: Pre-built filter chains in ffmpeg_service.py
- **Testing**: Unit tests for each FFmpeg operation

