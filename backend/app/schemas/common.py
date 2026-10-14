from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total_records: int
    page: int
    page_size: int
    total_pages: int

class MetaData(BaseModel):
    disclaimer: Optional[str] = None
    pagination: Optional[PaginationMeta] = None
    extra: Optional[dict[str, Any]] = None

class ResponseEnvelope(BaseModel, Generic[T]):
    data: T
    meta: Optional[dict[str, Any]] = Field(default_factory=dict)

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorEnvelope(BaseModel):
    error: ErrorDetail
