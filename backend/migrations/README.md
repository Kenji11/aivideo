# Database Migrations

Raw SQL migrations for the AI Video Generator backend.

## Structure

Migrations are numbered sequentially:
- `001_initial_schema.sql` - Initial database schema (assets, video_generations tables)
- `002_add_final_music_url.sql` - Add final_music_url column (historical, no-op)
- `003_add_storyboard_images.sql` - Add storyboard_images column (deprecated)

## Running Migrations

Use the migration runner script:

```bash
# Run all pending migrations
python migrate.py up

# Check migration status
python migrate.py status

# Rollback last migration (if implemented)
python migrate.py down
```

## Creating New Migrations

1. Create a new file: `00X_description.sql`
2. Write your SQL (use `DO $$ BEGIN ... END $$;` blocks for conditional logic)
3. Add comments at the top:
   ```sql
   -- Description of what this migration does
   -- Migration: 00X_description
   -- Date: YYYY-MM-DD
   ```

## Migration Tracking

The `schema_migrations` table tracks applied migrations:
- `version` - Migration number (e.g., "001")
- `name` - Migration filename
- `applied_at` - When it was applied

## Notes

- Each migration runs in a transaction (automatic rollback on error)
- Migrations are idempotent where possible (use `IF NOT EXISTS` checks)
- Never modify existing migration files after they've been applied
- Always test migrations on a dev database first

