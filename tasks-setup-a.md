# Setup Tasks - Part A: Infrastructure & Docker

**Owner:** Either person (coordinate who does what)  
**Time Estimate:** 1-2 hours  
**Goal:** Get local development environment running

---

## Task 1: Create Project Structure

### 1.1 Initialize Backend
```bash
mkdir videogen-pipeline
cd videogen-pipeline

# Backend structure
mkdir -p backend/app/{common,services,api,orchestrator,phases,tests}
mkdir -p backend/app/phases/{phase1_validate,phase2_animatic,phase3_references,phase4_chunks,phase5_refine,phase6_export}
mkdir -p backend/alembic/versions

cd backend
```

### 1.2 Create Backend Files
```bash
# Root level
touch Dockerfile
touch docker-compose.yml
touch requirements.txt
touch .env.example
touch README.md
touch .gitignore

# App level
touch app/__init__.py
touch app/main.py
touch app/config.py
touch app/database.py

# Common (shared code)
touch app/common/__init__.py
touch app/common/models.py
touch app/common/schemas.py
touch app/common/exceptions.py
touch app/common/logging.py
touch app/common/constants.py

# Services (external APIs)
touch app/services/__init__.py
touch app/services/replicate.py
touch app/services/openai.py
touch app/services/s3.py
touch app/services/ffmpeg.py

# API endpoints
touch app/api/__init__.py
touch app/api/generate.py
touch app/api/status.py
touch app/api/video.py
touch app/api/health.py

# Orchestrator
touch app/orchestrator/__init__.py
touch app/orchestrator/celery_app.py
touch app/orchestrator/pipeline.py
touch app/orchestrator/progress.py
touch app/orchestrator/cost_tracker.py

# Tests
touch app/tests/conftest.py
```

### 1.3 Create Phase Folders
```bash
# Phase 1 (Person handling Phase 1 will fill these)
touch app/phases/phase1_validate/__init__.py
touch app/phases/phase1_validate/task.py
touch app/phases/phase1_validate/service.py
touch app/phases/phase1_validate/schemas.py
mkdir -p app/phases/phase1_validate/templates

# Phase 2 (Person handling Phase 2 will fill these)
touch app/phases/phase2_animatic/__init__.py
touch app/phases/phase2_animatic/task.py
touch app/phases/phase2_animatic/service.py
touch app/phases/phase2_animatic/schemas.py
touch app/phases/phase2_animatic/prompts.py

# Placeholder for other phases
for phase in phase3_references phase4_chunks phase5_refine phase6_export; do
  touch app/phases/$phase/__init__.py
  touch app/phases/$phase/task.py
  touch app/phases/$phase/service.py
  touch app/phases/$phase/schemas.py
done
```

---

## Task 2: Create Dockerfile

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

---

## Task 3: Create requirements.txt

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

---

## Task 4: Create docker-compose.yml

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
      S3_BUCKET: ${S3_BUCKET:-videogen-outputs-dev}
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
      S3_BUCKET: ${S3_BUCKET:-videogen-outputs-dev}
      AWS_REGION: us-east-2
    volumes:
      - ./app:/app/app
    command: celery -A app.orchestrator.celery_app worker --loglevel=info --concurrency=4

volumes:
  postgres_data:
```

---

## Task 5: Create .env.example

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
S3_BUCKET=videogen-outputs-dev
AWS_REGION=us-east-2
```

---

## Task 6: Create .gitignore

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

---

## Task 7: Create .env file (LOCAL ONLY)
```bash
# Copy example and fill in real values
cp .env.example .env

# Edit .env with your actual keys
# DO NOT COMMIT THIS FILE
```

---

## Task 8: Test Docker Setup
```bash
# Build and start services
docker-compose up --build

# In another terminal, verify services are running
docker-compose ps

# Expected output:
# postgres: healthy
# redis: healthy
# api: running on port 8000
# worker: running

# Test API health
curl http://localhost:8000/health
# Should return: {"status": "ok"}

# Stop services
docker-compose down
```

---

## ✅ Checkpoint

After completing these tasks, you should have:
- ✅ Project structure created
- ✅ Dockerfile configured
- ✅ Docker Compose running (postgres, redis, api, worker)
- ✅ All placeholder files created
- ✅ Ready for implementing shared code in Setup Part B

**Next:** Move to `tasks-setup-b.md`