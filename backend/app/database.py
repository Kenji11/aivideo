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
    """Initialize database (create tables)
    
    NOTE: With Alembic migrations enabled, this function is deprecated.
    Tables are now created via: alembic upgrade head
    
    This function is kept for backwards compatibility but does nothing.
    """
    # Migrations handle schema creation now
    # Base.metadata.create_all(bind=engine)
    pass
