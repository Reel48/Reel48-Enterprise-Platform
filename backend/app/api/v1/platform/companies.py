"""Platform admin endpoints for client company management.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from app.schemas.org_code import OrgCodeResponse
from app.schemas.sub_brand import SubBrandResponse
from app.schemas.user import UserResponse
from app.services.company_service import CompanyService
from app.services.org_code_service import OrgCodeService
from app.services.sub_brand_service import SubBrandService
from app.services.user_service import UserService

router = APIRouter(prefix="/platform/companies", tags=["platform-companies"])


@router.get("/", response_model=ApiListResponse[CompanyResponse])
async def list_all_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[CompanyResponse]:
    """List ALL client companies across the platform.

    Supports optional is_active filter. Ordered by created_at descending.
    """
    service = CompanyService(db)
    companies, total = await service.list_all_companies(
        page=page, per_page=per_page, is_active=is_active
    )
    return ApiListResponse(
        data=[CompanyResponse.model_validate(c) for c in companies],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def get_company(
    company_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
    """Get a single company by ID."""
    service = CompanyService(db)
    company = await service.get_company(company_id)
    return ApiResponse(data=CompanyResponse.model_validate(company))


@router.post(
    "/",
    response_model=ApiResponse[CompanyResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_company(
    data: CompanyCreate,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
    """Create a new client company.

    Atomically creates the company and its default sub-brand (ADR-003).
    """
    service = CompanyService(db)
    company = await service.create_company(data)
    return ApiResponse(data=CompanyResponse.model_validate(company))


@router.patch("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def update_company(
    company_id: UUID,
    data: CompanyUpdate,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
    """Update a company's name, slug, or active status."""
    service = CompanyService(db)
    company = await service.update_company(company_id, data)
    return ApiResponse(data=CompanyResponse.model_validate(company))


@router.post(
    "/{company_id}/deactivate",
    response_model=ApiResponse[CompanyResponse],
)
async def deactivate_company(
    company_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
    """Soft-deactivate a company (sets is_active=false)."""
    service = CompanyService(db)
    company = await service.deactivate_company(company_id)
    return ApiResponse(data=CompanyResponse.model_validate(company))


@router.post(
    "/{company_id}/reactivate",
    response_model=ApiResponse[CompanyResponse],
)
async def reactivate_company(
    company_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
    """Re-activate a previously deactivated company (sets is_active=true)."""
    service = CompanyService(db)
    company = await service.reactivate_company(company_id)
    return ApiResponse(data=CompanyResponse.model_validate(company))


@router.get(
    "/{company_id}/sub_brands/",
    response_model=ApiListResponse[SubBrandResponse],
)
async def list_company_sub_brands(
    company_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[SubBrandResponse]:
    """List all sub-brands for a specific company."""
    service = SubBrandService(db)
    sub_brands, total = await service.list_sub_brands(
        company_id=company_id, sub_brand_id=None, page=page, per_page=per_page
    )
    return ApiListResponse(
        data=[SubBrandResponse.model_validate(sb) for sb in sub_brands],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get(
    "/{company_id}/users/",
    response_model=ApiListResponse[UserResponse],
)
async def list_company_users(
    company_id: UUID,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[UserResponse]:
    """List all users for a specific company."""
    service = UserService(db)
    users, total = await service.list_users(
        company_id=company_id, sub_brand_id=None, page=page, per_page=per_page
    )
    return ApiListResponse(
        data=[UserResponse.model_validate(u) for u in users],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get(
    "/{company_id}/org_code/",
    response_model=ApiResponse[OrgCodeResponse | None],
)
async def get_company_org_code(
    company_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrgCodeResponse | None]:
    """Get the current active org code for a company, or null if none exists."""
    service = OrgCodeService(db)
    org_code = await service.get_current(company_id)
    return ApiResponse(
        data=OrgCodeResponse.model_validate(org_code) if org_code else None
    )
