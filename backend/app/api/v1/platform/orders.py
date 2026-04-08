"""Platform admin endpoints for cross-company order visibility.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.order import OrderLineItemResponse, OrderResponse, OrderWithItemsResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/platform/orders", tags=["platform-orders"])


@router.get("/", response_model=ApiListResponse[OrderResponse])
async def list_all_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    company_id: UUID | None = Query(None),
    catalog_id: UUID | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[OrderResponse]:
    """List ALL orders across all companies."""
    service = OrderService(db)
    orders, total = await service.list_all_orders(
        page,
        per_page,
        status_filter=status,
        company_id_filter=company_id,
        catalog_id_filter=catalog_id,
    )
    return ApiListResponse(
        data=[OrderResponse.model_validate(o) for o in orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{order_id}", response_model=ApiResponse[OrderWithItemsResponse])
async def get_order(
    order_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderWithItemsResponse]:
    """Get any order detail with line items (cross-company)."""
    service = OrderService(db)
    order = await service.get_order(order_id)  # No company_id filter
    line_items = await service.get_order_line_items(order_id)
    response = OrderWithItemsResponse.model_validate(order)
    response.line_items = [OrderLineItemResponse.model_validate(li) for li in line_items]
    return ApiResponse(data=response)
