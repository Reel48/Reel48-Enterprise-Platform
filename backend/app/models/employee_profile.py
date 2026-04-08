from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class EmployeeProfile(TenantBase):
    """
    Employee profile storing sizing, department, delivery address, and preferences.
    One profile per user. Uses TenantBase (company_id + sub_brand_id).
    RLS: employee_profiles_company_isolation + employee_profiles_sub_brand_scoping.
    """

    __tablename__ = "employee_profiles"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_employee_profiles_user_id_users"),
        nullable=False,
        unique=True,
    )
    department = Column(String(255), nullable=True)
    job_title = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    shirt_size = Column(String(10), nullable=True)
    pant_size = Column(String(20), nullable=True)
    shoe_size = Column(String(20), nullable=True)
    delivery_address_line1 = Column(String(255), nullable=True)
    delivery_address_line2 = Column(String(255), nullable=True)
    delivery_city = Column(String(100), nullable=True)
    delivery_state = Column(String(100), nullable=True)
    delivery_zip = Column(String(20), nullable=True)
    delivery_country = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    profile_photo_url = Column(Text, nullable=True)
    onboarding_complete = Column(Boolean, nullable=False, server_default="false")
    deleted_at = Column(DateTime(timezone=True), nullable=True)
