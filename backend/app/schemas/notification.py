from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import ApiListResponse


class NotificationCreate(BaseModel):
    """Used by admins to create a notification."""

    title: str
    body: str
    notification_type: str
    target_scope: str = "sub_brand"
    target_user_id: UUID | None = None
    link_url: str | None = None
    expires_at: datetime | None = None

    @field_validator("notification_type")
    @classmethod
    def notification_type_must_be_valid(cls, v: str) -> str:
        valid = {"announcement", "catalog_available", "buying_window_reminder", "order_update"}
        if v not in valid:
            raise ValueError(f"notification_type must be one of: {', '.join(sorted(valid))}")
        return v

    @field_validator("target_scope")
    @classmethod
    def target_scope_must_be_valid(cls, v: str) -> str:
        valid = {"company", "sub_brand", "individual"}
        if v not in valid:
            raise ValueError(f"target_scope must be one of: {', '.join(sorted(valid))}")
        return v


class NotificationResponse(BaseModel):
    """Full notification representation for API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    title: str
    body: str
    notification_type: str
    target_scope: str
    target_user_id: UUID | None
    read_by: list[str]
    link_url: str | None
    expires_at: datetime | None
    created_by: UUID
    is_active: bool
    is_read: bool = False
    created_at: datetime
    updated_at: datetime


class NotificationSummary(BaseModel):
    """Lighter version for list views."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    notification_type: str
    target_scope: str
    is_active: bool
    is_read: bool = False
    link_url: str | None
    created_at: datetime


class NotificationListMeta(BaseModel):
    page: int
    per_page: int
    total: int
    unread_count: int = 0


class NotificationListResponse(BaseModel):
    """Paginated notification list with unread_count in meta."""

    data: list[NotificationSummary]
    meta: NotificationListMeta
    errors: list = []
