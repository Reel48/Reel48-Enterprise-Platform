from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_company_admin
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.schemas.common import ApiResponse
from app.schemas.org_code import OrgCodeResponse
from app.services.helpers import resolve_current_user_id
from app.services.org_code_service import OrgCodeService

router = APIRouter(prefix="/org_codes", tags=["org_codes"])


def _require_company_id(context: TenantContext) -> UUID:
    if context.company_id is None:
        raise ForbiddenError(
            "Use platform endpoints for cross-company org code management"
        )
    return context.company_id


@router.post(
    "/",
    response_model=ApiResponse[OrgCodeResponse],
    status_code=status.HTTP_201_CREATED,
)
async def generate_org_code(
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrgCodeResponse]:
    company_id = _require_company_id(context)
    created_by = await resolve_current_user_id(db, context.user_id)
    service = OrgCodeService(db)
    org_code = await service.generate_code(company_id, created_by)
    return ApiResponse(data=OrgCodeResponse.model_validate(org_code))


@router.get("/current", response_model=ApiResponse[OrgCodeResponse])
async def get_current_org_code(
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrgCodeResponse]:
    company_id = _require_company_id(context)
    service = OrgCodeService(db)
    org_code = await service.get_current(company_id)
    if org_code is None:
        raise NotFoundError("OrgCode", "current")
    return ApiResponse(data=OrgCodeResponse.model_validate(org_code))


@router.delete("/{org_code_id}", response_model=ApiResponse[OrgCodeResponse])
async def deactivate_org_code(
    org_code_id: UUID,
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[OrgCodeResponse]:
    company_id = _require_company_id(context)
    service = OrgCodeService(db)
    org_code = await service.deactivate(org_code_id, company_id)
    return ApiResponse(data=OrgCodeResponse.model_validate(org_code))
