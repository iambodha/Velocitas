import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://gmail_user:secure_password_123@localhost:5432/gmail_api_db'
)

# Redis Configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
REDIS_DB = int(os.getenv('REDIS_DB', 0))

# JWT Configuration
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Gmail API Configuration
CLIENT_SECRET_PATH = os.getenv('GOOGLE_CLIENT_SECRET_PATH', '../client_secret.json')
REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:8080/callback')
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', 
    'https://www.googleapis.com/auth/userinfo.email', 
    'openid'
]

# Service URLs - Fixed: Use correct auth service port
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8001')
GMAIL_SERVICE_URL = os.getenv('GMAIL_SERVICE_URL', 'http://localhost:5001')
EMAIL_SERVICE_URL = os.getenv('EMAIL_SERVICE_URL', 'http://localhost:5002')
USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://localhost:5003')
EMAIL_SYNC_SERVICE_URL = os.getenv('EMAIL_SYNC_SERVICE_URL', 'http://localhost:8081')