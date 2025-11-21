# Backend README

## Recent Changes

**January 2025**: Added Reference Assets feature (PR #1) - Users can now upload, manage, and use reference images in video generation. See `REFERENCE_ASSETS.md` for details.

**November 17, 2025**: Migrated from Alembic to raw SQL migrations for better control and to eliminate race conditions in multi-container setups. All migrations are now in `migrations/*.sql` and run via `python migrate.py`.

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

# Firebase (for authentication)
# Option 1: JSON file with private_key from env var (recommended)
# Copy firebase-credentials.json.example to firebase-credentials.json and fill in values (except private_key)
# Then set the private_key here:
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"
# And set the path to the JSON file (or use GOOGLE_APPLICATION_CREDENTIALS env var)
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json

# Option 2: Use GOOGLE_APPLICATION_CREDENTIALS env var pointing to JSON file
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-credentials.json
# FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"

# Option 3: Use individual environment variables (alternative)
# FIREBASE_PROJECT_ID=your-project-id
# FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYour private key here\n-----END PRIVATE KEY-----\n"
# FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@your-project.iam.gserviceaccount.com
```

**Note:** The `.env` file is gitignored and should never be committed. Copy these variables and fill in your actual API keys and credentials.

### Firebase Credentials Setup

**Recommended Approach: JSON file with private_key in .env**

1. Go to [Firebase Console](https://console.firebase.google.com/) → Your Project → Project Settings → Service Accounts
2. Click "Generate new private key" to download a JSON file
3. Copy `firebase-credentials.json.example` to `firebase-credentials.json`
4. Copy all fields from the downloaded JSON **except `private_key`** into `firebase-credentials.json`
5. Extract the `private_key` value and add it to `.env` as `FIREBASE_PRIVATE_KEY`
6. Set `FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json` in `.env` (or use `GOOGLE_APPLICATION_CREDENTIALS`)

**Important:** 
- `firebase-credentials.json` can be committed (it doesn't contain the private key)
- `FIREBASE_PRIVATE_KEY` in `.env` is gitignored and should never be committed
- The `FIREBASE_PRIVATE_KEY` in `.env` should be in quotes and include `\n` for newlines

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

This project uses raw SQL migrations for database schema management.

> 📖 **Detailed guide**: See [migrations/README.md](migrations/README.md) for comprehensive migration documentation

### Running Migrations

**From your local machine:**
```bash
# Check migration status
python migrate.py status

# Run all pending migrations
python migrate.py up
```

**From Docker:**
```bash
# Check migration status
docker compose exec api python migrate.py status

# Run all pending migrations
docker compose exec api python migrate.py up
```

### Creating New Migrations

When you need to modify the database schema:

1. Create a new SQL file in `migrations/` with the next number:
   ```bash
   migrations/004_your_description.sql
   ```

2. Write your SQL (use `DO $$ BEGIN ... END $$;` for conditional logic):
   ```sql
   -- Description of what this migration does
   -- Migration: 004_your_description
   -- Date: YYYY-MM-DD
   
   ALTER TABLE video_generations ADD COLUMN new_field VARCHAR;
   ```

3. Apply the migration:
   ```bash
   python migrate.py up
   ```

### Migration Best Practices

1. **Never delete committed migration files** - create a new migration to revert changes
2. **Always review auto-generated migrations** - they may not catch everything
3. **Test migrations on a copy of production data** before deploying
4. **Keep migrations idempotent** - running twice should be safe
