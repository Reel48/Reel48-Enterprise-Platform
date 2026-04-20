from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import CompanyBase


class Notification(CompanyBase):
    """
    Admin-created notification for employees.
    Uses CompanyBase (company_id only).
    RLS: notifications_company_isolation.
    """

    __tablename__ = "notifications"

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    notification_type = Column(String(30), nullable=False)
    target_scope = Column(String(20), nullable=False, server_default="company")
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
