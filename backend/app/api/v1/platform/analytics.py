"""Platform admin endpoints for cross-company analytics.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string
session variables set by require_reel48_admin → get_tenant_context.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.analytics import (
    ApprovalMetricsResponse,
    CompanyRevenueResponse,
    InvoiceSummaryResponse,
    OrderStatusBreakdownResponse,
    PlatformOverviewResponse,
    SpendOverTimeResponse,
    TopProductResponse,
)
from app.schemas.common import ApiResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/platform/analytics", tags=["platform-analytics"])


@router.get("/overview", response_model=ApiResponse[PlatformOverviewResponse])
async def get_platform_overview(
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[PlatformOverviewResponse]:
    """Cross-company platform overview: companies, users, orders, revenue, catalogs."""
    service = AnalyticsService(db)
    result = await service.get_platform_overview()
    return ApiResponse(data=PlatformOverviewResponse(**result))


@router.get(
    "/revenue/by-company",
    response_model=ApiResponse[list[CompanyRevenueResponse]],
)
async def get_revenue_by_company(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[CompanyRevenueResponse]]:
    """Revenue from paid invoices grouped by company."""
    service = AnalyticsService(db)
    result = await service.get_revenue_by_company(
        start_date=start_date, end_date=end_date
    )
    return ApiResponse(data=[CompanyRevenueResponse(**r) for r in result])


@router.get(
    "/revenue/over-time",
    response_model=ApiResponse[list[SpendOverTimeResponse]],
)
async def get_revenue_over_time(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[SpendOverTimeResponse]]:
    """Platform-wide revenue trend over time (reuses SpendOverTimeResponse schema)."""
    service = AnalyticsService(db)
    result = await service.get_spend_over_time(
        start_date=start_date, end_date=end_date, granularity=granularity
    )
    return ApiResponse(data=[SpendOverTimeResponse(**r) for r in result])


@router.get(
    "/orders/status-breakdown",
    response_model=ApiResponse[list[OrderStatusBreakdownResponse]],
)
async def get_order_status_breakdown(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[OrderStatusBreakdownResponse]]:
    """Cross-company order status counts."""
    service = AnalyticsService(db)
    result = await service.get_order_status_breakdown(
        start_date=start_date, end_date=end_date
    )
    return ApiResponse(data=[OrderStatusBreakdownResponse(**r) for r in result])


@router.get(
    "/orders/top-products",
    response_model=ApiResponse[list[TopProductResponse]],
)
async def get_top_products(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[TopProductResponse]]:
    """Cross-company top products by quantity."""
    service = AnalyticsService(db)
    result = await service.get_top_products(
        start_date=start_date, end_date=end_date, limit=limit
    )
    return ApiResponse(data=[TopProductResponse(**r) for r in result])


@router.get(
    "/invoices/summary",
    response_model=ApiResponse[InvoiceSummaryResponse],
)
async def get_invoice_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[InvoiceSummaryResponse]:
    """Cross-company invoice totals by status and billing flow."""
    service = AnalyticsService(db)
    result = await service.get_invoice_summary(
        start_date=start_date, end_date=end_date
    )
    return ApiResponse(data=InvoiceSummaryResponse(**result))


@router.get(
    "/approvals/metrics",
    response_model=ApiResponse[ApprovalMetricsResponse],
)
async def get_approval_metrics(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalMetricsResponse]:
    """Cross-company approval metrics."""
    service = AnalyticsService(db)
    result = await service.get_approval_metrics(
        start_date=start_date, end_date=end_date
    )
    return ApiResponse(data=ApprovalMetricsResponse(**result))
