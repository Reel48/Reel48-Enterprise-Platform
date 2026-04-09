"""create_module5_bulk_order_tables

Creates two tables for Module 5 (Bulk Ordering System):
  - bulk_orders: Bulk order sessions created by managers/admins for multiple employees
  - bulk_order_items: Individual items within a bulk order with product snapshots

All tables use TenantBase shape (company_id + sub_brand_id) with standard RLS policies.

Revision ID: 005
Revises: 004
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. Create bulk_orders table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "bulk_orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_bulk_orders_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_bulk_orders_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column(
            "catalog_id",
            UUID(as_uuid=True),
            sa.ForeignKey("catalogs.id", name="fk_bulk_orders_catalog_id_catalogs"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_bulk_orders_created_by_users"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("order_number", sa.String(30), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "total_items",
            sa.Integer,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_bulk_orders_approved_by_users"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancelled_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_bulk_orders_cancelled_by_users"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text, nullable=True),
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
            "status IN ('draft', 'submitted', 'approved', 'processing', 'shipped', 'delivered', 'cancelled')",
            name="ck_bulk_orders_status_valid",
        ),
        sa.CheckConstraint(
            "total_items >= 0", name="ck_bulk_orders_total_items_non_negative"
        ),
        sa.CheckConstraint(
            "total_amount >= 0", name="ck_bulk_orders_total_amount_non_negative"
        ),
    )

    # Bulk_orders indexes
    op.create_index("ix_bulk_orders_company_id", "bulk_orders", ["company_id"])
    op.create_index("ix_bulk_orders_sub_brand_id", "bulk_orders", ["sub_brand_id"])
    op.create_index("ix_bulk_orders_catalog_id", "bulk_orders", ["catalog_id"])
    op.create_index("ix_bulk_orders_created_by", "bulk_orders", ["created_by"])
    op.create_index(
        "ix_bulk_orders_company_id_status", "bulk_orders", ["company_id", "status"]
    )

    # Bulk_orders RLS
    op.execute("ALTER TABLE bulk_orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE bulk_orders FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY bulk_orders_company_isolation ON bulk_orders
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY bulk_orders_sub_brand_scoping ON bulk_orders AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 2. Create bulk_order_items table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "bulk_order_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "companies.id", name="fk_bulk_order_items_company_id_companies"
            ),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "sub_brands.id", name="fk_bulk_order_items_sub_brand_id_sub_brands"
            ),
            nullable=True,
        ),
        sa.Column(
            "bulk_order_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "bulk_orders.id", name="fk_bulk_order_items_bulk_order_id_bulk_orders"
            ),
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_bulk_order_items_employee_id_users"),
            nullable=True,
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "products.id", name="fk_bulk_order_items_product_id_products"
            ),
            nullable=False,
        ),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("product_sku", sa.String(100), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "quantity", sa.Integer, nullable=False, server_default=sa.text("1")
        ),
        sa.Column("size", sa.String(20), nullable=True),
        sa.Column("decoration", sa.String(255), nullable=True),
        sa.Column("line_total", sa.Numeric(10, 2), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
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
            "quantity > 0", name="ck_bulk_order_items_quantity_positive"
        ),
        sa.CheckConstraint(
            "unit_price >= 0", name="ck_bulk_order_items_unit_price_non_negative"
        ),
        sa.CheckConstraint(
            "line_total >= 0", name="ck_bulk_order_items_line_total_non_negative"
        ),
    )

    # Bulk_order_items indexes
    op.create_index(
        "ix_bulk_order_items_company_id", "bulk_order_items", ["company_id"]
    )
    op.create_index(
        "ix_bulk_order_items_sub_brand_id", "bulk_order_items", ["sub_brand_id"]
    )
    op.create_index(
        "ix_bulk_order_items_bulk_order_id", "bulk_order_items", ["bulk_order_id"]
    )
    op.create_index(
        "ix_bulk_order_items_employee_id", "bulk_order_items", ["employee_id"]
    )
    op.create_index(
        "ix_bulk_order_items_product_id", "bulk_order_items", ["product_id"]
    )

    # Bulk_order_items RLS
    op.execute("ALTER TABLE bulk_order_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE bulk_order_items FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY bulk_order_items_company_isolation ON bulk_order_items
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY bulk_order_items_sub_brand_scoping ON bulk_order_items AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # Drop in reverse order: items first, then bulk_orders
    # ──────────────────────────────────────────────────────────────────────

    # 1. Drop bulk_order_items
    op.execute(
        "DROP POLICY IF EXISTS bulk_order_items_sub_brand_scoping ON bulk_order_items"
    )
    op.execute(
        "DROP POLICY IF EXISTS bulk_order_items_company_isolation ON bulk_order_items"
    )
    op.execute("ALTER TABLE bulk_order_items DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_bulk_order_items_product_id", table_name="bulk_order_items")
    op.drop_index("ix_bulk_order_items_employee_id", table_name="bulk_order_items")
    op.drop_index("ix_bulk_order_items_bulk_order_id", table_name="bulk_order_items")
    op.drop_index("ix_bulk_order_items_sub_brand_id", table_name="bulk_order_items")
    op.drop_index("ix_bulk_order_items_company_id", table_name="bulk_order_items")
    op.drop_table("bulk_order_items")

    # 2. Drop bulk_orders
    op.execute("DROP POLICY IF EXISTS bulk_orders_sub_brand_scoping ON bulk_orders")
    op.execute("DROP POLICY IF EXISTS bulk_orders_company_isolation ON bulk_orders")
    op.execute("ALTER TABLE bulk_orders DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_bulk_orders_company_id_status", table_name="bulk_orders")
    op.drop_index("ix_bulk_orders_created_by", table_name="bulk_orders")
    op.drop_index("ix_bulk_orders_catalog_id", table_name="bulk_orders")
    op.drop_index("ix_bulk_orders_sub_brand_id", table_name="bulk_orders")
    op.drop_index("ix_bulk_orders_company_id", table_name="bulk_orders")
    op.drop_table("bulk_orders")
