"""Approval rules management endpoints.

Company-level rules that define approval thresholds for orders and bulk orders.
Only corporate_admin or above can manage rules.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_corporate_admin
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.approval import (
    ApprovalRuleCreate,
    ApprovalRuleResponse,
    ApprovalRuleUpdate,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.approval_service import ApprovalService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/approval_rules", tags=["approval-rules"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.post("/", response_model=ApiResponse[ApprovalRuleResponse], status_code=201)
async def create_approval_rule(
    data: ApprovalRuleCreate,
    context: TenantContext = Depends(require_corporate_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRuleResponse]:
    """Create an approval rule for the current user's company."""
    company_id = _require_company_id(context)
    created_by = await resolve_current_user_id(db, context.user_id)
    service = ApprovalService(db)
    rule = await service.create_rule(data, company_id, created_by)
    return ApiResponse(data=ApprovalRuleResponse.model_validate(rule))


@router.get("/", response_model=ApiListResponse[ApprovalRuleResponse])
async def list_approval_rules(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(require_corporate_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[ApprovalRuleResponse]:
    """List approval rules for the current user's company."""
    company_id = _require_company_id(context)
    service = ApprovalService(db)
    rules, total = await service.list_rules(company_id, page, per_page)
    return ApiListResponse(
        data=[ApprovalRuleResponse.model_validate(r) for r in rules],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.patch("/{rule_id}", response_model=ApiResponse[ApprovalRuleResponse])
async def update_approval_rule(
    rule_id: UUID,
    data: ApprovalRuleUpdate,
    context: TenantContext = Depends(require_corporate_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRuleResponse]:
    """Update an existing approval rule."""
    company_id = _require_company_id(context)
    service = ApprovalService(db)
    rule = await service.update_rule(rule_id, data, company_id)
    return ApiResponse(data=ApprovalRuleResponse.model_validate(rule))


@router.delete("/{rule_id}", response_model=ApiResponse[ApprovalRuleResponse])
async def deactivate_approval_rule(
    rule_id: UUID,
    context: TenantContext = Depends(require_corporate_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalRuleResponse]:
    """Deactivate an approval rule (soft: is_active=false). Returns 200 with deactivated rule."""
    company_id = _require_company_id(context)
    service = ApprovalService(db)
    rule = await service.deactivate_rule(rule_id, company_id)
    return ApiResponse(data=ApprovalRuleResponse.model_validate(rule))
