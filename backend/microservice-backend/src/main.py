from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import time
import logging
from contextlib import asynccontextmanager
import sys
import os

# Add the current directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now import our modules
from core.config import settings
from core.redis import redis_client
from database.connection import engine, get_db
from database.models import Base
from api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up Email Microservice...")
    
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        # Don't raise here for now to allow startup without DB
        logger.warning("⚠️  Continuing without database...")
    
    # Test Redis connection
    try:
        if redis_client._connect():
            logger.info("✅ Redis connection established")
        else:
            logger.warning("⚠️  Redis not available - continuing without cache")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")
        logger.warning("⚠️  Continuing without Redis...")
    
    logger.info("🚀 Email Microservice started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Email Microservice...")
    logger.info("👋 Email Microservice shutdown complete")

# Create FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A comprehensive email management microservice with Gmail, Outlook, and IMAP support",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host Middleware
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests"""
    start_time = time.time()
    
    # Log request
    logger.info(f"📥 {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"📤 {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.4f}s"
    )
    
    return response

# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Exception",
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation Error",
            "detail": "Request validation failed",
            "errors": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    if settings.DEBUG:
        # In debug mode, show the actual error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # In production, show generic error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": "An unexpected error occurred"
            }
        )

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_status = "unknown"
    redis_status = "unknown"
    
    try:
        # Check database
        with get_db() as db:
            db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    try:
        # Check Redis
        if redis_client._connect() and redis_client.client:
            redis_client.client.ping()
            redis_status = "healthy"
        else:
            redis_status = "unavailable"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    overall_status = "healthy" if db_status == "healthy" else "degraded"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "services": {
            "database": db_status,
            "redis": redis_status
        },
        "version": "1.0.0"
    }

@app.get("/health/database")
async def database_health():
    """Database-specific health check"""
    try:
        with get_db() as db:
            result = db.execute("SELECT current_database(), version()")
            db_info = result.fetchone()
        
        return {
            "status": "healthy",
            "database": db_info[0] if db_info else "unknown",
            "version": db_info[1] if db_info else "unknown"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unhealthy")

@app.get("/health/redis")
async def redis_health():
    """Redis-specific health check"""
    try:
        if redis_client._connect() and redis_client.client:
            redis_info = redis_client.client.info()
            return {
                "status": "healthy",
                "redis_version": redis_info.get("redis_version"),
                "used_memory": redis_info.get("used_memory_human"),
                "connected_clients": redis_info.get("connected_clients")
            }
        else:
            raise HTTPException(status_code=503, detail="Redis not available")
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        raise HTTPException(status_code=503, detail="Redis unhealthy")

# API status endpoint
@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Email Microservice API",
        "version": "1.0.0",
        "status": "running",
        "docs": f"{settings.API_V1_STR}/docs",
        "redoc": f"{settings.API_V1_STR}/redoc"
    }

@app.get("/status")
async def api_status():
    """Detailed API status"""
    return {
        "service": "Email Microservice",
        "version": "1.0.0",
        "status": "operational",
        "environment": "development" if settings.DEBUG else "production",
        "features": [
            "Gmail Integration",
            "Outlook Integration", 
            "IMAP Support",
            "Email Search",
            "Real-time Sync",
            "AI-powered Features"
        ],
        "endpoints": {
            "auth": f"{settings.API_V1_STR}/auth",
            "users": f"{settings.API_V1_STR}/users",
            "connections": f"{settings.API_V1_STR}/connections",
            "emails": f"{settings.API_V1_STR}/emails"
        }
    }

# Include API routes
try:
    app.include_router(api_router, prefix=settings.API_V1_STR)
    logger.info("✅ API routes loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load API routes: {e}")
    logger.warning("⚠️  API routes not available")

# Development-only routes
if settings.DEBUG:
    @app.get("/debug/redis-keys")
    async def debug_redis_keys():
        """Debug endpoint to see Redis keys"""
        try:
            if redis_client._connect() and redis_client.client:
                keys = redis_client.client.keys("*")
                return {"keys": keys, "count": len(keys)}
            else:
                return {"message": "Redis not available", "keys": [], "count": 0}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Redis error: {e}")
    
    @app.post("/debug/clear-cache")
    async def debug_clear_cache():
        """Debug endpoint to clear Redis cache"""
        try:
            if redis_client._connect() and redis_client.client:
                redis_client.flush_db()
                return {"message": "Cache cleared successfully"}
            else:
                return {"message": "Redis not available - no cache to clear"}
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Redis error: {e}")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )