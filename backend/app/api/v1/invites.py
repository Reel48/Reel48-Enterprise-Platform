from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_company_admin
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.schemas.invite import InviteCreate, InviteListItem, InviteResponse
from app.services.helpers import resolve_current_user_id
from app.services.invite_service import InviteService

router = APIRouter(prefix="/invites", tags=["invites"])


def _require_company_id(context: TenantContext) -> UUID:
    if context.company_id is None:
        raise ForbiddenError(
            "Use platform endpoints for cross-company invite management"
        )
    return context.company_id


@router.get("/", response_model=ApiListResponse[InviteListItem])
async def list_invites(
    page: int = 1,
    per_page: int = 20,
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[InviteListItem]:
    company_id = _require_company_id(context)
    per_page = min(per_page, 100)
    service = InviteService(db)
    invites, total = await service.list_invites(company_id, page, per_page)
    return ApiListResponse(
        data=[InviteListItem.model_validate(inv) for inv in invites],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.post(
    "/",
    response_model=ApiResponse[InviteResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    data: InviteCreate,
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[InviteResponse]:
    company_id = _require_company_id(context)
    created_by = await resolve_current_user_id(db, context.user_id)
    service = InviteService(db)
    invite = await service.create_invite(company_id, data, created_by)
    return ApiResponse(data=InviteResponse.model_validate(invite))


@router.delete("/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invite(
    invite_id: UUID,
    context: TenantContext = Depends(require_company_admin),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    company_id = _require_company_id(context)
    service = InviteService(db)
    await service.delete_invite(invite_id, company_id)
