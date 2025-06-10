from fastapi import APIRouter

from .routes import auth_router, users_router, connections_router, emails_router

api_router = APIRouter()

# Include all route modules
api_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    users_router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    connections_router,
    prefix="/connections",
    tags=["connections"]
)

api_router.include_router(
    emails_router,
    prefix="/emails",
    tags=["emails"]
)