from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductBase(BaseModel):
    """Shared fields for product creation and response."""

    name: str
    description: str | None = None
    sku: str
    unit_price: float


class ProductCreate(ProductBase):
    """Used for POST /products. Server sets id, status, created_by, timestamps."""

    sizes: list[str] = []
    decoration_options: list[str] = []
    image_urls: list[str] = []


class ProductUpdate(BaseModel):
    """Used for PATCH /products/{id}. All fields optional for partial updates."""

    name: str | None = None
    description: str | None = None
    sku: str | None = None
    unit_price: float | None = None
    sizes: list[str] | None = None
    decoration_options: list[str] | None = None
    image_urls: list[str] | None = None


class ProductResponse(BaseModel):
    """Used in API responses. Includes server-generated fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    name: str
    description: str | None
    sku: str
    unit_price: float
    sizes: list
    decoration_options: list
    image_urls: list
    status: str
    approved_by: UUID | None
    approved_at: datetime | None
    created_by: UUID
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime
