from sqlalchemy import Column, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import TenantBase


class Product(TenantBase):
    """
    Individual product with sizing, decoration options, and approval tracking.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: products_company_isolation + products_sub_brand_scoping.
    """

    __tablename__ = "products"

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    sku = Column(String(100), nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    sizes = Column(JSONB, nullable=False, server_default="[]")
    decoration_options = Column(JSONB, nullable=False, server_default="[]")
    image_urls = Column(JSONB, nullable=False, server_default="[]")
    status = Column(String(20), nullable=False, server_default="draft")
    approved_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_products_approved_by_users"),
        nullable=True,
    )
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_products_created_by_users"),
        nullable=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
