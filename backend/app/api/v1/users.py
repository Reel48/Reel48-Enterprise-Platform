from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_company_admin
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.tenant import TenantContext
from app.models.company import Company
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.cognito_service import CognitoService, get_cognito_service
from app.services.helpers import resolve_current_user_id
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=ApiResponse[UserResponse])
async def get_current_user(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[UserResponse]:
    """Return the authenticated user's own profile with company name."""
    service = UserService(db)
    user = await service.get_user_by_cognito_sub(context.user_id)
    if user is None:
        raise NotFoundError("User", context.user_id)
    response = UserResponse.model_validate(user)

    if user.company_id:
        result = await db.execute(
            select(Company.name).where(Company.id == user.company_id)
        )
        response.company_name = result.scalar_one_or_none()

    return ApiResponse(data=response)


@router.get("/", response_model=ApiListResponse[UserResponse])
async def list_users(
    page: int = 1,
    per_page: int = 20,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[UserResponse]:
    if not context.is_company_admin_or_above:
        raise ForbiddenError("Company admin role required to list users")

    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints to list users across companies")

    per_page = min(per_page, 100)
    service = UserService(db)
    users, total = await service.list_users(context.company_id, page, per_page)
    return ApiListResponse(
        data=[UserResponse.model_validate(u) for u in users],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(
    user_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[UserResponse]:
    service = UserService(db)
    user = await service.get_user(user_id, context.company_id)

    if not context.is_company_admin_or_above and user.cognito_sub != context.user_id:
        raise ForbiddenError("You can only view your own profile")

    return ApiResponse(data=UserResponse.model_validate(user))


@router.post(
    "/", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED
)
async def create_user(
    data: UserCreate,
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
    cognito_service: CognitoService = Depends(get_cognito_service),
) -> ApiResponse[UserResponse]:
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company user creation")

    service = UserService(db, cognito_service)
    user = await service.create_user(context.company_id, data, context.role)
    return ApiResponse(data=UserResponse.model_validate(user))


@router.patch("/me", response_model=ApiResponse[UserResponse])
async def update_current_user(
    data: UserUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
    cognito_service: CognitoService = Depends(get_cognito_service),
) -> ApiResponse[UserResponse]:
    """Update the authenticated user's own name and/or email."""
    user_id = await resolve_current_user_id(db, context.user_id)

    if not context.is_company_admin_or_above:
        allowed = data.model_dump(exclude_unset=True)
        disallowed = set(allowed.keys()) - {"full_name", "email"}
        if disallowed:
            raise ForbiddenError("You can only update your name and email")

    service = UserService(db, cognito_service)
    updated = await service.update_user(user_id, context.company_id, data, context.role)
    return ApiResponse(data=UserResponse.model_validate(updated))


@router.patch("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
    cognito_service: CognitoService = Depends(get_cognito_service),
) -> ApiResponse[UserResponse]:
    service = UserService(db, cognito_service)
    user = await service.get_user(user_id, context.company_id)

    if not context.is_company_admin_or_above:
        if user.cognito_sub != context.user_id:
            raise ForbiddenError("You can only update your own profile")
        allowed = data.model_dump(exclude_unset=True)
        disallowed = set(allowed.keys()) - {"full_name", "email"}
        if disallowed:
            raise ForbiddenError("Employees can only update their name and email")

    updated = await service.update_user(user_id, context.company_id, data, context.role)
    return ApiResponse(data=UserResponse.model_validate(updated))


@router.delete("/{user_id}", response_model=ApiResponse[UserResponse])
async def delete_user(
    user_id: UUID,
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
    cognito_service: CognitoService = Depends(get_cognito_service),
) -> ApiResponse[UserResponse]:
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company user deletion")
    service = UserService(db, cognito_service)
    user = await service.soft_delete_user(user_id, context.company_id)
    return ApiResponse(data=UserResponse.model_validate(user))
