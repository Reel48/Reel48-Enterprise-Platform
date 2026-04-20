"""Platform admin endpoints for cross-company analytics.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string
session variables set by require_reel48_admin → get_tenant_context.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.analytics import PlatformOverviewResponse
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/platform/analytics", tags=["platform-analytics"])


@router.get("/overview", response_model=ApiResponse[PlatformOverviewResponse])
async def get_platform_overview(
    _context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[PlatformOverviewResponse]:
    """Cross-company platform overview: active companies + users."""
    service = AnalyticsService(db)
    result = await service.get_platform_overview()
    return ApiResponse(data=PlatformOverviewResponse(**result))
