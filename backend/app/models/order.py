from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class Order(TenantBase):
    """
    Individual employee order with shipping, status lifecycle, and totals.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: orders_company_isolation + orders_sub_brand_scoping.
    """

    __tablename__ = "orders"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_orders_user_id_users"),
        nullable=False,
    )
    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", name="fk_orders_catalog_id_catalogs"),
        nullable=False,
    )
    order_number = Column(String(30), nullable=False, unique=True)
    status = Column(String(20), nullable=False, server_default="pending")
    shipping_address_line1 = Column(String(255), nullable=True)
    shipping_address_line2 = Column(String(255), nullable=True)
    shipping_city = Column(String(100), nullable=True)
    shipping_state = Column(String(100), nullable=True)
    shipping_zip = Column(String(20), nullable=True)
    shipping_country = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    subtotal = Column(Numeric(10, 2), nullable=False, server_default="0")
    total_amount = Column(Numeric(10, 2), nullable=False, server_default="0")
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_orders_cancelled_by_users"),
        nullable=True,
    )
