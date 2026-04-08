from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class CatalogBase(BaseModel):
    """Shared fields for catalog creation and response."""

    name: str
    description: str | None = None


class CatalogCreate(CatalogBase):
    """Used for POST /catalogs. Server sets id, slug, status, created_by, timestamps."""

    payment_model: str
    buying_window_opens_at: datetime | None = None
    buying_window_closes_at: datetime | None = None

    @model_validator(mode="after")
    def validate_buying_window(self) -> "CatalogCreate":
        if self.payment_model == "invoice_after_close":
            if self.buying_window_opens_at is None or self.buying_window_closes_at is None:
                raise ValueError(
                    "buying_window_opens_at and buying_window_closes_at are required "
                    "for invoice_after_close payment model"
                )
        elif self.payment_model == "self_service":
            if self.buying_window_opens_at is not None or self.buying_window_closes_at is not None:
                raise ValueError(
                    "buying_window_opens_at and buying_window_closes_at must not be set "
                    "for self_service payment model"
                )
        else:
            raise ValueError(
                f"Invalid payment_model: {self.payment_model}. "
                "Must be 'self_service' or 'invoice_after_close'"
            )
        return self


class CatalogUpdate(BaseModel):
    """Used for PATCH /catalogs/{id}. All fields optional for partial updates.
    payment_model is NOT updatable (set at creation)."""

    name: str | None = None
    description: str | None = None
    buying_window_opens_at: datetime | None = None
    buying_window_closes_at: datetime | None = None


class CatalogResponse(BaseModel):
    """Used in API responses. Includes server-generated fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    name: str
    description: str | None
    slug: str
    payment_model: str
    status: str
    buying_window_opens_at: datetime | None
    buying_window_closes_at: datetime | None
    approved_by: UUID | None
    approved_at: datetime | None
    created_by: UUID
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CatalogProductAdd(BaseModel):
    """Used for POST /catalogs/{id}/products/. Adds a product to a catalog."""

    product_id: UUID
    display_order: int = 0
    price_override: float | None = None


class CatalogProductResponse(BaseModel):
    """Response for catalog-product junction entries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    catalog_id: UUID
    product_id: UUID
    display_order: int
    price_override: float | None
    company_id: UUID
    sub_brand_id: UUID | None
    created_at: datetime
    updated_at: datetime
