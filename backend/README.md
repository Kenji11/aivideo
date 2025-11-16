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

## Database Migrations

This project uses Alembic for database schema management.

> 📖 **Detailed guide**: See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for comprehensive migration documentation

### Running Migrations

**First time setup:**
```bash
# Run migrations to create tables
alembic upgrade head
```

**After pulling new code:**
```bash
# Check current migration status
alembic current

# Apply new migrations
alembic upgrade head
```

### Creating New Migrations

When you modify the SQLAlchemy models in `app/common/models.py`:

```bash
# Generate a new migration automatically
alembic revision --autogenerate -m "description of changes"

# Review the generated migration file in alembic/versions/
# Edit if needed, then apply it
alembic upgrade head
```

### Docker Setup

When using Docker, migrations run automatically on container startup. If you need to run them manually:

```bash
# Access the API container
docker-compose exec api bash

# Run migrations
alembic upgrade head
```

### Migration Best Practices

1. **Never delete committed migration files** - create a new migration to revert changes
2. **Always review auto-generated migrations** - they may not catch everything
3. **Test migrations on a copy of production data** before deploying
4. **Keep migrations idempotent** - running twice should be safe
