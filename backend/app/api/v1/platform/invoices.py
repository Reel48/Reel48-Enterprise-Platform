"""Platform admin endpoints for invoice management.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.exceptions import ValidationError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceSummary
from app.services.helpers import resolve_current_user_id
from app.services.invoice_service import InvoiceService
from app.services.stripe_service import StripeService, get_stripe_service

router = APIRouter(prefix="/platform/invoices", tags=["platform-invoices"])


@router.post("/", response_model=ApiResponse[InvoiceResponse], status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> ApiResponse[InvoiceResponse]:
    """Create a draft invoice for a client company.

    billing_flow must be 'assigned' or 'post_window' (self_service is auto-generated).
    - assigned: at least one of order_ids or bulk_order_ids is required.
    - post_window: catalog_id is required; catalog must have payment_model =
      'invoice_after_close' and the buying window must have closed.
    """
    created_by = await resolve_current_user_id(db, context.user_id)
    service = InvoiceService(db, stripe_service=stripe_service)

    if body.billing_flow == "assigned":
        if not body.order_ids and not body.bulk_order_ids:
            raise ValidationError(
                "At least one order_id or bulk_order_id is required for assigned invoices"
            )
        invoice = await service.create_assigned_invoice(
            company_id=body.company_id,
            created_by=created_by,
            order_ids=body.order_ids,
            bulk_order_ids=body.bulk_order_ids,
            sub_brand_id=body.sub_brand_id,
        )
    elif body.billing_flow == "post_window":
        if not body.catalog_id:
            raise ValidationError(
                "catalog_id is required for post_window invoices"
            )
        invoice = await service.create_post_window_invoice(
            catalog_id=body.catalog_id,
            created_by=created_by,
        )
    else:
        raise ValidationError(f"Unsupported billing_flow: {body.billing_flow}")

    # Set due_date if provided (not handled by the service layer)
    if body.due_date is not None:
        invoice.due_date = body.due_date
        await db.flush()
        await db.refresh(invoice)

    return ApiResponse(data=InvoiceResponse.model_validate(invoice))


@router.post(
    "/{invoice_id}/finalize",
    response_model=ApiResponse[InvoiceResponse],
)
async def finalize_invoice(
    invoice_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> ApiResponse[InvoiceResponse]:
    """Finalize a draft invoice. Stripe assigns an invoice number."""
    service = InvoiceService(db, stripe_service=stripe_service)
    invoice = await service.finalize_invoice(invoice_id)
    return ApiResponse(data=InvoiceResponse.model_validate(invoice))


@router.post(
    "/{invoice_id}/send",
    response_model=ApiResponse[InvoiceResponse],
)
async def send_invoice(
    invoice_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> ApiResponse[InvoiceResponse]:
    """Send a finalized invoice to the client company."""
    service = InvoiceService(db, stripe_service=stripe_service)
    invoice = await service.send_invoice(invoice_id)
    return ApiResponse(data=InvoiceResponse.model_validate(invoice))


@router.post(
    "/{invoice_id}/void",
    response_model=ApiResponse[InvoiceResponse],
)
async def void_invoice(
    invoice_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
    stripe_service: StripeService = Depends(get_stripe_service),
) -> ApiResponse[InvoiceResponse]:
    """Void a draft, finalized, or sent invoice."""
    service = InvoiceService(db, stripe_service=stripe_service)
    invoice = await service.void_invoice(invoice_id)
    return ApiResponse(data=InvoiceResponse.model_validate(invoice))


@router.get("/", response_model=ApiListResponse[InvoiceSummary])
async def list_all_invoices(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    company_id: UUID | None = Query(None),
    status: str | None = Query(None),
    billing_flow: str | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[InvoiceSummary]:
    """List all invoices across all companies with optional filters."""
    service = InvoiceService(db)
    invoices, total = await service.list_all_invoices(
        company_id=company_id,
        status=status,
        billing_flow=billing_flow,
        page=page,
        per_page=per_page,
    )
    return ApiListResponse(
        data=[InvoiceSummary.model_validate(i) for i in invoices],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{invoice_id}", response_model=ApiResponse[InvoiceResponse])
async def get_invoice(
    invoice_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[InvoiceResponse]:
    """Get a single invoice by ID (cross-company)."""
    service = InvoiceService(db)
    invoice = await service.get_invoice_by_id(invoice_id)
    return ApiResponse(data=InvoiceResponse.model_validate(invoice))
