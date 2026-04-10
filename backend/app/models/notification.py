from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import TenantBase


class Notification(TenantBase):
    """
    Admin-created notification for employees.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: notifications_company_isolation + notifications_sub_brand_scoping.
    """

    __tablename__ = "notifications"

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    notification_type = Column(String(30), nullable=False)
    target_scope = Column(String(20), nullable=False, server_default="sub_brand")
    target_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_notifications_target_user_id_users"),
        nullable=True,
    )
    read_by = Column(JSONB, nullable=False, server_default="[]")
    link_url = Column(String(500), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_notifications_created_by_users"),
        nullable=False,
    )
    is_active = Column(Boolean, nullable=False, server_default="true")
