"""Wishlist endpoints — employee product wishlist management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiResponse, PaginationMeta
from app.schemas.wishlist import (
    WishlistCheckRequest,
    WishlistCreate,
    WishlistListResponse,
    WishlistResponse,
)
from app.services.helpers import resolve_current_user_id
from app.services.wishlist_service import WishlistService

router = APIRouter(prefix="/wishlists", tags=["wishlists"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.get("/", response_model=WishlistListResponse)
async def list_wishlist(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> WishlistListResponse:
    """List the authenticated user's wishlist with product details.

    Standard pagination. All authenticated roles.
    """
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = WishlistService(db)
    items, total = await service.list_wishlist(
        user_id=user_id,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        page=page,
        per_page=per_page,
    )

    return WishlistListResponse(
        data=[WishlistResponse(**item) for item in items],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.post(
    "/",
    response_model=ApiResponse[WishlistResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_to_wishlist(
    data: WishlistCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[WishlistResponse]:
    """Add a product to the authenticated user's wishlist.

    All authenticated roles.
    """
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = WishlistService(db)
    result = await service.add_to_wishlist(
        user_id=user_id,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        data=data,
    )

    return ApiResponse(data=WishlistResponse(**result))


@router.delete("/{wishlist_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_wishlist(
    wishlist_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove a product from the authenticated user's wishlist.

    Hard delete. Only the owning user can delete. Returns 204 No Content.
    """
    _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = WishlistService(db)
    await service.remove_from_wishlist(wishlist_id=wishlist_id, user_id=user_id)


@router.post("/check", response_model=ApiResponse[dict[str, bool]])
async def check_wishlist(
    data: WishlistCheckRequest,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[dict[str, bool]]:
    """Check if products are in the authenticated user's wishlist.

    Accepts {"product_ids": [UUID, ...]} in body.
    Returns {"data": {"uuid1": true, "uuid2": false}}.
    All authenticated roles. POST because product_ids list could be large.
    """
    _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = WishlistService(db)
    result = await service.check_wishlist(user_id=user_id, product_ids=data.product_ids)

    return ApiResponse(data=result)
