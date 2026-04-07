from sqlalchemy import Boolean, Column, String, Text

from app.models.base import GlobalBase


class Company(GlobalBase):
    """
    The tenant identity table. Each row represents one client company.
    Uses GlobalBase (no company_id FK — this IS the company).
    RLS: companies_isolation policy matches id against app.current_company_id.
    """

    __tablename__ = "companies"

    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    stripe_customer_id = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
