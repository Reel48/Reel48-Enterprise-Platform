from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import CompanyBase


class Invite(CompanyBase):
    """
    An employee invite to join a specific sub-brand. Uses CompanyBase (company_id only).
    target_sub_brand_id is an explicit FK, not the TenantBase sub_brand_id.
    RLS: invites_company_isolation policy on company_id only.
    """

    __tablename__ = "invites"

    target_sub_brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("sub_brands.id", name="fk_invites_target_sub_brand_id_sub_brands"),
        nullable=False,
        index=True,
    )
    email = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, server_default="employee")
    token = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_invites_created_by_users"),
        nullable=False,
        index=True,
    )
