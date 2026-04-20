from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import CompanyBase


class User(CompanyBase):
    """
    A platform user. Uses CompanyBase (company_id only).

    reel48_admin users belong to an internal "Reel48 Operations" company in the
    DB, but their JWT omits custom:company_id so the auth middleware sets
    app.current_company_id = '' (cross-company RLS bypass).
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
