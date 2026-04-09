"""Platform admin endpoints for cross-company approval visibility and management.

All endpoints require reel48_admin role. These operate cross-company --
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalQueueItem,
    ApprovalRequestResponse,
    ApprovalSummaryResponse,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.approval_service import ApprovalService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/platform/approvals", tags=["platform-approvals"])


@router.get("/", response_model=ApiListResponse[ApprovalRequestResponse])
async def list_all_approvals(
    status: str | None = Query(None),
    entity_type: str | None = Query(None),
    company_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[ApprovalRequestResponse]:
    """List ALL approval requests across all companies with optional filters."""
    service = ApprovalService(db)
    items, total = await service.list_all_approvals(
        status_filter=status,
        entity_type_filter=entity_type,
        company_id_filter=company_id,
        page=page,
        per_page=per_page,
    )
    return ApiListResponse(
        data=[ApprovalRequestResponse.model_validate(ar) for ar in items],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/summary", response_model=ApiResponse[ApprovalSummaryResponse])
async def get_approval_summary(
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalSummaryResponse]:
    """Return aggregated pending approval statistics by entity type and company."""
    service = ApprovalService(db)
    summary = await service.get_approval_summary()
    return ApiResponse(data=ApprovalSummaryResponse.model_validate(summary))


@router.get(
    "/{approval_request_id}",
    response_model=ApiResponse[ApprovalRequestResponse],
)
async def get_approval_request(
    approval_request_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRequestResponse]:
    """Get detail for any approval request (cross-company)."""
    service = ApprovalService(db)
    ar = await service.get_approval_request(approval_request_id)
    return ApiResponse(data=ApprovalRequestResponse.model_validate(ar))


@router.post(
    "/{approval_request_id}/approve",
    response_model=ApiResponse[ApprovalRequestResponse],
)
async def approve_request(
    approval_request_id: UUID,
    body: ApprovalDecisionRequest | None = None,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRequestResponse]:
    """Platform-level approve. Works for all entity types including products/catalogs."""
    decided_by = await resolve_current_user_id(db, context.user_id)
    service = ApprovalService(db)
    result = await service.process_decision(
        approval_request_id=approval_request_id,
        decided_by=decided_by,
        decision="approved",
        decision_notes=body.decision_notes if body else None,
        role=context.role,
        company_id=context.company_id,
    )
    return ApiResponse(data=ApprovalRequestResponse.model_validate(result))


@router.post(
    "/{approval_request_id}/reject",
    response_model=ApiResponse[ApprovalRequestResponse],
)
async def reject_request(
    approval_request_id: UUID,
    body: ApprovalDecisionRequest | None = None,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRequestResponse]:
    """Platform-level reject. Works for all entity types including products/catalogs."""
    decided_by = await resolve_current_user_id(db, context.user_id)
    service = ApprovalService(db)
    result = await service.process_decision(
        approval_request_id=approval_request_id,
        decided_by=decided_by,
        decision="rejected",
        decision_notes=body.decision_notes if body else None,
        role=context.role,
        company_id=context.company_id,
    )
    return ApiResponse(data=ApprovalRequestResponse.model_validate(result))
