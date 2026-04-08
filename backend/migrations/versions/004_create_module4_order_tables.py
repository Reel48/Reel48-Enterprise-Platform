"""create_module4_order_tables

Creates two tables for Module 4 (Ordering Flow):
  - orders: Individual employee orders with shipping, status lifecycle, and totals
  - order_line_items: Snapshot of product details at order time with pricing

All tables use TenantBase shape (company_id + sub_brand_id) with standard RLS policies.

Revision ID: 004
Revises: 003
Create Date: 2026-04-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. Create orders table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_orders_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_orders_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_orders_user_id_users"),
            nullable=False,
        ),
        sa.Column(
            "catalog_id",
            UUID(as_uuid=True),
            sa.ForeignKey("catalogs.id", name="fk_orders_catalog_id_catalogs"),
            nullable=False,
        ),
        sa.Column("order_number", sa.String(30), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("shipping_address_line1", sa.String(255), nullable=True),
        sa.Column("shipping_address_line2", sa.String(255), nullable=True),
        sa.Column("shipping_city", sa.String(100), nullable=True),
        sa.Column("shipping_state", sa.String(100), nullable=True),
        sa.Column("shipping_zip", sa.String(20), nullable=True),
        sa.Column("shipping_country", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "subtotal",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "total_amount",
            sa.Numeric(10, 2),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancelled_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_orders_cancelled_by_users"),
            nullable=True,
        ),
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
            "status IN ('pending', 'approved', 'processing', 'shipped', 'delivered', 'cancelled')",
            name="ck_orders_status_valid",
        ),
        sa.CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_non_negative"),
        sa.CheckConstraint(
            "total_amount >= 0", name="ck_orders_total_amount_non_negative"
        ),
    )

    # Orders indexes
    op.create_index("ix_orders_company_id", "orders", ["company_id"])
    op.create_index("ix_orders_sub_brand_id", "orders", ["sub_brand_id"])
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_catalog_id", "orders", ["catalog_id"])
    op.create_index("ix_orders_company_id_status", "orders", ["company_id", "status"])

    # Orders RLS
    op.execute("ALTER TABLE orders ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE orders FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY orders_company_isolation ON orders
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY orders_sub_brand_scoping ON orders AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 2. Create order_line_items table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "order_line_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "companies.id", name="fk_order_line_items_company_id_companies"
            ),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "sub_brands.id", name="fk_order_line_items_sub_brand_id_sub_brands"
            ),
            nullable=True,
        ),
        sa.Column(
            "order_id",
            UUID(as_uuid=True),
            sa.ForeignKey("orders.id", name="fk_order_line_items_order_id_orders"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey(
                "products.id", name="fk_order_line_items_product_id_products"
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
            "quantity > 0", name="ck_order_line_items_quantity_positive"
        ),
        sa.CheckConstraint(
            "unit_price >= 0", name="ck_order_line_items_unit_price_non_negative"
        ),
        sa.CheckConstraint(
            "line_total >= 0", name="ck_order_line_items_line_total_non_negative"
        ),
    )

    # Order_line_items indexes
    op.create_index(
        "ix_order_line_items_company_id", "order_line_items", ["company_id"]
    )
    op.create_index(
        "ix_order_line_items_sub_brand_id", "order_line_items", ["sub_brand_id"]
    )
    op.create_index(
        "ix_order_line_items_order_id", "order_line_items", ["order_id"]
    )
    op.create_index(
        "ix_order_line_items_product_id", "order_line_items", ["product_id"]
    )

    # Order_line_items RLS
    op.execute("ALTER TABLE order_line_items ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE order_line_items FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY order_line_items_company_isolation ON order_line_items
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY order_line_items_sub_brand_scoping ON order_line_items AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # Drop in reverse order: line items first, then orders
    # ──────────────────────────────────────────────────────────────────────

    # 1. Drop order_line_items
    op.execute(
        "DROP POLICY IF EXISTS order_line_items_sub_brand_scoping ON order_line_items"
    )
    op.execute(
        "DROP POLICY IF EXISTS order_line_items_company_isolation ON order_line_items"
    )
    op.execute("ALTER TABLE order_line_items DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_order_line_items_product_id", table_name="order_line_items")
    op.drop_index("ix_order_line_items_order_id", table_name="order_line_items")
    op.drop_index("ix_order_line_items_sub_brand_id", table_name="order_line_items")
    op.drop_index("ix_order_line_items_company_id", table_name="order_line_items")
    op.drop_table("order_line_items")

    # 2. Drop orders
    op.execute("DROP POLICY IF EXISTS orders_sub_brand_scoping ON orders")
    op.execute("DROP POLICY IF EXISTS orders_company_isolation ON orders")
    op.execute("ALTER TABLE orders DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_orders_company_id_status", table_name="orders")
    op.drop_index("ix_orders_catalog_id", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_index("ix_orders_sub_brand_id", table_name="orders")
    op.drop_index("ix_orders_company_id", table_name="orders")
    op.drop_table("orders")
