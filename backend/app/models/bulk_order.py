from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class BulkOrder(TenantBase):
    """
    Bulk order session created by a manager/admin for multiple employees.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: bulk_orders_company_isolation + bulk_orders_sub_brand_scoping.
    """

    __tablename__ = "bulk_orders"

    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", name="fk_bulk_orders_catalog_id_catalogs"),
        nullable=False,
    )
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_orders_created_by_users"),
        nullable=False,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_number = Column(String(30), nullable=False, unique=True)
    status = Column(String(20), nullable=False, server_default="draft")
    total_items = Column(Integer, nullable=False, server_default="0")
    total_amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_orders_approved_by_users"),
        nullable=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_orders_cancelled_by_users"),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
