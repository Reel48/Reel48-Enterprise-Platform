from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_admin
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.employee_profile import (
    EmployeeProfileCreate,
    EmployeeProfileResponse,
    EmployeeProfileUpdate,
)
from app.services.employee_profile_service import EmployeeProfileService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/profiles", tags=["employee-profiles"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


@router.get("/me", response_model=ApiResponse[EmployeeProfileResponse])
async def get_my_profile(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EmployeeProfileResponse]:
    """Return the authenticated user's own employee profile."""
    user_id = await resolve_current_user_id(db, context.user_id)
    service = EmployeeProfileService(db)
    profile = await service.get_profile_by_user_id(user_id, context.company_id)
    return ApiResponse(data=EmployeeProfileResponse.model_validate(profile))


@router.put("/me", response_model=ApiResponse[EmployeeProfileResponse])
async def upsert_my_profile(
    data: EmployeeProfileCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EmployeeProfileResponse]:
    """Create or update the authenticated user's own employee profile."""
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = EmployeeProfileService(db)
    profile = await service.upsert_my_profile(
        user_id, company_id, context.sub_brand_id, data
    )
    return ApiResponse(data=EmployeeProfileResponse.model_validate(profile))


@router.post("/me/complete-onboarding", response_model=ApiResponse[EmployeeProfileResponse])
async def complete_onboarding(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EmployeeProfileResponse]:
    """Mark the authenticated user's onboarding as complete. Idempotent."""
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = EmployeeProfileService(db)
    profile = await service.complete_onboarding(
        user_id, company_id, context.sub_brand_id
    )
    return ApiResponse(data=EmployeeProfileResponse.model_validate(profile))


@router.get("/", response_model=ApiListResponse[EmployeeProfileResponse])
async def list_profiles(
    page: int = 1,
    per_page: int = 20,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[EmployeeProfileResponse]:
    """List employee profiles. Requires admin role."""
    company_id = _require_company_id(context)
    per_page = min(per_page, 100)
    service = EmployeeProfileService(db)
    profiles, total = await service.list_profiles(
        company_id, context.sub_brand_id, page, per_page
    )
    return ApiListResponse(
        data=[EmployeeProfileResponse.model_validate(p) for p in profiles],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{profile_id}", response_model=ApiResponse[EmployeeProfileResponse])
async def get_profile(
    profile_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EmployeeProfileResponse]:
    """Get a specific employee profile. Employees can only view their own."""
    service = EmployeeProfileService(db)
    profile = await service.get_profile(profile_id, context.company_id)

    # Employees can only view their own profile
    if not context.is_admin:
        user_id = await resolve_current_user_id(db, context.user_id)
        if profile.user_id != user_id:
            raise ForbiddenError("You can only view your own profile")

    # Sub-brand-scoped admins can only see profiles in their sub-brand
    if (
        context.sub_brand_id is not None
        and profile.sub_brand_id is not None
        and profile.sub_brand_id != context.sub_brand_id
        and not context.is_corporate_admin_or_above
    ):
        raise ForbiddenError("You can only view profiles in your sub-brand")

    return ApiResponse(data=EmployeeProfileResponse.model_validate(profile))


@router.patch("/{profile_id}", response_model=ApiResponse[EmployeeProfileResponse])
async def update_profile(
    profile_id: UUID,
    data: EmployeeProfileUpdate,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EmployeeProfileResponse]:
    """Update an employee profile. Requires admin role."""
    company_id = _require_company_id(context)
    service = EmployeeProfileService(db)

    # Sub-brand-scoped admins: verify profile is in their sub-brand
    profile = await service.get_profile(profile_id, company_id)
    if (
        context.sub_brand_id is not None
        and profile.sub_brand_id is not None
        and profile.sub_brand_id != context.sub_brand_id
        and not context.is_corporate_admin_or_above
    ):
        raise ForbiddenError("You can only update profiles in your sub-brand")

    updated = await service.update_profile(profile_id, company_id, data)
    return ApiResponse(data=EmployeeProfileResponse.model_validate(updated))


@router.delete("/{profile_id}", response_model=ApiResponse[EmployeeProfileResponse])
async def delete_profile(
    profile_id: UUID,
    context: TenantContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[EmployeeProfileResponse]:
    """Soft-delete an employee profile. Requires admin role."""
    company_id = _require_company_id(context)
    service = EmployeeProfileService(db)
    profile = await service.soft_delete_profile(profile_id, company_id)
    return ApiResponse(data=EmployeeProfileResponse.model_validate(profile))
