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
    """Initialize database tables
    
    Note: This uses SQLAlchemy's create_all() which only creates missing tables.
    For schema changes, use the migration system: python migrate.py up
    """
    from app.common.models import VideoGeneration, Asset
    
    # Create tables if they don't exist (for initial setup)
    # This is safe to run multiple times - it only creates missing tables
    Base.metadata.create_all(bind=engine)
