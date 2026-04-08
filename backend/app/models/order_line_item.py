from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class OrderLineItem(TenantBase):
    """
    Snapshot of product details at order time with pricing.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: order_line_items_company_isolation + order_line_items_sub_brand_scoping.
    """

    __tablename__ = "order_line_items"

    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", name="fk_order_line_items_order_id_orders"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", name="fk_order_line_items_product_id_products"),
        nullable=False,
    )
    product_name = Column(String(255), nullable=False)
    product_sku = Column(String(100), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False, server_default="1")
    size = Column(String(20), nullable=True)
    decoration = Column(String(255), nullable=True)
    line_total = Column(Numeric(10, 2), nullable=False)
