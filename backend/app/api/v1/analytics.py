"""Client-facing analytics endpoints (tenant-scoped).

Post-simplification, the only surviving analytics surface is an active-user
count. Commerce analytics (spend, orders, approvals, invoicing) will return
when the Shopify integration lands.
"""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_company_admin
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.analytics import CompanyOverviewResponse
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _require_company_id(context: TenantContext) -> UUID:
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.get("/overview", response_model=ApiResponse[CompanyOverviewResponse])
async def get_company_overview(
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyOverviewResponse]:
    """Company-scoped overview (active user count)."""
    _require_company_id(context)
    service = AnalyticsService(db)
    result = await service.get_company_overview()
    return ApiResponse(data=CompanyOverviewResponse(**result))
