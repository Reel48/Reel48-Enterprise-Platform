"""Platform admin endpoints for cross-company approval rules visibility.

All endpoints require reel48_admin role. These operate cross-company --
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.approval import ApprovalRuleResponse
from app.schemas.common import ApiListResponse, PaginationMeta
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/platform/approval_rules", tags=["platform-approval-rules"])


@router.get("/", response_model=ApiListResponse[ApprovalRuleResponse])
async def list_all_approval_rules(
    company_id: UUID | None = Query(None),
    entity_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[ApprovalRuleResponse]:
    """List ALL approval rules across all companies with optional filters."""
    service = ApprovalService(db)
    rules, total = await service.list_all_rules(
        company_id_filter=company_id,
        entity_type_filter=entity_type,
        page=page,
        per_page=per_page,
    )
    return ApiListResponse(
        data=[ApprovalRuleResponse.model_validate(r) for r in rules],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )
