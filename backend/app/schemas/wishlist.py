from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta


class WishlistCreate(BaseModel):
    """Used by employees to add a product to their wishlist."""

    product_id: UUID
    catalog_id: UUID | None = None
    notes: str | None = None


class WishlistResponse(BaseModel):
    """Full wishlist entry with nested product details for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    catalog_id: UUID | None
    product_name: str
    product_sku: str
    product_unit_price: float
    product_image_url: str | None
    product_status: str
    is_purchasable: bool
    notes: str | None
    created_at: datetime


class WishlistCheckRequest(BaseModel):
    """Request body for checking if products are in the user's wishlist."""

    product_ids: list[UUID]


class WishlistCheckResponse(BaseModel):
    """Response for the wishlist check endpoint."""

    model_config = ConfigDict(from_attributes=True)


WishlistListResponse = ApiListResponse[WishlistResponse]
