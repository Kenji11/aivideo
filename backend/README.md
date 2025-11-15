# Backend README

## Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

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

**Note:** The `.env` file is gitignored and should never be committed. Copy these variables and fill in your actual API keys and credentials.

## Docker Setup

### Prerequisites
- Docker and Docker Compose installed
- Environment variables configured in `.env` file

### Running the Services

```bash
# Build and start all services
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Services

- **postgres**: PostgreSQL database on port 5432
- **redis**: Redis cache on port 6379
- **api**: FastAPI application on port 8000
- **worker**: Celery worker for background tasks

### Health Check

Once services are running, test the API:

```bash
curl http://localhost:8000/health
```

Expected response: `{"status": "ok"}`
