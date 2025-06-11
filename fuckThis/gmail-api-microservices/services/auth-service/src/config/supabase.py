from supabase import create_client, Client
import os
from typing import Optional
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from pathlib import Path

logger = logging.getLogger(__name__)

# Load environment variables from multiple possible locations
def load_env_files():
    """Load .env files from multiple possible locations"""
    possible_env_paths = [
        Path(__file__).parent.parent.parent.parent.parent / '.env',  # /backend/.env
        Path(__file__).parent.parent.parent.parent / '.env',  # /services/.env
        Path(__file__).parent.parent.parent / '.env',  # /auth-service/.env
        Path(__file__).parent.parent / '.env',  # /src/.env
        Path(__file__).parent / '.env',  # /config/.env
        Path('.env')  # current directory
    ]
    
    for env_path in possible_env_paths:
        if env_path.exists():
            logger.info(f"Loading .env from: {env_path}")
            load_dotenv(env_path)
            break
    else:
        logger.warning("No .env file found in expected locations")

# Load environment variables
load_env_files()

class SupabaseConfig:
    def __init__(self):
        # Debug: Print current working directory and environment variables
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"SUPABASE_URL exists: {'SUPABASE_URL' in os.environ}")
        logger.info(f"SUPABASE_ANON_KEY exists: {'SUPABASE_ANON_KEY' in os.environ}")
        logger.info(f"SUPABASE_SERVICE_ROLE_KEY exists: {'SUPABASE_SERVICE_ROLE_KEY' in os.environ}")
        
        self.url = os.getenv("SUPABASE_URL")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.url:
            logger.error("SUPABASE_URL not found in environment variables")
        if not self.anon_key:
            logger.error("SUPABASE_ANON_KEY not found in environment variables")
        if not self.service_role_key:
            logger.error("SUPABASE_SERVICE_ROLE_KEY not found in environment variables")
            
        if not all([self.url, self.anon_key, self.service_role_key]):
            logger.error("Missing Supabase configuration. Available env vars:")
            for key, value in os.environ.items():
                if 'SUPABASE' in key:
                    logger.error(f"  {key}: {'SET' if value else 'NOT SET'}")
            raise ValueError("Missing Supabase configuration. Check your environment variables.")
        
        # Local database for Gmail credentials
        self.database_url = os.getenv("DATABASE_URL", "postgresql://gmail_user:secure_password_123@localhost:5432/gmail_api_db")
        
        # Setup local database
        try:
            self.engine = create_engine(self.database_url)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            logger.info("Database connection initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def get_client(self, service_role: bool = False) -> Client:
        """Get Supabase client - use service_role=True for admin operations"""
        key = self.service_role_key if service_role else self.anon_key
        return create_client(self.url, key)
    
    def get_db_session(self):
        """Get local database session"""
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()

# Global instances
supabase_config = SupabaseConfig()
supabase: Client = supabase_config.get_client()
admin_supabase: Client = supabase_config.get_client(service_role=True)