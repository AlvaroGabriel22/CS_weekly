"""Base response schemas"""
from typing import Generic, TypeVar, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

T = TypeVar('T')


class BaseResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool
    message: str = ""
    data: Optional[Any] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""
    items: List[T]
    total: int
    skip: int
    limit: int

    @property
    def pages(self) -> int:
        return (self.total + self.limit - 1) // self.limit


class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    status_code: int = 400


class TimestampedSchema(BaseModel):
    """Base schema with timestamps"""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
