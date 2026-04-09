"""Client-facing invoice endpoints (tenant-scoped).

These endpoints allow client company admins to VIEW their invoices.
Employees are denied access (403). Client admins can NEVER create,
edit, or send invoices — that's reel48_admin only (platform endpoints).

Authorization:
- corporate_admin: sees all invoices across all sub-brands in their company
- sub_brand_admin / regional_manager: sees invoices for their sub-brand only
- employee: NO access (403 on all invoice endpoints)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.invoice import InvoiceResponse, InvoiceSummary
from app.services.invoice_service import InvoiceService
from app.services.stripe_service import StripeService, get_stripe_service

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


def _require_invoice_access(context: TenantContext) -> None:
    """Guard: employees cannot access invoice endpoints."""
    if context.role == "employee":
        raise ForbiddenError("Employees do not have access to invoices")


@router.get("/", response_model=ApiListResponse[InvoiceSummary])
async def list_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    billing_flow: str | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[InvoiceSummary]:
    """List invoices for the authenticated company.

    - corporate_admin: sees all invoices across all sub-brands
    - sub_brand_admin / regional_manager: sees invoices for their sub-brand only
    - employee: 403
    """
    company_id = _require_company_id(context)
    _require_invoice_access(context)

    service = InvoiceService(db)
    invoices, total = await service.list_invoices(
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,  # None for corporate_admin → no sub-brand filter
        page=page,
        per_page=per_page,
        status=status,
        billing_flow=billing_flow,
    )
    return ApiListResponse(
        data=[InvoiceSummary.model_validate(i) for i in invoices],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{invoice_id}", response_model=ApiResponse[InvoiceResponse])
async def get_invoice(
    invoice_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[InvoiceResponse]:
    """Get invoice detail with tenant scoping.

    - corporate_admin: any invoice in their company
    - sub_brand_admin / regional_manager: invoices in their sub-brand only
    - employee: 403
    """
    company_id = _require_company_id(context)
    _require_invoice_access(context)

    service = InvoiceService(db)
    invoice = await service.get_invoice(
        invoice_id=invoice_id,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
    )
    return ApiResponse(data=InvoiceResponse.model_validate(invoice))


@router.get("/{invoice_id}/pdf", response_model=ApiResponse[dict])
async def get_invoice_pdf(
    invoice_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> ApiResponse[dict]:
    """Get the Stripe-hosted invoice PDF URL.

    Returns the cached stripe_pdf_url if available, otherwise fetches
    from Stripe and caches it on the local record.
    """
    company_id = _require_company_id(context)
    _require_invoice_access(context)

    service = InvoiceService(db, stripe_service=stripe_service)
    invoice = await service.get_invoice(
        invoice_id=invoice_id,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
    )

    pdf_url = invoice.stripe_pdf_url

    # If not cached locally, fetch from Stripe and cache
    if pdf_url is None and invoice.stripe_invoice_id:
        stripe_data = await stripe_service.get_invoice(invoice.stripe_invoice_id)
        pdf_url = stripe_data.get("invoice_pdf")
        if pdf_url:
            invoice.stripe_pdf_url = pdf_url
            await db.flush()
            await db.refresh(invoice)

    if pdf_url is None:
        raise NotFoundError("Invoice PDF", str(invoice_id))

    return ApiResponse(data={"invoice_id": str(invoice_id), "pdf_url": pdf_url})
