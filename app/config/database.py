from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging
from app.config.settings import settings
from app.models.base import Base

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DB_URL,
    pool_pre_ping=True,   # drops the dead connections if exists
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    """
    Initialize database schema.
    - Creates emp_ai schema if it doesn't exist
    - Enables pgvector extension
    - Creates all tables
    """
    try:
        with engine.begin() as conn:
            # Create pgvector extension
            logger.info("Enabling pgvector extension...")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            
            # Create emp_ai schema
            logger.info("Creating emp_ai schema...")
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS emp_ai"))
            conn.commit()
            
        # Create all tables
        logger.info("Creating tables in emp_ai schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise


def drop_all_tables():
    """Drop all tables (use with caution)."""
    try:
        logger.warning("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped")
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency — yields a scoped DB session per request.

    Usage in a route:
        @router.post("/run")
        async def run(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
