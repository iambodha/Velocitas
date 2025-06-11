from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class BaseSchema(BaseModel):
    """Base schema with common fields"""
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class PaginationSchema(BaseModel):
    """Pagination metadata"""
    page: int = Field(1, ge=1, description="Current page number")
    per_page: int = Field(50, ge=1, le=100, description="Items per page")
    total: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there's a next page")
    has_prev: bool = Field(..., description="Whether there's a previous page")