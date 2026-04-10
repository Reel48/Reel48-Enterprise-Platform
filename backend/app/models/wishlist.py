from sqlalchemy import Column, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class Wishlist(TenantBase):
    """
    Employee wishlist entry for a product.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: wishlists_company_isolation + wishlists_sub_brand_scoping.
    """

    __tablename__ = "wishlists"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_wishlists_user_id_product_id"),
    )

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_wishlists_user_id_users"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", name="fk_wishlists_product_id_products"),
        nullable=False,
    )
    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", name="fk_wishlists_catalog_id_catalogs"),
        nullable=True,
    )
    notes = Column(Text, nullable=True)
