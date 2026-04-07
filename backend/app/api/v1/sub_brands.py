from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_corporate_admin
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.sub_brand import SubBrandCreate, SubBrandResponse, SubBrandUpdate
from app.services.sub_brand_service import SubBrandService

router = APIRouter(prefix="/sub_brands", tags=["sub_brands"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped write endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError(
            "Use platform endpoints for cross-company sub-brand management"
        )
    return context.company_id


@router.get("/", response_model=ApiListResponse[SubBrandResponse])
async def list_sub_brands(
    page: int = 1,
    per_page: int = 20,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[SubBrandResponse]:
    per_page = min(per_page, 100)

    if context.company_id is None:
        # reel48_admin — RLS returns all; no defense-in-depth filter possible
        # For now return empty; platform listing endpoints come later
        raise ForbiddenError(
            "Use platform endpoints to list sub-brands across companies"
        )

    service = SubBrandService(db)
    # corporate_admin (sub_brand_id=None): sees all. Others: own sub-brand only.
    sub_brands, total = await service.list_sub_brands(
        context.company_id, context.sub_brand_id, page, per_page
    )
    return ApiListResponse(
        data=[SubBrandResponse.model_validate(sb) for sb in sub_brands],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{sub_brand_id}", response_model=ApiResponse[SubBrandResponse])
async def get_sub_brand(
    sub_brand_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SubBrandResponse]:
    if context.company_id is None:
        raise ForbiddenError(
            "Use platform endpoints for cross-company sub-brand access"
        )
    # Non-corporate users: check sub_brand_id matches their own
    if context.sub_brand_id is not None and context.sub_brand_id != sub_brand_id:
        raise ForbiddenError("You can only view your own sub-brand")
    service = SubBrandService(db)
    sub_brand = await service.get_sub_brand(sub_brand_id, context.company_id)
    return ApiResponse(data=SubBrandResponse.model_validate(sub_brand))


@router.post(
    "/",
    response_model=ApiResponse[SubBrandResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_sub_brand(
    data: SubBrandCreate,
    context: TenantContext = Depends(require_corporate_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SubBrandResponse]:
    company_id = _require_company_id(context)
    service = SubBrandService(db)
    sub_brand = await service.create_sub_brand(company_id, data)
    return ApiResponse(data=SubBrandResponse.model_validate(sub_brand))


@router.patch("/{sub_brand_id}", response_model=ApiResponse[SubBrandResponse])
async def update_sub_brand(
    sub_brand_id: UUID,
    data: SubBrandUpdate,
    context: TenantContext = Depends(require_corporate_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SubBrandResponse]:
    company_id = _require_company_id(context)
    service = SubBrandService(db)
    sub_brand = await service.update_sub_brand(sub_brand_id, company_id, data)
    return ApiResponse(data=SubBrandResponse.model_validate(sub_brand))


@router.delete("/{sub_brand_id}", response_model=ApiResponse[SubBrandResponse])
async def delete_sub_brand(
    sub_brand_id: UUID,
    context: TenantContext = Depends(require_corporate_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[SubBrandResponse]:
    company_id = _require_company_id(context)
    service = SubBrandService(db)
    sub_brand = await service.deactivate_sub_brand(sub_brand_id, company_id)
    return ApiResponse(data=SubBrandResponse.model_validate(sub_brand))
