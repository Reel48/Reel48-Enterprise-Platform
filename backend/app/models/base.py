from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base. All models inherit from this (directly or via mixins)."""

    pass


class GlobalBase(Base):
    """
    For tables with NO tenant isolation columns.
    Used by: companies (the tenant identity table itself)
    """

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CompanyBase(Base):
    """
    For tables scoped to a company but NOT to a sub-brand.
    Used by: sub_brands, org_codes, invites (company-level entities)
    """

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class TenantBase(Base):
    """
    For tables scoped to BOTH company AND sub-brand (the common case).
    Used by: users, products, orders, bulk_orders, invoices, etc.
    """

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True
    )
    sub_brand_id = Column(
        UUID(as_uuid=True), ForeignKey("sub_brands.id"), nullable=True, index=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
