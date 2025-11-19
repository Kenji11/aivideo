# Setup Tasks - Part A: Infrastructure & Docker

**Owner:** Either person (coordinate who does what)  
**Goal:** Get local development environment running

---

## PR #1: Project Structure & Basic Files

### Task 1.1: Initialize Backend Structure
```bash
mkdir videogen-pipeline
cd videogen-pipeline

# Backend structure
mkdir -p backend/app/{common,services,api,orchestrator,phases,tests}
mkdir -p backend/app/phases/{phase1_validate,phase2_animatic,phase3_references,phase4_chunks,phase4_refine,phase6_export}
mkdir -p backend/alembic/versions

cd backend
```

- [ ] Create root `videogen-pipeline` directory
- [ ] Create `backend/app` directory structure
- [ ] Create all phase directories in `backend/app/phases/`
- [ ] Create `backend/alembic/versions` directory

### Task 1.2: Create Root Level Files
```bash
# Root level
touch Dockerfile
touch docker-compose.yml
touch requirements.txt
touch .env.example
touch README.md
touch .gitignore
```

- [ ] Create `Dockerfile`
- [ ] Create `docker-compose.yml`
- [ ] Create `requirements.txt`
- [ ] Create `.env.example`
- [ ] Create `README.md`
- [ ] Create `.gitignore`

### Task 1.3: Create App Level Files
```bash
# App level
touch app/__init__.py
touch app/main.py
touch app/config.py
touch app/database.py
```

- [ ] Create `app/__init__.py`
- [ ] Create `app/main.py`
- [ ] Create `app/config.py`
- [ ] Create `app/database.py`

### Task 1.4: Create Common Files
```bash
# Common (shared code)
touch app/common/__init__.py
touch app/common/models.py
touch app/common/schemas.py
touch app/common/exceptions.py
touch app/common/logging.py
touch app/common/constants.py
```

- [ ] Create `app/common/__init__.py`
- [ ] Create `app/common/models.py`
- [ ] Create `app/common/schemas.py`
- [ ] Create `app/common/exceptions.py`
- [ ] Create `app/common/logging.py`
- [ ] Create `app/common/constants.py`

### Task 1.5: Create Services Files
```bash
# Services (external APIs)
touch app/services/__init__.py
touch app/services/replicate.py
touch app/services/openai.py
touch app/services/s3.py
touch app/services/ffmpeg.py
```

- [ ] Create `app/services/__init__.py`
- [ ] Create `app/services/replicate.py`
- [ ] Create `app/services/openai.py`
- [ ] Create `app/services/s3.py`
- [ ] Create `app/services/ffmpeg.py`

### Task 1.6: Create API Files
```bash
# API endpoints
touch app/api/__init__.py
touch app/api/generate.py
touch app/api/status.py
touch app/api/video.py
touch app/api/health.py
```

- [ ] Create `app/api/__init__.py`
- [ ] Create `app/api/generate.py`
- [ ] Create `app/api/status.py`
- [ ] Create `app/api/video.py`
- [ ] Create `app/api/health.py`

### Task 1.7: Create Orchestrator Files
```bash
# Orchestrator
touch app/orchestrator/__init__.py
touch app/orchestrator/celery_app.py
touch app/orchestrator/pipeline.py
touch app/orchestrator/progress.py
touch app/orchestrator/cost_tracker.py
```

- [ ] Create `app/orchestrator/__init__.py`
- [ ] Create `app/orchestrator/celery_app.py`
- [ ] Create `app/orchestrator/pipeline.py`
- [ ] Create `app/orchestrator/progress.py`
- [ ] Create `app/orchestrator/cost_tracker.py`

### Task 1.8: Create Test Files
```bash
# Tests
touch app/tests/conftest.py
```

- [ ] Create `app/tests/conftest.py`

### Task 1.9: Create Phase 1 Files
```bash
# Phase 1
touch app/phases/phase1_validate/__init__.py
touch app/phases/phase1_validate/task.py
touch app/phases/phase1_validate/service.py
touch app/phases/phase1_validate/schemas.py
mkdir -p app/phases/phase1_validate/templates
```

- [ ] Create `app/phases/phase1_validate/__init__.py`
- [ ] Create `app/phases/phase1_validate/task.py`
- [ ] Create `app/phases/phase1_validate/service.py`
- [ ] Create `app/phases/phase1_validate/schemas.py`
- [ ] Create `app/phases/phase1_validate/templates/` directory

### Task 1.10: Create Phase 2 Files
```bash
# Phase 2
touch app/phases/phase2_animatic/__init__.py
touch app/phases/phase2_animatic/task.py
touch app/phases/phase2_animatic/service.py
touch app/phases/phase2_animatic/schemas.py
touch app/phases/phase2_animatic/prompts.py
```

- [ ] Create `app/phases/phase2_animatic/__init__.py`
- [ ] Create `app/phases/phase2_animatic/task.py`
- [ ] Create `app/phases/phase2_animatic/service.py`
- [ ] Create `app/phases/phase2_animatic/schemas.py`
- [ ] Create `app/phases/phase2_animatic/prompts.py`

### Task 1.11: Create Placeholder Phase Files
```bash
# Placeholder for other phases
for phase in phase3_references phase4_chunks phase4_refine phase6_export; do
  touch app/phases/$phase/__init__.py
  touch app/phases/$phase/task.py
  touch app/phases/$phase/service.py
  touch app/phases/$phase/schemas.py
done
```

- [ ] Create phase3 placeholder files
- [ ] Create phase4 placeholder files
- [ ] Create phase5 placeholder files
- [ ] Create phase6 placeholder files

---

## PR #2: Docker Configuration

### Task 2.1: Create Dockerfile

**File:** `backend/Dockerfile`
```dockerfile
FROM python:3.11-slim

# Install FFmpeg and system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Default command (overridden in docker-compose for worker)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] Create Dockerfile with Python 3.11 base image
- [ ] Add FFmpeg installation
- [ ] Add requirements.txt copy and pip install
- [ ] Add application code copy
- [ ] Set default uvicorn command

### Task 2.2: Create requirements.txt

**File:** `backend/requirements.txt`
```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
alembic==1.13.0
psycopg2-binary==2.9.9

# Task Queue
celery==5.3.4
redis==5.0.1

# External APIs
openai==1.3.7
replicate==0.22.0
boto3==1.34.10

# Utilities
python-dotenv==1.0.0
python-multipart==0.0.6
```

- [ ] Add FastAPI and Uvicorn dependencies
- [ ] Add database dependencies (SQLAlchemy, Alembic, psycopg2)
- [ ] Add task queue dependencies (Celery, Redis)
- [ ] Add external API dependencies (OpenAI, Replicate, boto3)
- [ ] Add utility dependencies

### Task 2.3: Create docker-compose.yml

**File:** `backend/docker-compose.yml`
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: videogen
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: devpass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://dev:devpass@postgres:5432/videogen
      REDIS_URL: redis://redis:6379/0
      REPLICATE_API_TOKEN: ${REPLICATE_API_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      S3_BUCKET: ${S3_BUCKET:-ai-video-assets-dev}
      AWS_REGION: us-east-2
    volumes:
      - ./app:/app/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://dev:devpass@postgres:5432/videogen
      REDIS_URL: redis://redis:6379/0
      REPLICATE_API_TOKEN: ${REPLICATE_API_TOKEN}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      S3_BUCKET: ${S3_BUCKET:-ai-video-assets-dev}
      AWS_REGION: us-east-2
    volumes:
      - ./app:/app/app
    command: celery -A app.orchestrator.celery_app worker --loglevel=info --concurrency=4

volumes:
  postgres_data:
```

- [ ] Add postgres service with healthcheck
- [ ] Add redis service with healthcheck
- [ ] Add api service with environment variables
- [ ] Add worker service with Celery command
- [ ] Configure service dependencies
- [ ] Add volume mounts for development

### Task 2.4: Create .env.example

**File:** `backend/.env.example`
```bash
# Database
DATABASE_URL=postgresql://dev:devpass@postgres:5432/videogen

# Redis
REDIS_URL=redis://redis:6379/0

# External APIs
REPLICATE_API_TOKEN=r8_your_token_here
OPENAI_API_KEY=sk-your_key_here

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET=ai-video-assets-dev
AWS_REGION=us-east-2
```

- [ ] Add database URL example
- [ ] Add Redis URL example
- [ ] Add external API token placeholders
- [ ] Add AWS configuration placeholders

### Task 2.5: Create .gitignore

**File:** `backend/.gitignore`
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# Environment variables
.env

# Database
*.db
*.sqlite3

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Alembic
alembic/versions/*.pyc
```

- [ ] Add Python-specific ignores
- [ ] Add environment variable ignores
- [ ] Add database file ignores
- [ ] Add IDE ignores
- [ ] Add OS-specific ignores
- [ ] Add log file ignores

### Task 2.6: Create Local Environment File
```bash
# Copy example and fill in real values
cp .env.example .env

# Edit .env with your actual keys
# DO NOT COMMIT THIS FILE
```

- [ ] Copy `.env.example` to `.env`
- [ ] Fill in real API keys in `.env`

### Task 2.7: Test Docker Setup
```bash
# Build and start services
docker-compose up --build

# In another terminal, verify services are running
docker-compose ps

# Test API health
curl http://localhost:8000/health

# Stop services
docker-compose down
```

- [ ] Run `docker-compose up --build`
- [ ] Verify all services show as healthy in `docker-compose ps`
- [ ] Test health endpoint returns success
- [ ] Stop services with `docker-compose down`

---

## ✅ PR #2 Checklist

Before merging PR #2:
- [ ] All Docker files created
- [ ] Services start without errors
- [ ] Health check endpoint responds
- [ ] Can access API docs at http://localhost:8000/docs

**Next:** Move to `tasks-setup-b.md`