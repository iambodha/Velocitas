from pydantic_settings import BaseSettings
from typing import List, Optional
import os

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Email Microservice"
    DEBUG: bool = True
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/emaildb"
    DATABASE_ECHO: bool = False
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Session Configuration
    SESSION_TTL: int = 86400  # 24 hours in seconds
    SESSION_PREFIX: str = "session"
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Gmail API Configuration
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/gmail/callback"
    
    # Outlook API Configuration
    OUTLOOK_CLIENT_ID: Optional[str] = None
    OUTLOOK_CLIENT_SECRET: Optional[str] = None
    OUTLOOK_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/outlook/callback"
    
    # Cache settings
    CACHE_TTL: int = 3600
    CACHE_PREFIX: str = "email_service"
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 3600
    
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://:redis123@localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://:redis123@localhost:6379/2"
    
    # File Upload Configuration
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB in bytes
    
    # AI/ML Configuration
    OPENAI_API_KEY: Optional[str] = "your-openai-api-key"
    EMBEDDING_MODEL: str = "text-embedding-ada-002"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Allow extra fields from .env file
        extra = "ignore"  # This will ignore extra fields instead of raising an error

# Create the settings instance
settings = Settings()