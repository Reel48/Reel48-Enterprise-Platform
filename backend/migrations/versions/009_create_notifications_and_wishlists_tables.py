"""create_notifications_and_wishlists_tables

Creates the notifications and wishlists tables for Module 9 (Employee Engagement).

Both tables use TenantBase shape (company_id + sub_brand_id) with standard RLS policies:
  - {table}_company_isolation (PERMISSIVE)
  - {table}_sub_brand_scoping (RESTRICTIVE)

Revision ID: 009
Revises: 007
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. Create notifications table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_notifications_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_notifications_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("target_scope", sa.String(20), nullable=False, server_default="sub_brand"),
        sa.Column(
            "target_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_notifications_target_user_id_users"),
            nullable=True,
        ),
        sa.Column("read_by", JSONB, nullable=False, server_default="[]"),
        sa.Column("link_url", sa.String(500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_notifications_created_by_users"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
            "notification_type IN ('announcement', 'catalog_available', "
            "'buying_window_reminder', 'order_update')",
            name="ck_notifications_notification_type_valid",
        ),
        sa.CheckConstraint(
            "target_scope IN ('company', 'sub_brand', 'individual')",
            name="ck_notifications_target_scope_valid",
        ),
    )

    # ──────────────────────────────────────────────────────────────────────
    # 2. Notifications indexes
    # ──────────────────────────────────────────────────────────────────────
    op.create_index("ix_notifications_company_id", "notifications", ["company_id"])
    op.create_index("ix_notifications_sub_brand_id", "notifications", ["sub_brand_id"])
    op.create_index("ix_notifications_target_user_id", "notifications", ["target_user_id"])
    op.create_index(
        "ix_notifications_company_id_is_active_created_at",
        "notifications",
        ["company_id", "is_active", sa.text("created_at DESC")],
    )

    # ──────────────────────────────────────────────────────────────────────
    # 3. Notifications RLS policies
    # ──────────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE notifications ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE notifications FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY notifications_company_isolation ON notifications
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY notifications_sub_brand_scoping ON notifications AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 4. Create wishlists table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "wishlists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_wishlists_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_wishlists_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_wishlists_user_id_users"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("products.id", name="fk_wishlists_product_id_products"),
            nullable=False,
        ),
        sa.Column(
            "catalog_id",
            UUID(as_uuid=True),
            sa.ForeignKey("catalogs.id", name="fk_wishlists_catalog_id_catalogs"),
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
        # UNIQUE constraint: one wishlist entry per user per product
        sa.UniqueConstraint("user_id", "product_id", name="uq_wishlists_user_id_product_id"),
    )

    # ──────────────────────────────────────────────────────────────────────
    # 5. Wishlists indexes
    # ──────────────────────────────────────────────────────────────────────
    op.create_index("ix_wishlists_company_id", "wishlists", ["company_id"])
    op.create_index("ix_wishlists_sub_brand_id", "wishlists", ["sub_brand_id"])
    op.create_index(
        "ix_wishlists_user_id_created_at",
        "wishlists",
        ["user_id", sa.text("created_at DESC")],
    )

    # ──────────────────────────────────────────────────────────────────────
    # 6. Wishlists RLS policies
    # ──────────────────────────────────────────────────────────────────────
    op.execute("ALTER TABLE wishlists ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE wishlists FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY wishlists_company_isolation ON wishlists
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY wishlists_sub_brand_scoping ON wishlists AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # Drop wishlists (RLS policies first)
    # ──────────────────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS wishlists_sub_brand_scoping ON wishlists")
    op.execute("DROP POLICY IF EXISTS wishlists_company_isolation ON wishlists")
    op.execute("ALTER TABLE wishlists DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_wishlists_user_id_created_at", table_name="wishlists")
    op.drop_index("ix_wishlists_sub_brand_id", table_name="wishlists")
    op.drop_index("ix_wishlists_company_id", table_name="wishlists")
    op.drop_table("wishlists")

    # ──────────────────────────────────────────────────────────────────────
    # Drop notifications (RLS policies first)
    # ──────────────────────────────────────────────────────────────────────
    op.execute("DROP POLICY IF EXISTS notifications_sub_brand_scoping ON notifications")
    op.execute("DROP POLICY IF EXISTS notifications_company_isolation ON notifications")
    op.execute("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_notifications_company_id_is_active_created_at", table_name="notifications"
    )
    op.drop_index("ix_notifications_target_user_id", table_name="notifications")
    op.drop_index("ix_notifications_sub_brand_id", table_name="notifications")
    op.drop_index("ix_notifications_company_id", table_name="notifications")
    op.drop_table("notifications")
