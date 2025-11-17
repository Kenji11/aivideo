# Migration from Alembic to Raw SQL

## Summary

Replaced Alembic with a simple raw SQL migration system for better control, transparency, and to avoid race condition issues in multi-container Docker setups.

## What Was Changed

### Removed
- ❌ `alembic/` directory and all version files
- ❌ `alembic.ini` configuration file
- ❌ `alembic==1.13.0` from requirements.txt
- ❌ Alembic code from `app/database.py`
- ❌ `create_initial_migration.py` helper script
- ❌ `migrate_add_final_music_url.py` helper script
- ❌ `MIGRATION_GUIDE.md` (Alembic-specific)
- ❌ Automatic migrations from Dockerfile entrypoint

### Added
- ✅ `migrations/` directory with SQL files:
  - `001_initial_schema.sql` - Complete initial schema
  - `002_add_final_music_url.sql` - Add music URL column
  - `003_add_storyboard_images.sql` - Add storyboard images column
  - `README.md` - Migration system documentation
- ✅ `migrate.py` - Simple Python migration runner
- ✅ Updated `README.md` with new migration instructions

### Modified
- 📝 `app/database.py` - Simplified `init_db()` function (removed Alembic integration)
- 📝 `backend/Dockerfile` - Removed automatic migration entrypoint
- 📝 `.env` - Updated `DATABASE_URL` to use `localhost:5434` for local development

## How It Works

### Migration Tracking
- Uses `schema_migrations` table to track applied migrations
- Each migration has a version number (001, 002, etc.) and filename
- Migrations run in transaction-safe mode (auto-rollback on error)

### Running Migrations

**Local machine:**
```bash
python migrate.py status   # Check what's applied
python migrate.py up       # Run pending migrations
```

**Docker container:**
```bash
docker compose exec api python migrate.py status
docker compose exec api python migrate.py up
```

### Creating New Migrations

1. Create `migrations/00X_description.sql`
2. Write SQL with header comments
3. Use `DO $$ BEGIN ... END $$;` blocks for conditional logic
4. Run `python migrate.py up`

## Why We Made This Change

### Problems with Alembic
1. **Race conditions** - Multiple containers running migrations simultaneously
2. **Revision mismatches** - Database state conflicts between branches
3. **Over-engineered** - Complex abstraction for a simple 2-table schema
4. **Poor error messages** - Hard to debug when things go wrong
5. **Magic auto-generation** - Not always accurate, required manual review anyway

### Benefits of Raw SQL
1. **Full transparency** - Just SQL, no magic
2. **Better control** - Write exactly what you need
3. **Easier debugging** - Read the SQL file directly
4. **Team familiarity** - Everyone knows SQL
5. **No dependencies** - One less package to maintain
6. **Proven pattern** - Similar to Knex migrations we've used successfully

## Migration Status

All existing Alembic migrations have been converted to equivalent SQL files. The database schema remains unchanged - we just changed how we manage it.

## Next Steps

1. Run `python migrate.py up` to apply migrations to your local database
2. Commit these changes
3. Team members should:
   - Pull the changes
   - Update their `.env` to use `localhost:5434` for DATABASE_URL
   - Run `python migrate.py status` to check migration status
   - Run `python migrate.py up` if needed

## Notes

- The `init_db()` function still uses `Base.metadata.create_all()` as a fallback
- This is safe - it only creates missing tables, doesn't modify existing ones
- For all schema changes, use the migration system: `python migrate.py up`

