"""
Security configuration and utilities for production deployment
"""

import os
import secrets
from typing import List
from fastapi.security import HTTPBearer
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi import Request, HTTPException
import time

class SecurityConfig:
    """Production security configuration"""
    
    # Generate secure JWT secret if not provided
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or secrets.token_urlsafe(64)
    
    # Security headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    # CORS configuration
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:3001", 
        "https://your-domain.com",  # Replace with your production domain
        os.getenv('FRONTEND_URL', 'http://localhost:3000')
    ]
    
    # Rate limiting settings
    RATE_LIMITS = {
        'login': {'max_attempts': 5, 'window_minutes': 15},
        'register': {'max_attempts': 3, 'window_minutes': 60},
        'refresh': {'max_attempts': 10, 'window_minutes': 5},
        'email_sync': {'max_attempts': 3, 'window_minutes': 10}
    }

class SecurityMiddleware:
    """Custom security middleware"""
    
    @staticmethod
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses"""
        response = await call_next(request)
        
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
            
        return response
    
    @staticmethod
    async def log_requests(request: Request, call_next):
        """Log all requests for security monitoring"""
        start_time = time.time()
        client_ip = request.client.host if request.client else "unknown"
        
        # Log the request
        print(f"🔍 {request.method} {request.url.path} from {client_ip}")
        
        response = await call_next(request)
        
        # Log response time
        process_time = time.time() - start_time
        print(f"⏱️  Processed in {process_time:.3f}s - Status: {response.status_code}")
        
        return response

def configure_production_security(app):
    """Configure security middleware for production"""
    
    # Add HTTPS redirect in production
    if os.getenv('ENVIRONMENT') == 'production':
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Add trusted host middleware
    trusted_hosts = ["localhost", "127.0.0.1", "your-domain.com"]  # Add your domains
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)
    
    # Add custom security middleware
    app.middleware("http")(SecurityMiddleware.add_security_headers)
    app.middleware("http")(SecurityMiddleware.log_requests)

def validate_environment():
    """Validate that all required environment variables are set"""
    required_vars = [
        'JWT_SECRET_KEY',
        'DATABASE_URL'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    print("✅ All required environment variables are set")

def generate_secure_key():
    """Generate a secure JWT key for production use"""
    return secrets.token_urlsafe(64)

if __name__ == "__main__":
    # Generate a new secure key
    print("🔐 Generated secure JWT key:")
    print(generate_secure_key())
    print("\n💡 Add this to your .env file as JWT_SECRET_KEY")