from sqlalchemy import create_engine, text
from .database import engine, SessionLocal
from .models.base import Base
import logging

logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize the database and create tables"""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False

def check_database_health():
    """Check database connection health"""
    try:
        with SessionLocal() as db:
            # Use text() to wrap the SQL query
            result = db.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()
            if row and row[0] == 1:
                logger.info("✅ Database health check passed")
                return True
            else:
                logger.error("❌ Database health check failed: Unexpected result")
                return False
    except Exception as e:
        logger.error(f"❌ Database health check failed: {e}")
        return False

if __name__ == "__main__":
    initialize_database()