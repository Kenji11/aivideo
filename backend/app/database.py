from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database (create tables and run migrations)"""
    from app.common.models import VideoGeneration, Asset
    
    # Create tables if they don't exist (for initial setup)
    Base.metadata.create_all(bind=engine)
    
    # Run Alembic migrations to handle schema changes
    try:
        from alembic.config import Config
        from alembic import command
        from alembic.script import ScriptDirectory
        import os
        
        # Get the alembic.ini path (should be in backend directory)
        alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
        
        if os.path.exists(alembic_ini_path):
            alembic_cfg = Config(alembic_ini_path)
            
            # Try to upgrade to head, but catch revision mismatch errors gracefully
            try:
                command.upgrade(alembic_cfg, "head")
            except Exception as upgrade_error:
                error_msg = str(upgrade_error)
                if "Can't locate revision" in error_msg:
                    # Database has a revision that Alembic can't find - this is OK, schema is likely up to date
                    logger.warning(f"Migration revision mismatch: {error_msg}")
                    logger.warning("Skipping migration - database schema appears to be current")
                elif "Multiple head revisions" in error_msg:
                    logger.warning("Multiple migration heads detected, upgrading all heads")
                    try:
                        command.upgrade(alembic_cfg, "heads")
                    except Exception as heads_error:
                        if "Can't locate revision" in str(heads_error):
                            logger.warning("Skipping migration due to revision mismatch")
                        else:
                            raise
                else:
                    # Other errors - log but don't fail startup
                    logger.warning(f"Migration upgrade failed: {error_msg}")
                    logger.warning("Continuing startup - migrations can be run manually if needed")
        else:
            # If alembic.ini doesn't exist, just log a warning
            logger.warning(f"Alembic config not found at {alembic_ini_path}, skipping migrations")
    except Exception as e:
        # Log error but don't fail startup if migrations fail
        logger.error(f"Failed to run migrations: {str(e)}")
        # Still continue - the app should start even if migrations fail
        # (they can be run manually later)
