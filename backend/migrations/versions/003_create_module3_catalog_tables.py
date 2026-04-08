"""create_module3_catalog_tables

Creates three tables for Module 3 (Product Catalog & Brand Management):
  - products: Individual products with sizing, decoration, and approval tracking
  - catalogs: Groupings of products with payment model and buying window support
  - catalog_products: Junction table linking products to catalogs with optional price override

All tables use TenantBase shape (company_id + sub_brand_id) with standard RLS policies.

Revision ID: 003
Revises: 002
Create Date: 2026-04-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. Create products table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_products_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_products_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("sizes", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "decoration_options", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
        sa.Column("image_urls", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "approved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_products_approved_by_users"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_products_created_by_users"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("unit_price >= 0", name="ck_products_unit_price_non_negative"),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'active', 'archived')",
            name="ck_products_status_valid",
        ),
    )

    # Products indexes
    op.create_index("ix_products_company_id", "products", ["company_id"])
    op.create_index("ix_products_sub_brand_id", "products", ["sub_brand_id"])
    op.create_index("ix_products_company_id_status", "products", ["company_id", "status"])

    # Partial unique index: SKU unique per company, excluding soft-deleted rows
    op.execute(
        "CREATE UNIQUE INDEX uq_products_company_id_sku "
        "ON products (company_id, sku) WHERE deleted_at IS NULL"
    )

    # Products RLS
    op.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE products FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY products_company_isolation ON products
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY products_sub_brand_scoping ON products AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 2. Create catalogs table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "catalogs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_catalogs_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_catalogs_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("payment_model", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("buying_window_opens_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("buying_window_closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "approved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_catalogs_approved_by_users"),
            nullable=True,
        ),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_catalogs_created_by_users"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
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
            "payment_model IN ('self_service', 'invoice_after_close')",
            name="ck_catalogs_payment_model_valid",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'submitted', 'approved', 'active', 'closed', 'archived')",
            name="ck_catalogs_status_valid",
        ),
    )

    # Catalogs indexes
    op.create_index("ix_catalogs_company_id", "catalogs", ["company_id"])
    op.create_index("ix_catalogs_sub_brand_id", "catalogs", ["sub_brand_id"])
    op.create_index("ix_catalogs_company_id_status", "catalogs", ["company_id", "status"])

    # Partial unique index: slug unique per company, excluding soft-deleted rows
    op.execute(
        "CREATE UNIQUE INDEX uq_catalogs_company_id_slug "
        "ON catalogs (company_id, slug) WHERE deleted_at IS NULL"
    )

    # Catalogs RLS
    op.execute("ALTER TABLE catalogs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE catalogs FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY catalogs_company_isolation ON catalogs
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY catalogs_sub_brand_scoping ON catalogs AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 3. Create catalog_products junction table (TenantBase)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "catalog_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_catalog_products_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_catalog_products_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column(
            "catalog_id",
            UUID(as_uuid=True),
            sa.ForeignKey("catalogs.id", name="fk_catalog_products_catalog_id_catalogs"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", name="fk_catalog_products_product_id_products"),
            nullable=False,
        ),
        sa.Column("display_order", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("price_override", sa.Numeric(10, 2), nullable=True),
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
        # Unique constraint: a product can only appear once per catalog
        sa.UniqueConstraint("catalog_id", "product_id", name="uq_catalog_products_catalog_product"),
    )

    # Catalog_products indexes
    op.create_index("ix_catalog_products_company_id", "catalog_products", ["company_id"])
    op.create_index("ix_catalog_products_sub_brand_id", "catalog_products", ["sub_brand_id"])
    op.create_index("ix_catalog_products_catalog_id", "catalog_products", ["catalog_id"])
    op.create_index("ix_catalog_products_product_id", "catalog_products", ["product_id"])

    # Catalog_products RLS
    op.execute("ALTER TABLE catalog_products ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE catalog_products FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY catalog_products_company_isolation ON catalog_products
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY catalog_products_sub_brand_scoping ON catalog_products AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # Drop in reverse order: junction table first, then entity tables
    # ──────────────────────────────────────────────────────────────────────

    # 1. Drop catalog_products
    op.execute("DROP POLICY IF EXISTS catalog_products_sub_brand_scoping ON catalog_products")
    op.execute("DROP POLICY IF EXISTS catalog_products_company_isolation ON catalog_products")
    op.execute("ALTER TABLE catalog_products DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_catalog_products_product_id", table_name="catalog_products")
    op.drop_index("ix_catalog_products_catalog_id", table_name="catalog_products")
    op.drop_index("ix_catalog_products_sub_brand_id", table_name="catalog_products")
    op.drop_index("ix_catalog_products_company_id", table_name="catalog_products")
    op.drop_table("catalog_products")

    # 2. Drop catalogs
    op.execute("DROP POLICY IF EXISTS catalogs_sub_brand_scoping ON catalogs")
    op.execute("DROP POLICY IF EXISTS catalogs_company_isolation ON catalogs")
    op.execute("ALTER TABLE catalogs DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS uq_catalogs_company_id_slug")
    op.drop_index("ix_catalogs_company_id_status", table_name="catalogs")
    op.drop_index("ix_catalogs_sub_brand_id", table_name="catalogs")
    op.drop_index("ix_catalogs_company_id", table_name="catalogs")
    op.drop_table("catalogs")

    # 3. Drop products
    op.execute("DROP POLICY IF EXISTS products_sub_brand_scoping ON products")
    op.execute("DROP POLICY IF EXISTS products_company_isolation ON products")
    op.execute("ALTER TABLE products DISABLE ROW LEVEL SECURITY")
    op.execute("DROP INDEX IF EXISTS uq_products_company_id_sku")
    op.drop_index("ix_products_company_id_status", table_name="products")
    op.drop_index("ix_products_sub_brand_id", table_name="products")
    op.drop_index("ix_products_company_id", table_name="products")
    op.drop_table("products")
