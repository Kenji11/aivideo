# Database Migration Guide

## For New Developers

When you first clone this repository and set up your local environment, you need to run database migrations to create the proper schema.

### Quick Start

```bash
# 1. Start the database
docker-compose up -d postgres

# 2. Run migrations (either method works)

# Option A: Using Docker
docker-compose run --rm api alembic upgrade head

# Option B: Using local Python (if you have venv activated)
cd backend
source venv/bin/activate  # or activate based on your shell
alembic upgrade head
```

### When Pulling New Code

Always check for new migrations after pulling from main:

```bash
# Check if there are pending migrations
alembic current  # Shows current migration
alembic heads    # Shows latest available migration

# Apply new migrations
alembic upgrade head
```

### Common Issues

#### "relation does not exist" error
- **Cause**: Migrations haven't been run
- **Fix**: Run `alembic upgrade head`

#### "column does not exist" error (like `final_music_url`)
- **Cause**: Your database schema is out of sync with the code
- **Fix**: Run `alembic upgrade head` to apply new migrations

#### Migration conflicts
- **Cause**: Multiple people created migrations at the same time
- **Fix**: Coordinate with team to merge migrations properly

### Creating Migrations

When you modify models in `app/common/models.py`:

```bash
# 1. Make your changes to the model
# 2. Generate migration (auto-detect changes)
alembic revision --autogenerate -m "add new column to table"

# 3. Review the generated file in alembic/versions/
#    The autogenerate is smart but not perfect - always review!

# 4. Test the migration
alembic upgrade head

# 5. Test the downgrade (optional but recommended)
alembic downgrade -1  # Go back one migration
alembic upgrade head  # Apply again
```

### Migration File Naming

Alembic generates filenames like: `<revision_id>_<description>.py`

Example: `001_initial_schema.py`

### Best Practices

1. ✅ **DO** run migrations before starting development
2. ✅ **DO** create migrations for every model change
3. ✅ **DO** test both upgrade and downgrade
4. ✅ **DO** commit migration files to git
5. ❌ **DON'T** delete committed migration files
6. ❌ **DON'T** modify migration files after they're merged to main
7. ❌ **DON'T** run `Base.metadata.create_all()` - use migrations instead

### Rolling Back

To undo the last migration:

```bash
# Go back one migration
alembic downgrade -1

# Go back to a specific revision
alembic downgrade <revision_id>

# Go back to initial state (WARNING: drops all tables)
alembic downgrade base
```

### Migration History

View migration history:

```bash
# Show current migration
alembic current

# Show all migrations
alembic history

# Show pending migrations
alembic history --verbose
```

## Production Deployments

Migrations run automatically via Docker entrypoint script on container startup.

The deployment process:
1. New container starts
2. `docker-entrypoint.sh` runs `alembic upgrade head`
3. Application starts after successful migration

### Zero-Downtime Migrations

For production changes that need zero downtime:

1. **Adding columns**: Add as nullable first, then make non-nullable in a later migration
2. **Removing columns**: Deprecate first, deploy code that doesn't use it, then remove in later migration
3. **Renaming columns**: Create new column, copy data, deprecate old column, remove in later migration

## Troubleshooting

### Reset Local Database

If your local database is completely out of sync:

```bash
# Nuclear option: drop everything and start fresh
docker-compose down -v  # -v removes volumes (deletes data!)
docker-compose up -d postgres
alembic upgrade head
```

### Check Migration Status

```bash
# What migration am I on?
alembic current

# What's the latest migration?
alembic heads

# Show full history
alembic history
```

### Manual SQL (Last Resort)

If you really need to manually fix something:

```bash
# Connect to database
docker-compose exec postgres psql -U dev -d videogen

# Check tables
\dt

# Check columns
\d video_generations

# Exit
\q
```

## Questions?

Contact the team lead or check the [main README](README.md) for more information.

