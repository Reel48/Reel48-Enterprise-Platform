"""Platform admin endpoints for product approval workflow.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.product import ProductResponse
from app.services.approval_service import ApprovalService
from app.services.email_service import EmailService, get_email_service
from app.services.helpers import resolve_current_user_id
from app.services.product_service import ProductService

router = APIRouter(prefix="/platform/products", tags=["platform-products"])


class RejectRequest(BaseModel):
    rejection_reason: str | None = None


@router.get("/", response_model=ApiListResponse[ProductResponse])
async def list_all_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    company_id: UUID | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[ProductResponse]:
    """List ALL products across all companies. Supports status and company_id filters."""
    service = ProductService(db)
    products, total = await service.list_all_products(
        page, per_page, status_filter=status, company_id_filter=company_id
    )
    return ApiListResponse(
        data=[ProductResponse.model_validate(p) for p in products],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.post("/{product_id}/approve", response_model=ApiResponse[ProductResponse])
async def approve_product(
    product_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
    email_service: EmailService = Depends(get_email_service),
) -> ApiResponse[ProductResponse]:
    """Approve a submitted product. Transitions: submitted -> approved."""
    approved_by = await resolve_current_user_id(db, context.user_id)
    service = ProductService(db)
    product = await service.approve_product(product_id, approved_by)

    # Sync: also update the corresponding approval_request if one exists
    approval_svc = ApprovalService(db, email_service=email_service)
    ar = await approval_svc.find_by_entity("product", product_id)
    if ar is not None:
        from datetime import UTC, datetime

        ar.decided_by = approved_by  # type: ignore[assignment]
        ar.decided_at = datetime.now(UTC)  # type: ignore[assignment]
        ar.status = "approved"  # type: ignore[assignment]
        await db.flush()

        await approval_svc._notify_submitter(
            entity_type="product",
            entity_id=product_id,
            requested_by=ar.requested_by,
            decided_by=approved_by,
            decision="approved",
            decision_notes=None,
        )

    return ApiResponse(data=ProductResponse.model_validate(product))


@router.post("/{product_id}/reject", response_model=ApiResponse[ProductResponse])
async def reject_product(
    product_id: UUID,
    body: RejectRequest | None = None,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
    email_service: EmailService = Depends(get_email_service),
) -> ApiResponse[ProductResponse]:
    """Reject a submitted product back to draft. Transitions: submitted -> draft."""
    rejected_by = await resolve_current_user_id(db, context.user_id)
    service = ProductService(db)
    product = await service.reject_product(product_id)

    # Sync: also update the corresponding approval_request if one exists
    approval_svc = ApprovalService(db, email_service=email_service)
    ar = await approval_svc.find_by_entity("product", product_id)
    if ar is not None:
        from datetime import UTC, datetime
        rejection_reason = body.rejection_reason if body else None

        ar.decided_by = rejected_by  # type: ignore[assignment]
        ar.decided_at = datetime.now(UTC)  # type: ignore[assignment]
        ar.status = "rejected"  # type: ignore[assignment]
        ar.decision_notes = rejection_reason  # type: ignore[assignment]
        await db.flush()

        await approval_svc._notify_submitter(
            entity_type="product",
            entity_id=product_id,
            requested_by=ar.requested_by,
            decided_by=rejected_by,
            decision="rejected",
            decision_notes=rejection_reason,
        )

    return ApiResponse(data=ProductResponse.model_validate(product))


@router.post("/{product_id}/activate", response_model=ApiResponse[ProductResponse])
async def activate_product(
    product_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    """Activate an approved product. Transitions: approved -> active."""
    service = ProductService(db)
    product = await service.activate_product(product_id)
    return ApiResponse(data=ProductResponse.model_validate(product))
