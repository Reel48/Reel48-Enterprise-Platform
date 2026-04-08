from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class Catalog(TenantBase):
    """
    Product catalog with payment model and optional buying window.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: catalogs_company_isolation + catalogs_sub_brand_scoping.
    """

    __tablename__ = "catalogs"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(100), nullable=False)
    payment_model = Column(String(30), nullable=False)
    status = Column(String(20), nullable=False, server_default="draft")
    buying_window_opens_at = Column(DateTime(timezone=True), nullable=True)
    buying_window_closes_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_catalogs_approved_by_users"),
        nullable=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_catalogs_created_by_users"),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
