"""Notification endpoints — employee feed and admin management."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_session, get_tenant_context, require_admin
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiResponse
from app.schemas.notification import (
    NotificationCreate,
    NotificationListMeta,
    NotificationListResponse,
    NotificationResponse,
    NotificationSummary,
)
from app.services.helpers import resolve_current_user_id
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


# ---------------------------------------------------------------------------
# Employee notification feed
# ---------------------------------------------------------------------------


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> NotificationListResponse:
    """List notifications for the authenticated employee.

    Returns unread_count in meta alongside standard pagination.
    All authenticated roles can access.
    """
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = NotificationService(db)
    notifications, total, unread_count = await service.list_notifications_for_user(
        user_id=user_id,
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
    )

    user_id_str = str(user_id)
    summaries = []
    for n in notifications:
        summary = NotificationSummary.model_validate(n)
        summary.is_read = user_id_str in (n.read_by or [])
        summaries.append(summary)

    return NotificationListResponse(
        data=summaries,
        meta=NotificationListMeta(
            page=page,
            per_page=per_page,
            total=total,
            unread_count=unread_count,
        ),
    )


@router.post("/{notification_id}/read", response_model=ApiResponse[NotificationResponse])
async def mark_notification_as_read(
    notification_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[NotificationResponse]:
    """Mark a single notification as read. All authenticated roles."""
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = NotificationService(db)
    notification = await service.mark_as_read(notification_id, str(user_id), company_id)
    response = NotificationResponse.model_validate(notification)
    response.is_read = str(user_id) in (notification.read_by or [])
    return ApiResponse(data=response)


@router.post("/read-all")
async def mark_all_notifications_as_read(
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[dict]:
    """Mark all unread notifications as read. All authenticated roles."""
    company_id = _require_company_id(context)
    user_id = await resolve_current_user_id(db, context.user_id)
    service = NotificationService(db)
    marked_count = await service.mark_all_as_read(
        str(user_id), company_id, context.sub_brand_id,
    )
    return ApiResponse(data={"marked_count": marked_count})


# ---------------------------------------------------------------------------
# Admin notification management
# ---------------------------------------------------------------------------


@router.post("/", response_model=ApiResponse[NotificationResponse], status_code=201)
async def create_notification(
    data: NotificationCreate,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[NotificationResponse]:
    """Create a new notification/announcement. Requires is_admin.

    Sub-brand admins can only create sub_brand or individual scope.
    Corporate admins can create company scope.
    reel48_admin can create any scope.
    """
    company_id = _require_company_id(context)

    if not context.is_admin:
        raise ForbiddenError("Admin role required to create notifications")

    # Sub-brand admins cannot create company-scope notifications
    if data.target_scope == "company" and not context.is_corporate_admin_or_above:
        raise ForbiddenError("Corporate admin or above required for company-scope notifications")

    created_by = await resolve_current_user_id(db, context.user_id)
    service = NotificationService(db)
    notification = await service.create_notification(
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        data=data,
        created_by=created_by,
    )
    return ApiResponse(data=NotificationResponse.model_validate(notification))


@router.get("/admin/", response_model=NotificationListResponse)
async def list_notifications_admin(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    notification_type: str | None = Query(None),
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> NotificationListResponse:
    """Admin view: list all notifications for management. Requires is_admin."""
    company_id = _require_company_id(context)

    if not context.is_admin:
        raise ForbiddenError("Admin role required")

    service = NotificationService(db)
    notifications, total = await service.list_notifications_admin(
        company_id=company_id,
        sub_brand_id=context.sub_brand_id,
        page=page,
        per_page=per_page,
        notification_type=notification_type,
    )

    summaries = [NotificationSummary.model_validate(n) for n in notifications]

    return NotificationListResponse(
        data=summaries,
        meta=NotificationListMeta(
            page=page,
            per_page=per_page,
            total=total,
            unread_count=0,
        ),
    )


@router.delete("/{notification_id}", response_model=ApiResponse[NotificationResponse])
async def deactivate_notification(
    notification_id: UUID,
    context: TenantContext = Depends(get_tenant_context),
    db: AsyncSession = Depends(get_db_session),
) -> ApiResponse[NotificationResponse]:
    """Deactivate a notification (soft-delete). Requires is_admin.

    Sub-brand admins can only deactivate notifications in their sub-brand.
    """
    company_id = _require_company_id(context)

    if not context.is_admin:
        raise ForbiddenError("Admin role required")

    service = NotificationService(db)
    notification = await service.deactivate_notification(notification_id, company_id)

    # Sub-brand admins can only deactivate their own sub-brand's notifications
    if (
        context.sub_brand_id is not None
        and notification.sub_brand_id is not None
        and notification.sub_brand_id != context.sub_brand_id
    ):
        raise ForbiddenError("Cannot deactivate notifications from another sub-brand")

    return ApiResponse(data=NotificationResponse.model_validate(notification))
