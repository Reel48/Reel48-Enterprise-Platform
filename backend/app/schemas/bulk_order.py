from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class BulkOrderCreate(BaseModel):
    """Create a new bulk order session (draft)."""

    catalog_id: UUID
    title: str
    description: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()


class BulkOrderUpdate(BaseModel):
    """Update a draft bulk order session. All fields optional for partial update."""

    title: str | None = None
    description: str | None = None
    notes: str | None = None

    @field_validator("title")
    @classmethod
    def title_not_empty_if_provided(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v is not None else v


class BulkOrderItemCreate(BaseModel):
    """Add an item to a bulk order session."""

    product_id: UUID
    employee_id: UUID | None = None
    quantity: int = 1
    size: str | None = None
    decoration: str | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


class BulkOrderItemUpdate(BaseModel):
    """Update an item within a draft bulk order. All fields optional."""

    employee_id: UUID | None = None
    quantity: int | None = None
    size: str | None = None
    decoration: str | None = None
    notes: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive_if_provided(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


class BulkOrderItemResponse(BaseModel):
    """Bulk order item in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bulk_order_id: UUID
    employee_id: UUID | None
    product_id: UUID
    product_name: str
    product_sku: str
    unit_price: float
    quantity: int
    size: str | None
    decoration: str | None
    line_total: float
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BulkOrderResponse(BaseModel):
    """Bulk order session in API responses (without items)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    catalog_id: UUID
    created_by: UUID
    title: str
    description: str | None
    order_number: str
    status: str
    total_items: int
    total_amount: float
    submitted_at: datetime | None
    approved_by: UUID | None
    approved_at: datetime | None
    cancelled_at: datetime | None
    cancelled_by: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class BulkOrderWithItemsResponse(BulkOrderResponse):
    """Bulk order session with nested items for detail endpoints."""

    items: list[BulkOrderItemResponse] = []
