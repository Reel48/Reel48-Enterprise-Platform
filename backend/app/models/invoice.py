from sqlalchemy import Column, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import TenantBase


class Invoice(TenantBase):
    """
    Invoice for client company billing via Stripe.
    Uses TenantBase (company_id + sub_brand_id).
    RLS: invoices_company_isolation + invoices_sub_brand_scoping.
    """

    __tablename__ = "invoices"

    order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", name="fk_invoices_order_id_orders"),
        nullable=True,
    )
    bulk_order_id = Column(
        UUID(as_uuid=True),
        ForeignKey("bulk_orders.id", name="fk_invoices_bulk_order_id_bulk_orders"),
        nullable=True,
    )
    catalog_id = Column(
        UUID(as_uuid=True),
        ForeignKey("catalogs.id", name="fk_invoices_catalog_id_catalogs"),
        nullable=True,
    )
    stripe_invoice_id = Column(Text, nullable=False, unique=True)
    stripe_invoice_url = Column(Text, nullable=True)
    stripe_pdf_url = Column(Text, nullable=True)
    invoice_number = Column(Text, nullable=True)
    billing_flow = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, server_default="draft")
    total_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, server_default="usd")
    due_date = Column(Date, nullable=True)
    buying_window_closes_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_invoices_created_by_users"),
        nullable=False,
    )
    paid_at = Column(DateTime(timezone=True), nullable=True)
