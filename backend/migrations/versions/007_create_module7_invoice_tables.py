"""create_module7_invoice_tables

Creates the invoices table for Module 7 (Invoicing & Client Billing).

invoices uses TenantBase shape (company_id + sub_brand_id) with standard RLS policies:
  - invoices_company_isolation (PERMISSIVE)
  - invoices_sub_brand_scoping (RESTRICTIVE)

Revision ID: 007
Revises: 006
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. Create invoices table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "invoices",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_invoices_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_invoices_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column(
            "order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orders.id", name="fk_invoices_order_id_orders"),
            nullable=True,
        ),
        sa.Column(
            "bulk_order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("bulk_orders.id", name="fk_invoices_bulk_order_id_bulk_orders"),
            nullable=True,
        ),
        sa.Column(
            "catalog_id",
            UUID(as_uuid=True),
            sa.ForeignKey("catalogs.id", name="fk_invoices_catalog_id_catalogs"),
            nullable=True,
        ),
        sa.Column("stripe_invoice_id", sa.Text, nullable=False, unique=True),
        sa.Column("stripe_invoice_url", sa.Text, nullable=True),
        sa.Column("stripe_pdf_url", sa.Text, nullable=True),
        sa.Column("invoice_number", sa.Text, nullable=True),
        sa.Column("billing_flow", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="usd"),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column(
            "buying_window_closes_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_invoices_created_by_users"),
            nullable=False,
        ),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # CHECK constraints
        sa.CheckConstraint(
            "billing_flow IN ('assigned', 'self_service', 'post_window')",
            name="ck_invoices_billing_flow_valid",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'finalized', 'sent', 'paid', 'payment_failed', 'voided')",
            name="ck_invoices_status_valid",
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name="ck_invoices_total_amount_non_negative",
        ),
    )

    # ──────────────────────────────────────────────────────────────────────
    # 2. Indexes
    # ──────────────────────────────────────────────────────────────────────
    op.create_index("ix_invoices_company_id", "invoices", ["company_id"])
    op.create_index("ix_invoices_sub_brand_id", "invoices", ["sub_brand_id"])
    op.create_index("ix_invoices_stripe_invoice_id", "invoices", ["stripe_invoice_id"])
    op.create_index(
        "ix_invoices_company_id_status", "invoices", ["company_id", "status"]
    )
    op.create_index("ix_invoices_billing_flow", "invoices", ["billing_flow"])

    # ──────────────────────────────────────────────────────────────────────
    # 3. RLS policies (MUST be in same migration as table creation)
    # ──────────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE invoices ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invoices FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invoices_company_isolation ON invoices
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY invoices_sub_brand_scoping ON invoices AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # Drop RLS policies before dropping the table
    # ──────────────────────────────────────────────────────────────────────
    op.execute(
        "DROP POLICY IF EXISTS invoices_sub_brand_scoping ON invoices"
    )
    op.execute(
        "DROP POLICY IF EXISTS invoices_company_isolation ON invoices"
    )
    op.execute("ALTER TABLE invoices DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_invoices_billing_flow", table_name="invoices")
    op.drop_index("ix_invoices_company_id_status", table_name="invoices")
    op.drop_index("ix_invoices_stripe_invoice_id", table_name="invoices")
    op.drop_index("ix_invoices_sub_brand_id", table_name="invoices")
    op.drop_index("ix_invoices_company_id", table_name="invoices")
    op.drop_table("invoices")
