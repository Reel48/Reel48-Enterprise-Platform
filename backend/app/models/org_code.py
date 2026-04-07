from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import CompanyBase


class OrgCode(CompanyBase):
    """
    Company-level registration code for employee self-registration.
    Uses CompanyBase (company_id only, no sub_brand_id).
    RLS: org_codes_company_isolation policy on company_id only.
    Only one active code per company at a time.
    """

    __tablename__ = "org_codes"

    code = Column(String(8), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_org_codes_created_by_users"),
        nullable=False,
    )
