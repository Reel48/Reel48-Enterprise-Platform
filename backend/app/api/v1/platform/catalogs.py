"""Platform admin endpoints for catalog approval workflow.

All endpoints require reel48_admin role. These operate cross-company —
the reel48_admin has no company_id, so RLS is bypassed via empty string.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, require_reel48_admin
from app.core.tenant import TenantContext
from app.schemas.catalog import CatalogResponse
from app.schemas.common import ApiListResponse, ApiResponse, PaginationMeta
from app.services.catalog_service import CatalogService
from app.services.helpers import resolve_current_user_id

router = APIRouter(prefix="/platform/catalogs", tags=["platform-catalogs"])


class RejectRequest(BaseModel):
    rejection_reason: str | None = None


@router.get("/", response_model=ApiListResponse[CatalogResponse])
async def list_all_catalogs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    company_id: UUID | None = Query(None),
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiListResponse[CatalogResponse]:
    """List ALL catalogs across all companies. Supports status and company_id filters."""
    service = CatalogService(db)
    catalogs, total = await service.list_all_catalogs(
        page, per_page, status_filter=status, company_id_filter=company_id
    )
    return ApiListResponse(
        data=[CatalogResponse.model_validate(c) for c in catalogs],
        meta=PaginationMeta(page=page, per_page=per_page, total=total),
    )


@router.post("/{catalog_id}/approve", response_model=ApiResponse[CatalogResponse])
async def approve_catalog(
    catalog_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Approve a submitted catalog. All products must be approved/active first."""
    approved_by = await resolve_current_user_id(db, context.user_id)
    service = CatalogService(db)
    catalog = await service.approve_catalog(catalog_id, approved_by)
    return ApiResponse(data=CatalogResponse.model_validate(catalog))


@router.post("/{catalog_id}/reject", response_model=ApiResponse[CatalogResponse])
async def reject_catalog(
    catalog_id: UUID,
    body: RejectRequest | None = None,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Reject a submitted catalog back to draft."""
    service = CatalogService(db)
    catalog = await service.reject_catalog(catalog_id)
    return ApiResponse(data=CatalogResponse.model_validate(catalog))


@router.post("/{catalog_id}/activate", response_model=ApiResponse[CatalogResponse])
async def activate_catalog(
    catalog_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Activate an approved catalog. Makes it visible to employees."""
    service = CatalogService(db)
    catalog = await service.activate_catalog(catalog_id)
    return ApiResponse(data=CatalogResponse.model_validate(catalog))


@router.post("/{catalog_id}/close", response_model=ApiResponse[CatalogResponse])
async def close_catalog(
    catalog_id: UUID,
    context: TenantContext = Depends(require_reel48_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[CatalogResponse]:
    """Close an active catalog. For invoice_after_close buying window catalogs."""
    service = CatalogService(db)
    catalog = await service.close_catalog(catalog_id)
    return ApiResponse(data=CatalogResponse.model_validate(catalog))
