#!/usr/bin/env python3
"""
Simple database migration runner for raw SQL migrations.
No external dependencies - uses psycopg2 directly.
"""
import sys
import os
from pathlib import Path
import psycopg2
from psycopg2 import sql
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))
from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

def get_connection():
    """Get database connection"""
    settings = get_settings()
    # Parse database URL (format: postgresql://user:pass@host:port/dbname)
    db_url = settings.database_url
    return psycopg2.connect(db_url)

def ensure_migrations_table(conn):
    """Create schema_migrations table if it doesn't exist"""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(10) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                applied_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    conn.commit()

def get_applied_migrations(conn):
    """Get list of applied migration versions"""
    with conn.cursor() as cur:
        cur.execute("SELECT version FROM schema_migrations ORDER BY version")
        return {row[0] for row in cur.fetchall()}

def get_migration_files():
    """Get all migration files sorted by version"""
    if not MIGRATIONS_DIR.exists():
        print(f"❌ Migrations directory not found: {MIGRATIONS_DIR}")
        sys.exit(1)
    
    migrations = []
    for file in MIGRATIONS_DIR.glob("*.sql"):
        if file.name == "README.md":
            continue
        # Extract version number (e.g., "001" from "001_initial_schema.sql")
        version = file.stem.split("_")[0]
        migrations.append((version, file.name, file))
    
    return sorted(migrations, key=lambda x: x[0])

def run_migration(conn, version, name, filepath):
    """Run a single migration file"""
    print(f"  Running {name}...", end=" ")
    
    with open(filepath, 'r') as f:
        sql_content = f.read()
    
    try:
        with conn.cursor() as cur:
            # Execute the migration SQL
            cur.execute(sql_content)
            
            # Record that we applied this migration
            cur.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                (version, name)
            )
        conn.commit()
        print("✅")
        return True
    except Exception as e:
        conn.rollback()
        print(f"❌")
        print(f"    Error: {e}")
        return False

def cmd_up(conn):
    """Run all pending migrations"""
    ensure_migrations_table(conn)
    applied = get_applied_migrations(conn)
    migrations = get_migration_files()
    
    pending = [(v, n, f) for v, n, f in migrations if v not in applied]
    
    if not pending:
        print("✅ Database is up to date - no pending migrations")
        return
    
    print(f"📦 Running {len(pending)} pending migration(s):")
    
    for version, name, filepath in pending:
        if not run_migration(conn, version, name, filepath):
            print(f"\n❌ Migration failed, stopping")
            sys.exit(1)
    
    print(f"\n✅ Successfully applied {len(pending)} migration(s)")

def cmd_status(conn):
    """Show migration status"""
    ensure_migrations_table(conn)
    applied = get_applied_migrations(conn)
    migrations = get_migration_files()
    
    print("\n📊 Migration Status:")
    print("-" * 60)
    
    if not migrations:
        print("  No migration files found")
        return
    
    for version, name, filepath in migrations:
        status = "✅ Applied" if version in applied else "⏳ Pending"
        print(f"  {version}: {name:<45} {status}")
    
    print("-" * 60)
    pending_count = len([v for v, _, _ in migrations if v not in applied])
    print(f"  Total: {len(migrations)} | Applied: {len(applied)} | Pending: {pending_count}")
    print()

def cmd_down(conn):
    """Rollback last migration (not implemented yet)"""
    print("❌ Rollback not implemented yet")
    print("   To rollback, manually write and run the reverse SQL")
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python migrate.py [up|down|status]")
        print()
        print("Commands:")
        print("  up      - Run all pending migrations")
        print("  status  - Show migration status")
        print("  down    - Rollback last migration (not implemented)")
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        conn = get_connection()
        
        if command == "up":
            cmd_up(conn)
        elif command == "status":
            cmd_status(conn)
        elif command == "down":
            cmd_down(conn)
        else:
            print(f"❌ Unknown command: {command}")
            sys.exit(1)
        
        conn.close()
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

