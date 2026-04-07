from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response wrapper matching the format defined in root CLAUDE.md."""

    data: T
    meta: dict = {}
    errors: list[ErrorDetail] = []


class ApiListResponse(BaseModel, Generic[T]):
    """Standard API response wrapper for paginated list endpoints."""

    data: list[T]
    meta: PaginationMeta
    errors: list[ErrorDetail] = []


class ErrorResponse(BaseModel):
    """Standard error response format."""

    data: None = None
    errors: list[ErrorDetail]
