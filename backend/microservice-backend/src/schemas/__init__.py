from .base import BaseSchema, PaginationSchema
from .user import (
    UserBase, UserCreate, UserUpdate, UserResponse, UserWithConnections,
    UserStats, LoginRequest, LoginResponse, TokenRefreshResponse
)
from .connection import (
    ConnectionBase, ConnectionCreate, ConnectionUpdate, ConnectionResponse,
    ConnectionWithStats, SyncStatusResponse, ConnectionStatusResponse, ProviderType
)
from .email import (
    EmailBase, EmailCreate, EmailUpdate, EmailResponse, EmailWithAttachments,
    EmailListResponse, EmailThreadResponse, EmailThreadWithMessages,
    EmailSearchRequest, EmailBulkUpdateRequest, EmailStatsResponse,
    EmailActionResponse, EmailPriority
)
from .attachment import (
    AttachmentBase, AttachmentCreate, AttachmentUpdate, AttachmentResponse,
    AttachmentDownloadResponse, FileType
)

__all__ = [
    # Base
    "BaseSchema", "PaginationSchema",
    
    # User schemas
    "UserBase", "UserCreate", "UserUpdate", "UserResponse", "UserWithConnections",
    "UserStats", "LoginRequest", "LoginResponse", "TokenRefreshResponse",
    
    # Connection schemas
    "ConnectionBase", "ConnectionCreate", "ConnectionUpdate", "ConnectionResponse",
    "ConnectionWithStats", "SyncStatusResponse", "ConnectionStatusResponse", "ProviderType",
    
    # Email schemas
    "EmailBase", "EmailCreate", "EmailUpdate", "EmailResponse", "EmailWithAttachments",
    "EmailListResponse", "EmailThreadResponse", "EmailThreadWithMessages",
    "EmailSearchRequest", "EmailBulkUpdateRequest", "EmailStatsResponse",
    "EmailActionResponse", "EmailPriority",
    
    # Attachment schemas
    "AttachmentBase", "AttachmentCreate", "AttachmentUpdate", "AttachmentResponse",
    "AttachmentDownloadResponse", "FileType"
]