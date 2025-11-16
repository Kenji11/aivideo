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
        import os
        
        # Get the alembic.ini path (should be in backend directory)
        alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
        
        if os.path.exists(alembic_ini_path):
            alembic_cfg = Config(alembic_ini_path)
            # Run all pending migrations
            # Use "heads" to upgrade all heads if multiple exist, otherwise "head" for single head
            try:
                command.upgrade(alembic_cfg, "head")
            except Exception as head_error:
                # If "head" fails due to multiple heads, try "heads" instead
                if "Multiple head revisions" in str(head_error):
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning("Multiple migration heads detected, upgrading all heads")
                    command.upgrade(alembic_cfg, "heads")
                else:
                    raise
        else:
            # If alembic.ini doesn't exist, just log a warning
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Alembic config not found at {alembic_ini_path}, skipping migrations")
    except Exception as e:
        # Log error but don't fail startup if migrations fail
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to run migrations: {str(e)}")
        # Still continue - the app should start even if migrations fail
        # (they can be run manually later)
