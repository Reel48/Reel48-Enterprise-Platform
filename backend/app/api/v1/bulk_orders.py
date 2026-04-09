from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_manager
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.bulk_order import (
    BulkOrderCreate,
    BulkOrderItemCreate,
    BulkOrderItemResponse,
    BulkOrderItemUpdate,
    BulkOrderResponse,
    BulkOrderUpdate,
    BulkOrderWithItemsResponse,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.bulk_order_service import BulkOrderService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/bulk_orders", tags=["bulk-orders"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.post("/", response_model=ApiResponse[BulkOrderResponse], status_code=201)
async def create_bulk_order(
    data: BulkOrderCreate,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Create a new draft bulk order session."""
    company_id = _require_company_id(context)
    created_by = await resolve_current_user_id(db, context.user_id)
    service = BulkOrderService(db)
    bulk_order = await service.create_bulk_order(
        data=data,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        created_by=created_by,
    )
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.get("/", response_model=ApiListResponse[BulkOrderResponse])
async def list_bulk_orders(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[BulkOrderResponse]:
    """List bulk orders visible within the user's tenant scope."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_orders, total = await service.list_bulk_orders(
        company_id,
        context.sub_brand_id,
        page,
        per_page,
        status_filter=status,
    )
    return ApiListResponse(
        data=[BulkOrderResponse.model_validate(bo) for bo in bulk_orders],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{bulk_order_id}", response_model=ApiResponse[BulkOrderWithItemsResponse])
async def get_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderWithItemsResponse]:
    """Get bulk order detail with items."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.get_bulk_order(bulk_order_id, company_id)
    items = await service.get_bulk_order_items(bulk_order_id)
    response = BulkOrderWithItemsResponse.model_validate(bulk_order)
    response.items = [BulkOrderItemResponse.model_validate(item) for item in items]
    return ApiResponse(data=response)


@router.patch("/{bulk_order_id}", response_model=ApiResponse[BulkOrderResponse])
async def update_bulk_order(
    bulk_order_id: UUID,
    data: BulkOrderUpdate,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Update a draft bulk order session (title, description, notes)."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.update_bulk_order(bulk_order_id, data, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.delete("/{bulk_order_id}", status_code=204)
async def delete_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Delete a draft bulk order and all its items. Hard delete (returns 204)."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    await service.delete_bulk_order(bulk_order_id, company_id)


# ---------------------------------------------------------------------------
# Status transition endpoints (Phase 4)
# ---------------------------------------------------------------------------


@router.post("/{bulk_order_id}/submit", response_model=ApiResponse[BulkOrderResponse])
async def submit_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Submit a draft bulk order for approval. Must have at least one item."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.submit_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/approve", response_model=ApiResponse[BulkOrderResponse])
async def approve_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Approve a submitted bulk order. Records approved_by."""
    company_id = _require_company_id(context)
    approved_by = await resolve_current_user_id(db, context.user_id)
    service = BulkOrderService(db)
    bulk_order = await service.approve_bulk_order(bulk_order_id, company_id, approved_by)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/process", response_model=ApiResponse[BulkOrderResponse])
async def process_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Mark an approved bulk order as processing."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.process_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/ship", response_model=ApiResponse[BulkOrderResponse])
async def ship_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Mark a processing bulk order as shipped."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.ship_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/deliver", response_model=ApiResponse[BulkOrderResponse])
async def deliver_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Mark a shipped bulk order as delivered."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    bulk_order = await service.deliver_bulk_order(bulk_order_id, company_id)
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


@router.post("/{bulk_order_id}/cancel", response_model=ApiResponse[BulkOrderResponse])
async def cancel_bulk_order(
    bulk_order_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderResponse]:
    """Cancel a draft, submitted, or approved bulk order."""
    company_id = _require_company_id(context)
    cancelled_by = await resolve_current_user_id(db, context.user_id)
    service = BulkOrderService(db)
    bulk_order = await service.cancel_bulk_order(
        bulk_order_id, company_id, cancelled_by, context.is_manager_or_above,
    )
    return ApiResponse(data=BulkOrderResponse.model_validate(bulk_order))


# ---------------------------------------------------------------------------
# Item management endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{bulk_order_id}/items/",
    response_model=ApiResponse[BulkOrderItemResponse],
    status_code=201,
)
async def add_item(
    bulk_order_id: UUID,
    data: BulkOrderItemCreate,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderItemResponse]:
    """Add an item to a draft bulk order."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    item = await service.add_item(
        bulk_order_id, data, company_id, context.sub_brand_id,
    )
    return ApiResponse(data=BulkOrderItemResponse.model_validate(item))


@router.patch(
    "/{bulk_order_id}/items/{item_id}",
    response_model=ApiResponse[BulkOrderItemResponse],
)
async def update_item(
    bulk_order_id: UUID,
    item_id: UUID,
    data: BulkOrderItemUpdate,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[BulkOrderItemResponse]:
    """Update an item within a draft bulk order."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    item = await service.update_item(bulk_order_id, item_id, data, company_id)
    return ApiResponse(data=BulkOrderItemResponse.model_validate(item))


@router.delete("/{bulk_order_id}/items/{item_id}", status_code=204)
async def remove_item(
    bulk_order_id: UUID,
    item_id: UUID,
    context: TenantContext = Depends(require_manager),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove an item from a draft bulk order (hard delete, returns 204)."""
    company_id = _require_company_id(context)
    service = BulkOrderService(db)
    await service.remove_item(bulk_order_id, item_id, company_id)
