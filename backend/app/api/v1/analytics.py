"""Client-facing analytics endpoints (tenant-scoped).

These endpoints provide analytics data to client company users.
Employees are denied access (403). All other roles get data scoped
by RLS to their company/sub-brand.

Authorization:
- corporate_admin: sees analytics across all sub-brands in their company
- sub_brand_admin / regional_manager: sees analytics for their sub-brand only
- employee: NO access (403 on all analytics endpoints)

Spend-by-sub-brand and invoice summary require corporate_admin (cross-brand view).
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.analytics import (
    ApprovalMetricsResponse,
    InvoiceSummaryResponse,
    OrderStatusBreakdownResponse,
    SizeDistributionResponse,
    SpendOverTimeResponse,
    SpendSummaryResponse,
    SubBrandSpendResponse,
    TopProductResponse,
)
from app.schemas.common import ApiListResponse, ApiResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Guards
# ---------------------------------------------------------------------------

def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


def _require_analytics_access(context: TenantContext) -> None:
    """Guard: employees cannot access analytics endpoints."""
    if context.role == "employee":
        raise ForbiddenError("Analytics access requires manager role or above")


def _require_corporate_admin_or_above(context: TenantContext) -> None:
    """Guard: only corporate_admin or reel48_admin can access."""
    if context.role not in ("corporate_admin", "reel48_admin"):
        raise ForbiddenError("This analytics view requires corporate admin access")


# ---------------------------------------------------------------------------
# Spend endpoints
# ---------------------------------------------------------------------------

@router.get("/spend/summary", response_model=ApiResponse[SpendSummaryResponse])
async def get_spend_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SpendSummaryResponse]:
    """Aggregate spend summary (individual + bulk orders).

    Accessible to: regional_manager, sub_brand_admin, corporate_admin.
    """
    _require_company_id(context)
    _require_analytics_access(context)

    service = AnalyticsService(db)
    result = await service.get_spend_summary(start_date=start_date, end_date=end_date)
    return ApiResponse(data=SpendSummaryResponse(**result))


@router.get("/spend/by-sub-brand", response_model=ApiResponse[list[SubBrandSpendResponse]])
async def get_spend_by_sub_brand(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[SubBrandSpendResponse]]:
    """Spend broken down by sub-brand. Corporate admin only (cross-brand view).

    sub_brand_admin and regional_manager get 403.
    """
    _require_company_id(context)
    _require_analytics_access(context)
    _require_corporate_admin_or_above(context)

    service = AnalyticsService(db)
    result = await service.get_spend_by_sub_brand(start_date=start_date, end_date=end_date)
    return ApiResponse(data=[SubBrandSpendResponse(**r) for r in result])


@router.get("/spend/over-time", response_model=ApiResponse[list[SpendOverTimeResponse]])
async def get_spend_over_time(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[SpendOverTimeResponse]]:
    """Spend aggregated into time buckets for trend charting.

    Accessible to: regional_manager, sub_brand_admin, corporate_admin.
    """
    _require_company_id(context)
    _require_analytics_access(context)

    service = AnalyticsService(db)
    result = await service.get_spend_over_time(
        start_date=start_date, end_date=end_date, granularity=granularity
    )
    return ApiResponse(data=[SpendOverTimeResponse(**r) for r in result])


# ---------------------------------------------------------------------------
# Order endpoints
# ---------------------------------------------------------------------------

@router.get("/orders/status-breakdown", response_model=ApiResponse[list[OrderStatusBreakdownResponse]])
async def get_order_status_breakdown(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[OrderStatusBreakdownResponse]]:
    """Count of orders by status, separated by order type.

    Accessible to: regional_manager, sub_brand_admin, corporate_admin.
    """
    _require_company_id(context)
    _require_analytics_access(context)

    service = AnalyticsService(db)
    result = await service.get_order_status_breakdown(start_date=start_date, end_date=end_date)
    return ApiResponse(data=[OrderStatusBreakdownResponse(**r) for r in result])


@router.get("/orders/top-products", response_model=ApiResponse[list[TopProductResponse]])
async def get_top_products(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[TopProductResponse]]:
    """Most ordered products by quantity.

    Accessible to: regional_manager, sub_brand_admin, corporate_admin.
    """
    _require_company_id(context)
    _require_analytics_access(context)

    service = AnalyticsService(db)
    result = await service.get_top_products(
        start_date=start_date, end_date=end_date, limit=limit
    )
    return ApiResponse(data=[TopProductResponse(**r) for r in result])


@router.get("/orders/size-distribution", response_model=ApiResponse[list[SizeDistributionResponse]])
async def get_size_distribution(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[list[SizeDistributionResponse]]:
    """Distribution of ordered sizes across all line items.

    Accessible to: regional_manager, sub_brand_admin, corporate_admin.
    """
    _require_company_id(context)
    _require_analytics_access(context)

    service = AnalyticsService(db)
    result = await service.get_size_distribution(start_date=start_date, end_date=end_date)
    return ApiResponse(data=[SizeDistributionResponse(**r) for r in result])


# ---------------------------------------------------------------------------
# Invoice endpoint
# ---------------------------------------------------------------------------

@router.get("/invoices/summary", response_model=ApiResponse[InvoiceSummaryResponse])
async def get_invoice_summary(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[InvoiceSummaryResponse]:
    """Invoice totals by status and billing flow.

    Accessible to: corporate_admin only (invoices are company-level).
    sub_brand_admin and regional_manager get 403.
    """
    _require_company_id(context)
    _require_analytics_access(context)
    _require_corporate_admin_or_above(context)

    service = AnalyticsService(db)
    result = await service.get_invoice_summary(start_date=start_date, end_date=end_date)
    return ApiResponse(data=InvoiceSummaryResponse(**result))


# ---------------------------------------------------------------------------
# Approval endpoint
# ---------------------------------------------------------------------------

@router.get("/approvals/metrics", response_model=ApiResponse[ApprovalMetricsResponse])
async def get_approval_metrics(
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ApprovalMetricsResponse]:
    """Approval request metrics: pending count, average approval time, approval rate.

    Accessible to: regional_manager, sub_brand_admin, corporate_admin.
    """
    _require_company_id(context)
    _require_analytics_access(context)

    service = AnalyticsService(db)
    result = await service.get_approval_metrics(start_date=start_date, end_date=end_date)
    return ApiResponse(data=ApprovalMetricsResponse(**result))
