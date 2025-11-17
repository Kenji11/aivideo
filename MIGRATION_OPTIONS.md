# Migration Strategy Options

## Current Problem
Alembic is causing race conditions in our multi-container setup. Both `api-1` and `worker-1` containers run migrations simultaneously, leading to `duplicate key` errors on the `alembic_version` table. The error occurs because PostgreSQL's internal catalog conflicts when multiple processes try to create the same table.

## Option A: Raw SQL Scripts

**Approach:** Manual SQL files with a simple Python runner script.

**Structure:**
```
backend/migrations/
  001_initial_schema.sql
  002_add_final_music_url.sql
  003_add_storyboard_images.sql
```

**Pros:**
- Full control, no magic or abstractions
- Transparent - everyone on team knows SQL
- Easy debugging (just read the SQL file)
- No vendor lock-in
- Similar to Knex pattern we used successfully in Node
- Simple migration tracking via `schema_migrations` table

**Cons:**
- Manual tracking of applied migrations
- No auto-generation from model changes
- Need to write basic runner script
- Have to manually write up/down migrations

---

## Option B: Yoyo Migrations

**Approach:** Lightweight Python migration library (Knex-like for Python).

**Pros:**
- Simple, explicit migrations
- Built-in transaction support
- Rollback support
- CLI tools provided
- Less complex than Alembic
- Supports both SQL and Python migrations

**Cons:**
- Smaller ecosystem/community than Alembic
- Less mature tooling
- Still adds a dependency
- Team needs to learn new tool

---

## Option C: Fix Alembic Race Condition

**Approach:** Keep Alembic but solve multi-container startup issues.

**Solutions:**
1. Remove migrations from Dockerfile entrypoint, run manually
2. Use separate init container for migrations
3. Add PostgreSQL advisory locks to prevent simultaneous runs
4. Only run migrations in one service (api or worker, not both)

**Pros:**
- Industry standard, widely adopted
- Stays with SQLAlchemy ecosystem
- Auto-generation from model changes
- Familiar to most Python developers

**Cons:**
- Complex abstraction layer
- Notorious for revision mismatch errors
- Poor error messages
- Still dealing with Alembic quirks long-term
- Over-engineered for our simple schema (2 tables)

---

## Recommendation

**Option A (Raw SQL Scripts)** - Best fit for our team:
- We have a simple schema (2 tables)
- All 3 engineers know SQL well
- Proven pattern from Node/Knex projects
- Complete transparency for debugging
- No surprises or magic

