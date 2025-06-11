from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from ..config.settings import DATABASE_URL

Base = declarative_base()

# Database engine and session
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create database tables if they don't exist"""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")

def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Re-export for convenience
__all__ = ['Base', 'engine', 'SessionLocal', 'get_db', 'create_tables']