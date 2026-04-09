"""create_module6_approval_tables

Creates two tables for Module 6 (Approval Workflows):
  - approval_requests: Tracks approval requests for products, catalogs, orders, bulk orders
  - approval_rules: Company-level rules that define when approval is required

approval_requests uses TenantBase shape (company_id + sub_brand_id) with standard RLS policies.
approval_rules uses CompanyBase shape (company_id only) with company isolation RLS only.

Revision ID: 006
Revises: 005
Create Date: 2026-04-09
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. Create approval_requests table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "approval_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_approval_requests_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_approval_requests_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "requested_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_approval_requests_requested_by_users"),
            nullable=False,
        ),
        sa.Column(
            "decided_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_approval_requests_decided_by_users"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("decision_notes", sa.Text, nullable=True),
        sa.Column(
            "requested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
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
            "entity_type IN ('product', 'catalog', 'order', 'bulk_order')",
            name="ck_approval_requests_entity_type_valid",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved', 'rejected')",
            name="ck_approval_requests_status_valid",
        ),
    )

    # approval_requests indexes
    op.create_index(
        "ix_approval_requests_company_id", "approval_requests", ["company_id"]
    )
    op.create_index(
        "ix_approval_requests_sub_brand_id", "approval_requests", ["sub_brand_id"]
    )
    op.create_index(
        "ix_approval_requests_entity_type_entity_id",
        "approval_requests",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_approval_requests_status", "approval_requests", ["status"]
    )
    op.create_index(
        "ix_approval_requests_company_id_status",
        "approval_requests",
        ["company_id", "status"],
    )
    op.create_index(
        "ix_approval_requests_requested_by", "approval_requests", ["requested_by"]
    )
    op.create_index(
        "ix_approval_requests_decided_by", "approval_requests", ["decided_by"]
    )

    # approval_requests RLS
    op.execute("ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE approval_requests FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY approval_requests_company_isolation ON approval_requests
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY approval_requests_sub_brand_scoping ON approval_requests AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 2. Create approval_rules table (CompanyBase — company_id only)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "approval_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_approval_rules_company_id_companies"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("rule_type", sa.String(30), nullable=False),
        sa.Column("threshold_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("required_role", sa.String(50), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_approval_rules_created_by_users"),
            nullable=False,
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
            "entity_type IN ('order', 'bulk_order')",
            name="ck_approval_rules_entity_type_valid",
        ),
        sa.CheckConstraint(
            "rule_type IN ('amount_threshold')",
            name="ck_approval_rules_rule_type_valid",
        ),
        sa.CheckConstraint(
            "required_role IN ('corporate_admin', 'sub_brand_admin', 'regional_manager')",
            name="ck_approval_rules_required_role_valid",
        ),
        sa.CheckConstraint(
            "threshold_amount >= 0",
            name="ck_approval_rules_threshold_non_negative",
        ),
        # UNIQUE constraint: one rule per type per company
        sa.UniqueConstraint(
            "company_id", "entity_type", "rule_type",
            name="uq_approval_rules_company_entity_rule",
        ),
    )

    # approval_rules indexes
    op.create_index(
        "ix_approval_rules_company_id", "approval_rules", ["company_id"]
    )
    op.create_index(
        "ix_approval_rules_company_id_entity_type",
        "approval_rules",
        ["company_id", "entity_type"],
    )

    # approval_rules RLS (company isolation only — no sub-brand scoping)
    op.execute("ALTER TABLE approval_rules ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE approval_rules FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY approval_rules_company_isolation ON approval_rules
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)


def downgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # Drop in reverse order: approval_rules first, then approval_requests
    # ──────────────────────────────────────────────────────────────────────

    # 1. Drop approval_rules
    op.execute(
        "DROP POLICY IF EXISTS approval_rules_company_isolation ON approval_rules"
    )
    op.execute("ALTER TABLE approval_rules DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_approval_rules_company_id_entity_type", table_name="approval_rules")
    op.drop_index("ix_approval_rules_company_id", table_name="approval_rules")
    op.drop_table("approval_rules")

    # 2. Drop approval_requests
    op.execute(
        "DROP POLICY IF EXISTS approval_requests_sub_brand_scoping ON approval_requests"
    )
    op.execute(
        "DROP POLICY IF EXISTS approval_requests_company_isolation ON approval_requests"
    )
    op.execute("ALTER TABLE approval_requests DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_approval_requests_decided_by", table_name="approval_requests")
    op.drop_index("ix_approval_requests_requested_by", table_name="approval_requests")
    op.drop_index("ix_approval_requests_company_id_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_entity_type_entity_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_sub_brand_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_company_id", table_name="approval_requests")
    op.drop_table("approval_requests")
