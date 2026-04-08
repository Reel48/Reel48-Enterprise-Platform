from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class OrderLineItemCreate(BaseModel):
    """What the client sends per line item when placing an order."""

    product_id: UUID
    quantity: int = 1
    size: str | None = None
    decoration: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


class OrderCreate(BaseModel):
    """What the client sends to place an order."""

    catalog_id: UUID
    line_items: list[OrderLineItemCreate]
    notes: str | None = None
    # Shipping address: if omitted, copied from employee profile
    shipping_address_line1: str | None = None
    shipping_address_line2: str | None = None
    shipping_city: str | None = None
    shipping_state: str | None = None
    shipping_zip: str | None = None
    shipping_country: str | None = None

    @field_validator("line_items")
    @classmethod
    def must_have_items(cls, v: list) -> list:
        if not v:
            raise ValueError("Order must have at least one line item")
        return v


class OrderLineItemResponse(BaseModel):
    """Line item in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    product_id: UUID
    product_name: str
    product_sku: str
    unit_price: float
    quantity: int
    size: str | None
    decoration: str | None
    line_total: float
    created_at: datetime
    updated_at: datetime


class OrderResponse(BaseModel):
    """Order in API responses (without line items)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    user_id: UUID
    catalog_id: UUID
    order_number: str
    status: str
    shipping_address_line1: str | None
    shipping_address_line2: str | None
    shipping_city: str | None
    shipping_state: str | None
    shipping_zip: str | None
    shipping_country: str | None
    notes: str | None
    subtotal: float
    total_amount: float
    cancelled_at: datetime | None
    cancelled_by: UUID | None
    created_at: datetime
    updated_at: datetime


class OrderWithItemsResponse(OrderResponse):
    """Order with nested line items for detail endpoints."""

    line_items: list[OrderLineItemResponse] = []
