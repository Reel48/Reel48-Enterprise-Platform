from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_admin
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.schemas.catalog import (
    CatalogCreate,
    CatalogProductAdd,
    CatalogProductResponse,
    CatalogResponse,
    CatalogUpdate,
)
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.approval_service import ApprovalService
from app.services.catalog_service import CatalogService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.post(
    "/",
    response_model=ApiResponse[CatalogResponse],
    status_code=201,
)
async def create_catalog(
    data: CatalogCreate,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Create a new draft catalog. Requires admin role."""
    company_id = _require_company_id(context)
    created_by = await resolve_current_user_id(db, context.user_id)
    service = CatalogService(db)
    catalog = await service.create_catalog(
        data, company_id, context.sub_brand_id, created_by
    )
    return ApiResponse(data=CatalogResponse.model_validate(catalog))


@router.get("/", response_model=ApiListResponse[CatalogResponse])
async def list_catalogs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[CatalogResponse]:
    """List catalogs. Employees see only active catalogs; admins see all statuses."""
    company_id = _require_company_id(context)
    service = CatalogService(db)

    if context.is_admin:
        catalogs, total = await service.list_catalogs(
            company_id,
            context.sub_brand_id,
            page,
            per_page,
            status_filter=status,
        )
    else:
        catalogs, total = await service.list_catalogs(
            company_id,
            context.sub_brand_id,
            page,
            per_page,
            active_only=True,
        )

    return ApiListResponse(
        data=[CatalogResponse.model_validate(c) for c in catalogs],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{catalog_id}", response_model=ApiResponse[CatalogResponse])
async def get_catalog(
    catalog_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Get a catalog by ID. Employees can only see active catalogs."""
    service = CatalogService(db)
    catalog = await service.get_catalog(catalog_id, context.company_id)

    # Employees can only see active catalogs
    if not context.is_admin and catalog.status != "active":
        raise NotFoundError("Catalog", str(catalog_id))

    # Sub-brand-scoped admins: verify catalog is in their sub-brand
    if (
        context.sub_brand_id is not None
        and catalog.sub_brand_id is not None
        and catalog.sub_brand_id != context.sub_brand_id
        and not context.is_corporate_admin_or_above
    ):
        raise ForbiddenError("You can only view catalogs in your sub-brand")

    return ApiResponse(data=CatalogResponse.model_validate(catalog))


@router.patch("/{catalog_id}", response_model=ApiResponse[CatalogResponse])
async def update_catalog(
    catalog_id: UUID,
    data: CatalogUpdate,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Update a draft catalog. Requires admin role."""
    company_id = _require_company_id(context)
    service = CatalogService(db)

    # Sub-brand-scoped admins: verify catalog is in their sub-brand
    catalog = await service.get_catalog(catalog_id, company_id)
    if (
        context.sub_brand_id is not None
        and catalog.sub_brand_id is not None
        and catalog.sub_brand_id != context.sub_brand_id
        and not context.is_corporate_admin_or_above
    ):
        raise ForbiddenError("You can only update catalogs in your sub-brand")

    updated = await service.update_catalog(catalog_id, company_id, data)
    return ApiResponse(data=CatalogResponse.model_validate(updated))


@router.delete("/{catalog_id}", response_model=ApiResponse[CatalogResponse])
async def delete_catalog(
    catalog_id: UUID,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Soft-delete a draft catalog. Requires admin role. Returns 200 with deleted resource."""
    company_id = _require_company_id(context)
    service = CatalogService(db)
    catalog = await service.soft_delete_catalog(catalog_id, company_id)
    return ApiResponse(data=CatalogResponse.model_validate(catalog))


@router.post(
    "/{catalog_id}/submit",
    response_model=ApiResponse[CatalogResponse],
)
async def submit_catalog(
    catalog_id: UUID,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Submit a draft catalog for approval. Catalog must have at least one product."""
    company_id = _require_company_id(context)
    submitted_by = await resolve_current_user_id(db, context.user_id)
    service = CatalogService(db)
    catalog = await service.submit_catalog(catalog_id, company_id)

    # Record in the unified approval queue
    approval_svc = ApprovalService(db)
    await approval_svc.record_submission(
        entity_type="catalog",
        entity_id=catalog.id,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        requested_by=submitted_by,
    )

    return ApiResponse(data=CatalogResponse.model_validate(catalog))


@router.post(
    "/{catalog_id}/products/",
    response_model=ApiResponse[CatalogProductResponse],
    status_code=201,
)
async def add_product_to_catalog(
    catalog_id: UUID,
    data: CatalogProductAdd,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogProductResponse]:
    """Add a product to a catalog. Requires admin role."""
    company_id = _require_company_id(context)
    service = CatalogService(db)
    cp = await service.add_product_to_catalog(
        catalog_id,
        data.product_id,
        company_id,
        context.sub_brand_id,
        data.display_order,
        data.price_override,
    )
    return ApiResponse(data=CatalogProductResponse.model_validate(cp))


@router.delete(
    "/{catalog_id}/products/{product_id}",
    status_code=204,
)
async def remove_product_from_catalog(
    catalog_id: UUID,
    product_id: UUID,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    """Remove a product from a catalog. Hard delete junction row. Returns 204."""
    company_id = _require_company_id(context)
    service = CatalogService(db)
    await service.remove_product_from_catalog(catalog_id, product_id, company_id)


@router.get(
    "/{catalog_id}/products/",
    response_model=ApiListResponse[CatalogProductResponse],
)
async def list_catalog_products(
    catalog_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[CatalogProductResponse]:
    """List products in a catalog. Paginated."""
    company_id = _require_company_id(context)
    service = CatalogService(db)
    products, total = await service.list_catalog_products(
        catalog_id, company_id, context.sub_brand_id, page, per_page
    )
    return ApiListResponse(
        data=[CatalogProductResponse.model_validate(cp) for cp in products],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )
