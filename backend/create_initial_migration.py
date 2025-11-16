#!/usr/bin/env python3
"""
Helper script to create initial Alembic migration.
Run this once to establish the baseline, then Alembic will auto-detect future changes.
"""
import sys
import os
import subprocess

def main():
    """Create initial migration"""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)
    
    print("Creating initial Alembic migration...")
    print("This establishes the baseline for future auto-migrations.")
    
    # Create initial migration (empty, just to establish baseline)
    try:
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "Initial migration - baseline"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Initial migration created successfully!")
        print(result.stdout)
        
        # Now create migration for final_music_url
        print("\nCreating migration for final_music_url column...")
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "Add final_music_url column"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ final_music_url migration created!")
        print(result.stdout)
        
        print("\n📝 Next steps:")
        print("1. Review the migration files in alembic/versions/")
        print("2. The migrations will run automatically on next app startup")
        print("3. Or run manually: alembic upgrade head")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ Error: 'alembic' command not found.")
        print("Make sure you're in a virtual environment with dependencies installed:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

if __name__ == "__main__":
    main()

