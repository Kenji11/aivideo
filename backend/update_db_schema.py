#!/usr/bin/env python3
"""
Update database schema to match current models.

This script:
1. Loads credentials from .env.prod
2. Connects to the database
3. Compares current schema with models
4. Applies necessary changes
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import ProgrammingError
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load .env.prod
env_prod_path = Path(__file__).parent / ".env.prod"
if env_prod_path.exists():
    load_dotenv(env_prod_path)
    logger.info(f"✅ Loaded .env.prod from {env_prod_path}")
else:
    logger.warning(f"⚠️  .env.prod not found at {env_prod_path}")
    logger.info("Trying to load from environment variables...")

# Get database URL
database_url = os.getenv("DATABASE_URL")
if not database_url:
    logger.error("DATABASE_URL not found in environment variables")
    sys.exit(1)

# Convert JDBC URL to SQLAlchemy format if needed
if database_url.startswith("jdbc:postgresql://"):
    database_url = database_url.replace("jdbc:postgresql://", "postgresql://")
    logger.info("Converted JDBC URL to SQLAlchemy format")

# Check if we need to add credentials from separate env vars
# If URL doesn't have @ (no credentials), try to get from separate env vars
if "@" not in database_url:
    # URL doesn't have credentials, check for separate env vars
    db_user = os.getenv("DB_USER") or os.getenv("DATABASE_USER") or os.getenv("POSTGRES_USER")
    db_password = os.getenv("DB_PASSWORD") or os.getenv("DATABASE_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
    
    if db_user and db_password:
        # Reconstruct URL with credentials
        if database_url.startswith("postgresql://"):
            # Extract host and database from URL
            url_parts = database_url.replace("postgresql://", "").split("/")
            if len(url_parts) >= 2:
                host_port = url_parts[0]
                database = url_parts[1]
                database_url = f"postgresql://{db_user}:{db_password}@{host_port}/{database}"
                logger.info("Added credentials from environment variables")
            else:
                logger.error("Could not parse database URL to add credentials")
                sys.exit(1)
        else:
            logger.error("Database URL format not recognized")
            sys.exit(1)
    else:
        logger.error("Database URL missing credentials and no DB_USER/DB_PASSWORD found in environment")
        logger.error("Please set DB_USER and DB_PASSWORD in .env.prod or include credentials in DATABASE_URL")
        sys.exit(1)

logger.info(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else '***'}")

# Create engine
engine = create_engine(database_url)

def get_current_columns(inspector, table_name):
    """Get current columns for a table"""
    try:
        columns = inspector.get_columns(table_name)
        return {col['name']: col for col in columns}
    except Exception as e:
        logger.error(f"Error getting columns for {table_name}: {e}")
        return {}

def get_current_enums(connection):
    """Get current ENUM types in the database"""
    query = text("""
        SELECT t.typname as enum_name, 
               array_agg(e.enumlabel ORDER BY e.enumsortorder) as enum_values
        FROM pg_type t 
        JOIN pg_enum e ON t.oid = e.enumtypid 
        WHERE t.typname IN ('assettype', 'assetsource', 'videostatus')
        GROUP BY t.typname;
    """)
    result = connection.execute(query)
    return {row[0]: row[1] for row in result}

def create_enum_if_not_exists(connection, enum_name, enum_values):
    """Create ENUM type if it doesn't exist"""
    current_enums = get_current_enums(connection)
    
    if enum_name in current_enums:
        current_values = current_enums[enum_name]
        if set(current_values) == set(enum_values):
            logger.info(f"✅ ENUM {enum_name} already exists with correct values")
            return False
        else:
            logger.warning(f"⚠️  ENUM {enum_name} exists but has different values")
            logger.warning(f"   Current: {current_values}")
            logger.warning(f"   Expected: {enum_values}")
            logger.warning("   Manual intervention may be required")
            return False
    
    # Create ENUM
    values_str = ", ".join([f"'{v}'" for v in enum_values])
    query = text(f"CREATE TYPE {enum_name} AS ENUM ({values_str})")
    connection.execute(query)
    connection.commit()
    logger.info(f"✅ Created ENUM {enum_name} with values: {enum_values}")
    return True

def update_table_schema(connection, inspector):
    """Update table schemas to match models"""
    
    # Define expected schemas based on models.py
    expected_assets = {
        'id': {'type': 'VARCHAR', 'nullable': False, 'primary_key': True},
        'user_id': {'type': 'VARCHAR', 'nullable': True},
        's3_key': {'type': 'VARCHAR', 'nullable': False},
        's3_url': {'type': 'VARCHAR', 'nullable': True},
        'asset_type': {'type': 'assettype', 'nullable': False},
        'source': {'type': 'assetsource', 'nullable': False},
        'file_name': {'type': 'VARCHAR', 'nullable': True},
        'file_size_bytes': {'type': 'INTEGER', 'nullable': True},
        'mime_type': {'type': 'VARCHAR', 'nullable': True},
        'asset_metadata': {'type': 'JSONB', 'nullable': True, 'default': "'{}'"},
        'created_at': {'type': 'TIMESTAMP WITH TIME ZONE', 'nullable': True, 'default': 'now()'},
    }
    
    expected_video_generations = {
        'id': {'type': 'VARCHAR', 'nullable': False, 'primary_key': True},
        'user_id': {'type': 'VARCHAR', 'nullable': True},
        'title': {'type': 'VARCHAR', 'nullable': False},
        'description': {'type': 'VARCHAR', 'nullable': True},
        'prompt': {'type': 'VARCHAR', 'nullable': False},
        'prompt_validated': {'type': 'VARCHAR', 'nullable': True},
        'reference_assets': {'type': 'JSONB', 'nullable': True, 'default': "'[]'"},
        'spec': {'type': 'JSONB', 'nullable': True},
        'template': {'type': 'VARCHAR', 'nullable': True},
        'status': {'type': 'videostatus', 'nullable': True, 'default': "'QUEUED'"},
        'progress': {'type': 'DOUBLE PRECISION', 'nullable': True, 'default': '0.0'},
        'current_phase': {'type': 'VARCHAR', 'nullable': True},
        'error_message': {'type': 'VARCHAR', 'nullable': True},
        'animatic_urls': {'type': 'JSONB', 'nullable': True, 'default': "'[]'"},
        'chunk_urls': {'type': 'JSONB', 'nullable': True, 'default': "'[]'"},
        'stitched_url': {'type': 'VARCHAR', 'nullable': True},
        'refined_url': {'type': 'VARCHAR', 'nullable': True},
        'final_video_url': {'type': 'VARCHAR', 'nullable': True},
        'final_music_url': {'type': 'VARCHAR', 'nullable': True},
        'phase_outputs': {'type': 'JSONB', 'nullable': True, 'default': "'{}'"},
        'cost_usd': {'type': 'DOUBLE PRECISION', 'nullable': True, 'default': '0.0'},
        'cost_breakdown': {'type': 'JSONB', 'nullable': True, 'default': "'{}'"},
        'generation_time_seconds': {'type': 'DOUBLE PRECISION', 'nullable': True},
        'created_at': {'type': 'TIMESTAMP WITH TIME ZONE', 'nullable': True, 'default': 'now()'},
        'completed_at': {'type': 'TIMESTAMP WITH TIME ZONE', 'nullable': True},
    }
    
    # Check and update assets table
    logger.info("\n" + "="*60)
    logger.info("Checking assets table...")
    logger.info("="*60)
    
    if 'assets' not in inspector.get_table_names():
        logger.info("Creating assets table...")
        create_assets_table(connection)
    else:
        current_columns = get_current_columns(inspector, 'assets')
        update_table(connection, 'assets', current_columns, expected_assets)
    
    # Check and update video_generations table
    logger.info("\n" + "="*60)
    logger.info("Checking video_generations table...")
    logger.info("="*60)
    
    if 'video_generations' not in inspector.get_table_names():
        logger.info("Creating video_generations table...")
        create_video_generations_table(connection)
    else:
        current_columns = get_current_columns(inspector, 'video_generations')
        
        # Add storyboard_images if it doesn't exist (migration 003)
        if 'storyboard_images' not in current_columns:
            logger.info("Adding storyboard_images column (from migration 003)...")
            try:
                connection.execute(text("ALTER TABLE video_generations ADD COLUMN storyboard_images JSONB"))
                connection.commit()
                logger.info("✅ Added storyboard_images column")
            except Exception as e:
                logger.error(f"Error adding storyboard_images: {e}")
        else:
            logger.info("✅ storyboard_images column already exists")
        
        update_table(connection, 'video_generations', current_columns, expected_video_generations)

def create_assets_table(connection):
    """Create assets table"""
    query = text("""
        CREATE TABLE assets (
            id VARCHAR NOT NULL,
            user_id VARCHAR,
            s3_key VARCHAR NOT NULL,
            s3_url VARCHAR,
            asset_type assettype NOT NULL,
            source assetsource NOT NULL,
            file_name VARCHAR,
            file_size_bytes INTEGER,
            mime_type VARCHAR,
            asset_metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (id)
        )
    """)
    connection.execute(query)
    connection.commit()
    logger.info("✅ Created assets table")

def create_video_generations_table(connection):
    """Create video_generations table"""
    query = text("""
        CREATE TABLE video_generations (
            id VARCHAR NOT NULL,
            user_id VARCHAR,
            title VARCHAR NOT NULL,
            description VARCHAR,
            prompt VARCHAR NOT NULL,
            prompt_validated VARCHAR,
            reference_assets JSONB DEFAULT '[]',
            spec JSONB,
            template VARCHAR,
            status videostatus DEFAULT 'QUEUED',
            progress DOUBLE PRECISION DEFAULT 0.0,
            current_phase VARCHAR,
            error_message VARCHAR,
            animatic_urls JSONB DEFAULT '[]',
            chunk_urls JSONB DEFAULT '[]',
            stitched_url VARCHAR,
            refined_url VARCHAR,
            final_video_url VARCHAR,
            final_music_url VARCHAR,
            phase_outputs JSONB DEFAULT '{}',
            cost_usd DOUBLE PRECISION DEFAULT 0.0,
            cost_breakdown JSONB DEFAULT '{}',
            generation_time_seconds DOUBLE PRECISION,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            completed_at TIMESTAMP WITH TIME ZONE,
            PRIMARY KEY (id)
        )
    """)
    connection.execute(query)
    connection.commit()
    logger.info("✅ Created video_generations table")

def update_table(connection, table_name, current_columns, expected_columns):
    """Update a table to match expected schema"""
    changes_made = False
    
    # Check for missing columns
    for col_name, col_spec in expected_columns.items():
        if col_name not in current_columns:
            logger.info(f"Adding missing column: {table_name}.{col_name}")
            add_column(connection, table_name, col_name, col_spec)
            changes_made = True
    
    # Check for extra columns (except storyboard_images which is handled separately)
    for col_name in current_columns:
        if col_name not in expected_columns and col_name != 'storyboard_images':
            logger.warning(f"⚠️  Extra column found: {table_name}.{col_name} (not in models)")
    
    if not changes_made:
        logger.info(f"✅ {table_name} table is up to date")

def add_column(connection, table_name, column_name, column_spec):
    """Add a column to a table"""
    col_type = column_spec['type']
    nullable = "NULL" if column_spec.get('nullable', True) else "NOT NULL"
    default = ""
    if 'default' in column_spec:
        default = f" DEFAULT {column_spec['default']}"
    
    query = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type} {nullable}{default}")
    try:
        connection.execute(query)
        connection.commit()
        logger.info(f"✅ Added column {table_name}.{column_name}")
    except Exception as e:
        logger.error(f"Error adding column {table_name}.{column_name}: {e}")
        connection.rollback()

def main():
    """Main function"""
    logger.info("="*60)
    logger.info("Database Schema Update Script")
    logger.info("="*60)
    
    try:
        with engine.connect() as connection:
            # Create ENUMs first
            logger.info("\nCreating/checking ENUM types...")
            create_enum_if_not_exists(connection, 'assettype', ['IMAGE', 'VIDEO', 'AUDIO'])
            create_enum_if_not_exists(connection, 'assetsource', ['USER_UPLOAD', 'SYSTEM_GENERATED'])
            create_enum_if_not_exists(connection, 'videostatus', [
                'QUEUED', 'VALIDATING', 'GENERATING_ANIMATIC', 'GENERATING_REFERENCES',
                'GENERATING_CHUNKS', 'REFINING', 'EXPORTING', 'COMPLETE', 'FAILED'
            ])
            
            # Update tables
            inspector = inspect(engine)
            update_table_schema(connection, inspector)
            
            logger.info("\n" + "="*60)
            logger.info("✅ Schema update complete!")
            logger.info("="*60)
            
    except Exception as e:
        logger.error(f"Error updating schema: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

