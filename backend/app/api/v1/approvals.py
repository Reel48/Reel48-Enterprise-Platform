"""Unified approval queue and decision endpoints.

Provides a single approval queue across all entity types (product, catalog,
order, bulk_order) with role-based visibility and decision processing.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.approval import (
    ApprovalDecisionRequest,
    ApprovalQueueItem,
    ApprovalRequestResponse,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.approval_service import ApprovalService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


# ---------------------------------------------------------------------------
# Approval Queue
# ---------------------------------------------------------------------------


@router.get("/pending/", response_model=ApiListResponse[ApprovalQueueItem])
async def list_pending_approvals(
    entity_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[ApprovalQueueItem]:
    """List pending approval requests visible to the current user.

    Visibility:
    - reel48_admin: all pending across all companies
    - corporate_admin: all pending in their company (all sub-brands)
    - sub_brand_admin: pending in their sub-brand (all entity types)
    - regional_manager: pending orders + bulk_orders in their sub-brand
    - employee: 403
    """
    if context.role == "employee":
        raise ForbiddenError("Employees cannot access the approval queue")

    service = ApprovalService(db)
    items, total = await service.list_pending(
        company_id=context.company_id,
        sub_brand_id=context.sub_brand_id,
        role=context.role,
        entity_type_filter=entity_type,
        page=page,
        per_page=per_page,
    )

    # Enrich with entity summary fields
    queue_items = []
    for ar in items:
        entity_name, entity_amount = await service.get_entity_summary(
            ar.entity_type, ar.entity_id
        )
        queue_items.append(
            ApprovalQueueItem(
                id=ar.id,
                entity_type=ar.entity_type,
                entity_id=ar.entity_id,
                status=ar.status,
                requested_by=ar.requested_by,
                requested_at=ar.requested_at,
                entity_name=entity_name,
                entity_amount=entity_amount,
            )
        )

    return ApiListResponse(
        data=queue_items,
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/history/", response_model=ApiListResponse[ApprovalQueueItem])
async def list_approval_history(
    entity_type: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[ApprovalQueueItem]:
    """List decided (approved/rejected) approval requests visible to the current user."""
    if context.role == "employee":
        raise ForbiddenError("Employees cannot access the approval queue")

    service = ApprovalService(db)
    items, total = await service.list_history(
        company_id=context.company_id,
        sub_brand_id=context.sub_brand_id,
        entity_type_filter=entity_type,
        status_filter=status,
        page=page,
        per_page=per_page,
    )

    queue_items = []
    for ar in items:
        entity_name, entity_amount = await service.get_entity_summary(
            ar.entity_type, ar.entity_id
        )
        queue_items.append(
            ApprovalQueueItem(
                id=ar.id,
                entity_type=ar.entity_type,
                entity_id=ar.entity_id,
                status=ar.status,
                requested_by=ar.requested_by,
                requested_at=ar.requested_at,
                entity_name=entity_name,
                entity_amount=entity_amount,
            )
        )

    return ApiListResponse(
        data=queue_items,
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{approval_request_id}", response_model=ApiResponse[ApprovalRequestResponse])
async def get_approval_request(
    approval_request_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRequestResponse]:
    """Get a single approval request detail."""
    if context.role == "employee":
        raise ForbiddenError("Employees cannot access approval requests")

    service = ApprovalService(db)
    ar = await service.get_approval_request(approval_request_id)

    # Scope check: non-reel48_admin must be in the same company
    if context.company_id is not None and ar.company_id != context.company_id:
        raise ForbiddenError("You can only view approval requests in your company")

    # Sub-brand scoping for non-corporate users
    if (
        context.sub_brand_id is not None
        and ar.sub_brand_id is not None
        and ar.sub_brand_id != context.sub_brand_id
    ):
        raise ForbiddenError("You can only view approval requests in your sub-brand")

    return ApiResponse(data=ApprovalRequestResponse.model_validate(ar))


# ---------------------------------------------------------------------------
# Approval Decisions
# ---------------------------------------------------------------------------


@router.post(
    "/{approval_request_id}/approve",
    response_model=ApiResponse[ApprovalRequestResponse],
)
async def approve_request(
    approval_request_id: UUID,
    body: ApprovalDecisionRequest | None = None,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRequestResponse]:
    """Approve an approval request. Delegates to the entity-specific service."""
    if context.role == "employee":
        raise ForbiddenError("Employees cannot approve requests")

    decided_by = await resolve_current_user_id(db, context.user_id)
    service = ApprovalService(db)

    # Scope check before processing
    ar = await service.get_approval_request(approval_request_id)
    if context.company_id is not None and ar.company_id != context.company_id:
        raise ForbiddenError("You can only approve requests in your company")

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
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRequestResponse]:
    """Reject an approval request. Delegates to the entity-specific service."""
    if context.role == "employee":
        raise ForbiddenError("Employees cannot reject requests")

    decided_by = await resolve_current_user_id(db, context.user_id)
    service = ApprovalService(db)

    # Scope check before processing
    ar = await service.get_approval_request(approval_request_id)
    if context.company_id is not None and ar.company_id != context.company_id:
        raise ForbiddenError("You can only reject requests in your company")

    result = await service.process_decision(
        approval_request_id=approval_request_id,
        decided_by=decided_by,
        decision="rejected",
        decision_notes=body.decision_notes if body else None,
        role=context.role,
        company_id=context.company_id,
    )
    return ApiResponse(data=ApprovalRequestResponse.model_validate(result))
