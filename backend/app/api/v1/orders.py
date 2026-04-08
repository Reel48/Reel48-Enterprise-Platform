from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_manager
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.order import (
    OrderCreate,
    OrderLineItemResponse,
    OrderResponse,
    OrderWithItemsResponse,
)
from app.services.helpers import resolve_current_user_id
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.post("/", response_model=ApiResponse[OrderWithItemsResponse], status_code=201)
async def create_order(
    data: OrderCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderWithItemsResponse]:
    """Place an order against an active catalog. All authenticated roles can order."""
    company_id = _require_company_id(context)
    service = OrderService(db)
    order, line_items = await service.create_order(
        data=data,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        cognito_sub=context.user_id,
    )
    response = OrderWithItemsResponse.model_validate(order)
    response.line_items = [OrderLineItemResponse.model_validate(li) for li in line_items]
    return ApiResponse(data=response)


@router.get("/", response_model=ApiListResponse[OrderResponse])
async def list_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    catalog_id: UUID | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[OrderResponse]:
    """List orders with role-based visibility.

    Managers and admins see all orders in their company/sub-brand scope.
    Employees see only their own orders.
    """
    company_id = _require_company_id(context)
    service = OrderService(db)

    if context.is_manager_or_above:
        orders, total = await service.list_orders(
            company_id,
            context.sub_brand_id,
            page,
            per_page,
            status_filter=status,
            catalog_id_filter=catalog_id,
        )
    else:
        user_id = await resolve_current_user_id(db, context.user_id)
        orders, total = await service.list_my_orders(
            user_id, company_id, page, per_page, status_filter=status,
        )

    return ApiListResponse(
        data=[OrderResponse.model_validate(o) for o in orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/my/", response_model=ApiListResponse[OrderResponse])
async def list_my_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[OrderResponse]:
    """List only the authenticated user's own orders, regardless of role."""
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = OrderService(db)
    orders, total = await service.list_my_orders(
        user_id, company_id, page, per_page, status_filter=status,
    )
    return ApiListResponse(
        data=[OrderResponse.model_validate(o) for o in orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{order_id}", response_model=ApiResponse[OrderWithItemsResponse])
async def get_order(
    order_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderWithItemsResponse]:
    """Get order detail with line items. Employees can only see their own."""
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.get_order(order_id, company_id)

    # Employees can only see their own orders
    if not context.is_manager_or_above:
        user_id = await resolve_current_user_id(db, context.user_id)
        if order.user_id != user_id:
            raise NotFoundError("Order", str(order_id))

    line_items = await service.get_order_line_items(order_id)
    response = OrderWithItemsResponse.model_validate(order)
    response.line_items = [OrderLineItemResponse.model_validate(li) for li in line_items]
    return ApiResponse(data=response)


# ---------------------------------------------------------------------------
# Status Transition Endpoints (Phase 4)
# ---------------------------------------------------------------------------


@router.post("/{order_id}/cancel", response_model=ApiResponse[OrderResponse])
async def cancel_order(
    order_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    """Cancel a pending order. Employees can cancel their own; managers can cancel any."""
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = OrderService(db)
    order = await service.cancel_order(
        order_id, company_id, user_id, context.is_manager_or_above,
    )
    return ApiResponse(data=OrderResponse.model_validate(order))


@router.post("/{order_id}/approve", response_model=ApiResponse[OrderResponse])
async def approve_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    """Approve a pending order. Requires manager_or_above."""
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.approve_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))


@router.post("/{order_id}/process", response_model=ApiResponse[OrderResponse])
async def process_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    """Mark an approved order as processing. Requires manager_or_above."""
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.process_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))


@router.post("/{order_id}/ship", response_model=ApiResponse[OrderResponse])
async def ship_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    """Mark a processing order as shipped. Requires manager_or_above."""
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.ship_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))


@router.post("/{order_id}/deliver", response_model=ApiResponse[OrderResponse])
async def deliver_order(
    order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrderResponse]:
    """Mark a shipped order as delivered. Requires manager_or_above."""
    company_id = _require_company_id(context)
    service = OrderService(db)
    order = await service.deliver_order(order_id, company_id)
    return ApiResponse(data=OrderResponse.model_validate(order))
