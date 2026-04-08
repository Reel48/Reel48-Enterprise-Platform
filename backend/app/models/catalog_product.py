from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class CatalogProduct(TenantBase):
    """
    Junction table linking products to catalogs with optional price override.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: catalog_products_company_isolation + catalog_products_sub_brand_scoping.
    """

    __tablename__ = "catalog_products"

    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", name="fk_catalog_products_catalog_id_catalogs"),
        nullable=False,
    )
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", name="fk_catalog_products_product_id_products"),
        nullable=False,
    )
    display_order = Column(Integer, nullable=False, server_default="0")
    price_override = Column(Numeric(10, 2), nullable=True)
