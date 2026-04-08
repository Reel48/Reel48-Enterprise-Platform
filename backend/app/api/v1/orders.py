from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiResponse
from app.schemas.order import OrderCreate, OrderLineItemResponse, OrderWithItemsResponse
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
