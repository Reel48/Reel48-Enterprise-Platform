"""Platform admin endpoints for cross-company bulk order visibility.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.bulk_order import (
    BulkOrderItemResponse,
    BulkOrderResponse,
    BulkOrderWithItemsResponse,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.bulk_order_service import BulkOrderService

router = APIRouter(prefix="/platform/bulk_orders", tags=["platform-bulk-orders"])


@router.get("/", response_model=ApiListResponse[BulkOrderResponse])
async def list_all_bulk_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    company_id: UUID | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[BulkOrderResponse]:
    """List ALL bulk orders across all companies."""
    service = BulkOrderService(db)
    bulk_orders, total = await service.list_all_bulk_orders(
        page,
        per_page,
        status_filter=status,
        company_id_filter=company_id,
    )
    return ApiListResponse(
        data=[BulkOrderResponse.model_validate(bo) for bo in bulk_orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{bulk_order_id}", response_model=ApiResponse[BulkOrderWithItemsResponse])
async def get_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderWithItemsResponse]:
    """Get any bulk order detail with items (cross-company)."""
    service = BulkOrderService(db)
    bulk_order = await service.get_bulk_order(bulk_order_id)  # No company_id filter
    items = await service.get_bulk_order_items(bulk_order_id)
    response = BulkOrderWithItemsResponse.model_validate(bulk_order)
    response.items = [BulkOrderItemResponse.model_validate(item) for item in items]
    return ApiResponse(data=response)
