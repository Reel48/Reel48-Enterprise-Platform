from sqlalchemy import Boolean, Column, String, UniqueConstraint

from app.models.base import CompanyBase


class SubBrand(CompanyBase):
    """
    A sub-brand within a company. Uses CompanyBase (company_id only, no sub_brand_id).
    RLS: sub_brands_company_isolation policy on company_id only.
    """

    __tablename__ = "sub_brands"
    __table_args__ = (
        UniqueConstraint("company_id", "slug", name="uq_sub_brands_company_id_slug"),
    )

    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False)
    is_default = Column(Boolean, nullable=False, server_default="false")
    is_active = Column(Boolean, nullable=False, server_default="true")
