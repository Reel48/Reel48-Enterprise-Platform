from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import ApiListResponse


class InvoiceCreate(BaseModel):
    """
    Used by reel48_admin to create an assigned or post-window invoice.

    NOTE: company_id is accepted here because this is a platform admin endpoint —
    the reel48_admin has no company_id of their own and must specify the target company.
    """

    company_id: UUID
    sub_brand_id: UUID | None = None
    order_id: UUID | None = None
    bulk_order_id: UUID | None = None
    catalog_id: UUID | None = None
    billing_flow: str
    due_date: date | None = None
    buying_window_closes_at: datetime | None = None

    @field_validator("billing_flow")
    @classmethod
    def billing_flow_must_be_valid(cls, v: str) -> str:
        valid = {"assigned", "self_service", "post_window"}
        if v not in valid:
            raise ValueError(f"billing_flow must be one of: {', '.join(sorted(valid))}")
        return v


class InvoiceResponse(BaseModel):
    """Full invoice representation for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    order_id: UUID | None
    bulk_order_id: UUID | None
    catalog_id: UUID | None
    stripe_invoice_id: str
    stripe_invoice_url: str | None
    stripe_pdf_url: str | None
    invoice_number: str | None
    billing_flow: str
    status: str
    total_amount: float
    currency: str
    due_date: date | None
    buying_window_closes_at: datetime | None
    created_by: UUID
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class InvoiceSummary(BaseModel):
    """Lighter version for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_number: str | None
    billing_flow: str
    status: str
    total_amount: float
    currency: str
    company_id: UUID
    sub_brand_id: UUID | None
    created_at: datetime
    paid_at: datetime | None


InvoiceListResponse = ApiListResponse[InvoiceSummary]
