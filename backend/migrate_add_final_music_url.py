#!/usr/bin/env python3
"""
Migration script to add final_music_url column to video_generations table.
Run this script to fix the 500 error on /api/status endpoint.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from app.config import get_settings

def run_migration():
    """Add final_music_url column if it doesn't exist"""
    try:
        settings = get_settings()
        engine = create_engine(settings.database_url)
        
        print("Connecting to database...")
        with engine.connect() as conn:
            print("Adding final_music_url column...")
            conn.execute(text(
                "ALTER TABLE video_generations "
                "ADD COLUMN IF NOT EXISTS final_music_url VARCHAR"
            ))
            conn.commit()
            print("✅ Migration successful: final_music_url column added")
            return True
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)

