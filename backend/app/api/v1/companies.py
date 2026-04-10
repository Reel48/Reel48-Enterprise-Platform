from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_reel48_admin
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.company import CompanyCreate, CompanyResponse, CompanyUpdate
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("/", response_model=ApiListResponse[CompanyResponse])
async def list_companies(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[CompanyResponse]:
    service = CompanyService(db)
    # reel48_admin sees all; others see only their own company
    companies, total = await service.list_companies(context.company_id, page, per_page)
    return ApiListResponse(
        data=[CompanyResponse.model_validate(c) for c in companies],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def get_company(
    company_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
    # Non-reel48_admin users can only view their own company
    if not context.is_reel48_admin and context.company_id != company_id:
        raise ForbiddenError("You can only view your own company")
    service = CompanyService(db)
    company = await service.get_company(company_id)
    return ApiResponse(data=CompanyResponse.model_validate(company))


@router.post(
    "/", response_model=ApiResponse[CompanyResponse], status_code=status.HTTP_201_CREATED
)
async def create_company(
    data: CompanyCreate,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
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
    service = CompanyService(db)
    company = await service.update_company(company_id, data)
    return ApiResponse(data=CompanyResponse.model_validate(company))


@router.delete("/{company_id}", response_model=ApiResponse[CompanyResponse])
async def delete_company(
    company_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CompanyResponse]:
    service = CompanyService(db)
    company = await service.deactivate_company(company_id)
    return ApiResponse(data=CompanyResponse.model_validate(company))
