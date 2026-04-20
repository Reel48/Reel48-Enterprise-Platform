"""create_notifications_table

Creates the notifications table for the in-app announcement feed.

Uses CompanyBase shape (company_id only) with the standard RLS policy.

Revision ID: 003
Revises: 002
Create Date: 2026-04-20
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
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_notifications_company_id_companies"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("notification_type", sa.String(30), nullable=False),
        sa.Column("target_scope", sa.String(20), nullable=False, server_default="company"),
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
        sa.CheckConstraint(
            "notification_type IN ('announcement', 'system')",
            name="ck_notifications_notification_type_valid",
        ),
        sa.CheckConstraint(
            "target_scope IN ('company', 'individual')",
            name="ck_notifications_target_scope_valid",
        ),
    )

    op.create_index("ix_notifications_company_id", "notifications", ["company_id"])
    op.create_index("ix_notifications_target_user_id", "notifications", ["target_user_id"])
    op.create_index(
        "ix_notifications_company_id_is_active_created_at",
        "notifications",
        ["company_id", "is_active", sa.text("created_at DESC")],
    )

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


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS notifications_company_isolation ON notifications")
    op.execute("ALTER TABLE notifications DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_notifications_company_id_is_active_created_at", table_name="notifications"
    )
    op.drop_index("ix_notifications_target_user_id", table_name="notifications")
    op.drop_index("ix_notifications_company_id", table_name="notifications")

    op.drop_table("notifications")
