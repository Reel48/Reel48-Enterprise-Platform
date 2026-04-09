from sqlalchemy import Column, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class BulkOrderItem(TenantBase):
    """
    Individual item within a bulk order session.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: bulk_order_items_company_isolation + bulk_order_items_sub_brand_scoping.
    """

    __tablename__ = "bulk_order_items"

    bulk_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bulk_orders.id", name="fk_bulk_order_items_bulk_order_id_bulk_orders"),
        nullable=False,
    )
    employee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_bulk_order_items_employee_id_users"),
        nullable=True,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", name="fk_bulk_order_items_product_id_products"),
        nullable=False,
    )
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, server_default="1")
    size = Column(String(20), nullable=True)
    decoration = Column(String(255), nullable=True)
    line_total = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)
