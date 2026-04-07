from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class User(TenantBase):
    """
    A platform user. Uses TenantBase (company_id + sub_brand_id).
    sub_brand_id is NULL for corporate_admin and reel48_admin users.
    RLS: users_company_isolation + users_sub_brand_scoping.
    """

    __tablename__ = "users"

    cognito_sub = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    registration_method = Column(String(20), nullable=False, server_default="invite")
    org_code_id = Column(
        UUID(as_uuid=True),
        ForeignKey("org_codes.id", name="fk_users_org_code_id_org_codes"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, server_default="true")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
