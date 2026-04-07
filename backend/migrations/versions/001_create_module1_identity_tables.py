"""create_module1_identity_tables

Creates the 5 identity tables for Module 1 (Auth & Multi-Tenancy):
  companies, sub_brands, org_codes, users, invites

Each table includes RLS policies in the same migration (per harness rules).
Circular FK between org_codes.created_by and users is resolved by deferring
the org_codes FK constraint until after users is created.

Revision ID: 001
Revises:
Create Date: 2026-04-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. companies (GlobalBase — no tenant FK columns)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("stripe_customer_id", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
    )

    # RLS for companies: id-based isolation (this IS the tenant table)
    op.execute("ALTER TABLE companies ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE companies FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY companies_isolation ON companies
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR id = current_setting('app.current_company_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 2. sub_brands (CompanyBase — company_id only)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "sub_brands",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_sub_brands_company_id_companies"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
        sa.UniqueConstraint("company_id", "slug", name="uq_sub_brands_company_id_slug"),
    )
    op.create_index("ix_sub_brands_company_id", "sub_brands", ["company_id"])

    # RLS for sub_brands: company isolation only (no sub-brand scoping — it IS the sub-brand)
    op.execute("ALTER TABLE sub_brands ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE sub_brands FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY sub_brands_company_isolation ON sub_brands
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 3. org_codes (CompanyBase — company_id only)
    #    NOTE: created_by is a plain UUID column here. The FK to users is
    #    added in step 6 after the users table exists (circular dependency).
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "org_codes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_org_codes_company_id_companies"),
            nullable=False,
        ),
        sa.Column("code", sa.String(8), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", UUID(as_uuid=True), nullable=False),  # FK deferred
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
    )
    op.create_index("ix_org_codes_company_id", "org_codes", ["company_id"])

    # RLS for org_codes: company isolation only
    op.execute("ALTER TABLE org_codes ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE org_codes FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY org_codes_company_isolation ON org_codes
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 4. users (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_users_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_users_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column("cognito_sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column(
            "registration_method",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'invite'"),
        ),
        sa.Column(
            "org_code_id",
            UUID(as_uuid=True),
            sa.ForeignKey("org_codes.id", name="fk_users_org_code_id_org_codes"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
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
    )
    op.create_index("ix_users_company_id", "users", ["company_id"])
    op.create_index("ix_users_sub_brand_id", "users", ["sub_brand_id"])
    op.create_index("ix_users_org_code_id", "users", ["org_code_id"])

    # RLS for users: company isolation + sub-brand scoping
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY users_company_isolation ON users
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY users_sub_brand_scoping ON users AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 5. invites (CompanyBase — company_id only)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "invites",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_invites_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "target_sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_invites_target_sub_brand_id_sub_brands"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default=sa.text("'employee'")),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_invites_created_by_users"),
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
    )
    op.create_index("ix_invites_company_id", "invites", ["company_id"])
    op.create_index("ix_invites_target_sub_brand_id", "invites", ["target_sub_brand_id"])
    op.create_index("ix_invites_created_by", "invites", ["created_by"])

    # RLS for invites: company isolation only
    op.execute("ALTER TABLE invites ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE invites FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invites_company_isolation ON invites
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)

    # ──────────────────────────────────────────────────────────────────────
    # 6. Deferred FK: org_codes.created_by → users.id
    # ──────────────────────────────────────────────────────────────────────
    op.create_foreign_key(
        "fk_org_codes_created_by_users",
        "org_codes",
        "users",
        ["created_by"],
        ["id"],
    )
    op.create_index("ix_org_codes_created_by", "org_codes", ["created_by"])


def downgrade() -> None:
    # Reverse order: drop deferred FK, then tables from last to first.
    # RLS policies are dropped before each table.

    # 6. Drop deferred FK on org_codes.created_by
    op.drop_index("ix_org_codes_created_by", table_name="org_codes")
    op.drop_constraint("fk_org_codes_created_by_users", "org_codes", type_="foreignkey")

    # 5. invites
    op.execute("DROP POLICY IF EXISTS invites_company_isolation ON invites")
    op.execute("ALTER TABLE invites DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_invites_created_by", table_name="invites")
    op.drop_index("ix_invites_target_sub_brand_id", table_name="invites")
    op.drop_index("ix_invites_company_id", table_name="invites")
    op.drop_table("invites")

    # 4. users
    op.execute("DROP POLICY IF EXISTS users_sub_brand_scoping ON users")
    op.execute("DROP POLICY IF EXISTS users_company_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_users_org_code_id", table_name="users")
    op.drop_index("ix_users_sub_brand_id", table_name="users")
    op.drop_index("ix_users_company_id", table_name="users")
    op.drop_table("users")

    # 3. org_codes
    op.execute("DROP POLICY IF EXISTS org_codes_company_isolation ON org_codes")
    op.execute("ALTER TABLE org_codes DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_org_codes_company_id", table_name="org_codes")
    op.drop_table("org_codes")

    # 2. sub_brands
    op.execute("DROP POLICY IF EXISTS sub_brands_company_isolation ON sub_brands")
    op.execute("ALTER TABLE sub_brands DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_sub_brands_company_id", table_name="sub_brands")
    op.drop_table("sub_brands")

    # 1. companies
    op.execute("DROP POLICY IF EXISTS companies_isolation ON companies")
    op.execute("ALTER TABLE companies DISABLE ROW LEVEL SECURITY")
    op.drop_table("companies")
