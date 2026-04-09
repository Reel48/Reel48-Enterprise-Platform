from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class ApprovalRequest(TenantBase):
    """
    Tracks approval requests for products, catalogs, orders, and bulk orders.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: approval_requests_company_isolation + approval_requests_sub_brand_scoping.
    Approval records are permanent audit trail — never soft-deleted.
    """

    __tablename__ = "approval_requests"

    entity_type = Column(String(30), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False)
    requested_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_approval_requests_requested_by_users"),
        nullable=False,
    )
    decided_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_approval_requests_decided_by_users"),
        nullable=True,
    )
    status = Column(String(20), nullable=False, server_default="pending")
    decision_notes = Column(Text, nullable=True)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
