from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import ApiListResponse


class WishlistCreate(BaseModel):
    """Used by employees to add a product to their wishlist."""

    product_id: UUID
    catalog_id: UUID | None = None
    notes: str | None = None


class WishlistProductInfo(BaseModel):
    """Nested product info for wishlist display."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sku: str
    image_urls: list[str] = []


class WishlistResponse(BaseModel):
    """Full wishlist entry representation for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    user_id: UUID
    product_id: UUID
    catalog_id: UUID | None
    notes: str | None
    product: WishlistProductInfo | None = None
    created_at: datetime
    updated_at: datetime


class WishlistSummary(BaseModel):
    """Lighter version for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    catalog_id: UUID | None
    notes: str | None
    product: WishlistProductInfo | None = None
    created_at: datetime


WishlistListResponse = ApiListResponse[WishlistSummary]
