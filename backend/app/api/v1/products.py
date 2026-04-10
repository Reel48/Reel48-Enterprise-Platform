from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_admin
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.product import ProductAddImage, ProductCreate, ProductResponse, ProductUpdate
from app.services.approval_service import ApprovalService
from app.services.email_service import EmailService, get_email_service
from app.services.helpers import resolve_current_user_id
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["products"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.post(
    "/",
    response_model=ApiResponse[ProductResponse],
    status_code=201,
)
async def create_product(
    data: ProductCreate,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    """Create a new draft product. Requires admin role."""
    company_id = _require_company_id(context)
    created_by = await resolve_current_user_id(db, context.user_id)
    service = ProductService(db)
    product = await service.create_product(
        data, company_id, context.sub_brand_id, created_by
    )
    return ApiResponse(data=ProductResponse.model_validate(product))


@router.get("/", response_model=ApiListResponse[ProductResponse])
async def list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[ProductResponse]:
    """List products. Employees see only active products; admins see all statuses."""
    company_id = _require_company_id(context)
    service = ProductService(db)

    # Employees and regional managers see only active products
    is_admin_user = context.is_admin
    if is_admin_user:
        products, total = await service.list_products(
            company_id,
            context.sub_brand_id,
            page,
            per_page,
            status_filter=status,
        )
    else:
        products, total = await service.list_products(
            company_id,
            context.sub_brand_id,
            page,
            per_page,
            active_only=True,
        )

    return ApiListResponse(
        data=[ProductResponse.model_validate(p) for p in products],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{product_id}", response_model=ApiResponse[ProductResponse])
async def get_product(
    product_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    """Get a product by ID. Employees can only see active products."""
    service = ProductService(db)
    product = await service.get_product(product_id, context.company_id)

    # Employees can only see active products
    if not context.is_admin and product.status != "active":
        raise NotFoundError("Product", str(product_id))

    # Sub-brand-scoped admins: verify product is in their sub-brand
    if (
        context.sub_brand_id is not None
        and product.sub_brand_id is not None
        and product.sub_brand_id != context.sub_brand_id
        and not context.is_corporate_admin_or_above
    ):
        raise ForbiddenError("You can only view products in your sub-brand")

    return ApiResponse(data=ProductResponse.model_validate(product))


@router.patch("/{product_id}", response_model=ApiResponse[ProductResponse])
async def update_product(
    product_id: UUID,
    data: ProductUpdate,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    """Update a draft product. Requires admin role."""
    company_id = _require_company_id(context)
    service = ProductService(db)

    # Sub-brand-scoped admins: verify product is in their sub-brand
    product = await service.get_product(product_id, company_id)
    if (
        context.sub_brand_id is not None
        and product.sub_brand_id is not None
        and product.sub_brand_id != context.sub_brand_id
        and not context.is_corporate_admin_or_above
    ):
        raise ForbiddenError("You can only update products in your sub-brand")

    updated = await service.update_product(product_id, company_id, data)
    return ApiResponse(data=ProductResponse.model_validate(updated))


@router.delete("/{product_id}", response_model=ApiResponse[ProductResponse])
async def delete_product(
    product_id: UUID,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    """Soft-delete a draft product. Requires admin role. Returns 200 with deleted resource."""
    company_id = _require_company_id(context)
    service = ProductService(db)
    product = await service.soft_delete_product(product_id, company_id)
    return ApiResponse(data=ProductResponse.model_validate(product))


@router.post(
    "/{product_id}/submit",
    response_model=ApiResponse[ProductResponse],
)
async def submit_product(
    product_id: UUID,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    email_service: EmailService = Depends(get_email_service),
) -> ApiResponse[ProductResponse]:
    """Submit a draft product for approval. Transitions status: draft -> submitted."""
    company_id = _require_company_id(context)
    submitted_by = await resolve_current_user_id(db, context.user_id)
    service = ProductService(db)
    product = await service.submit_product(product_id, company_id)

    # Record in the unified approval queue
    approval_svc = ApprovalService(db, email_service=email_service)
    await approval_svc.record_submission(
        entity_type="product",
        entity_id=product.id,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        requested_by=submitted_by,
    )

    return ApiResponse(data=ProductResponse.model_validate(product))


@router.post(
    "/{product_id}/images",
    response_model=ApiResponse[ProductResponse],
)
async def add_product_image(
    product_id: UUID,
    data: ProductAddImage,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    """Add an image to a draft product. Requires admin role."""
    company_id = _require_company_id(context)
    service = ProductService(db)
    product = await service.add_product_image(
        product_id, data.s3_key, company_id, context.sub_brand_id
    )
    return ApiResponse(data=ProductResponse.model_validate(product))


@router.delete(
    "/{product_id}/images/{index}",
    response_model=ApiResponse[ProductResponse],
)
async def remove_product_image(
    product_id: UUID,
    index: int,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[ProductResponse]:
    """Remove an image from a draft product by index. Requires admin role."""
    company_id = _require_company_id(context)
    service = ProductService(db)
    product = await service.remove_product_image(
        product_id, index, company_id, context.sub_brand_id
    )
    return ApiResponse(data=ProductResponse.model_validate(product))
