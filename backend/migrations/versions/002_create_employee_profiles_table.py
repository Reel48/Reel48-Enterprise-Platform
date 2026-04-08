"""create_employee_profiles_table

Creates the employee_profiles table for Module 2 (Employee Profiles).
One profile per user storing sizing, department, delivery address, and preferences.

Uses TenantBase shape (company_id + sub_brand_id) with standard RLS policies.

Revision ID: 002
Revises: 001
Create Date: 2026-04-08
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ──────────────────────────────────────────────────────────────────────
    # 1. Create employee_profiles table (TenantBase — company_id + sub_brand_id)
    # ──────────────────────────────────────────────────────────────────────
    op.create_table(
        "employee_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "company_id",
            UUID(as_uuid=True),
            sa.ForeignKey("companies.id", name="fk_employee_profiles_company_id_companies"),
            nullable=False,
        ),
        sa.Column(
            "sub_brand_id",
            UUID(as_uuid=True),
            sa.ForeignKey("sub_brands.id", name="fk_employee_profiles_sub_brand_id_sub_brands"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", name="fk_employee_profiles_user_id_users"),
            nullable=False,
            unique=True,
        ),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("shirt_size", sa.String(10), nullable=True),
        sa.Column("pant_size", sa.String(20), nullable=True),
        sa.Column("shoe_size", sa.String(20), nullable=True),
        sa.Column("delivery_address_line1", sa.String(255), nullable=True),
        sa.Column("delivery_address_line2", sa.String(255), nullable=True),
        sa.Column("delivery_city", sa.String(100), nullable=True),
        sa.Column("delivery_state", sa.String(100), nullable=True),
        sa.Column("delivery_zip", sa.String(20), nullable=True),
        sa.Column("delivery_country", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("profile_photo_url", sa.Text, nullable=True),
        sa.Column(
            "onboarding_complete",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
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
    )

    # 2. Create indexes
    op.create_index("ix_employee_profiles_company_id", "employee_profiles", ["company_id"])
    op.create_index("ix_employee_profiles_sub_brand_id", "employee_profiles", ["sub_brand_id"])
    op.create_index("ix_employee_profiles_user_id", "employee_profiles", ["user_id"])
    op.create_index(
        "ix_employee_profiles_company_id_department",
        "employee_profiles",
        ["company_id", "department"],
    )

    # 3. Enable RLS and create policies
    op.execute("ALTER TABLE employee_profiles ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE employee_profiles FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY employee_profiles_company_isolation ON employee_profiles
            USING (
                current_setting('app.current_company_id', true) IS NULL
                OR current_setting('app.current_company_id', true) = ''
                OR company_id = current_setting('app.current_company_id')::uuid
            )
    """)
    op.execute("""
        CREATE POLICY employee_profiles_sub_brand_scoping ON employee_profiles AS RESTRICTIVE
            USING (
                current_setting('app.current_sub_brand_id', true) IS NULL
                OR current_setting('app.current_sub_brand_id', true) = ''
                OR sub_brand_id = current_setting('app.current_sub_brand_id')::uuid
            )
    """)


def downgrade() -> None:
    # Drop RLS policies before table
    op.execute("DROP POLICY IF EXISTS employee_profiles_sub_brand_scoping ON employee_profiles")
    op.execute("DROP POLICY IF EXISTS employee_profiles_company_isolation ON employee_profiles")
    op.execute("ALTER TABLE employee_profiles DISABLE ROW LEVEL SECURITY")

    # Drop indexes
    op.drop_index("ix_employee_profiles_company_id_department", table_name="employee_profiles")
    op.drop_index("ix_employee_profiles_user_id", table_name="employee_profiles")
    op.drop_index("ix_employee_profiles_sub_brand_id", table_name="employee_profiles")
    op.drop_index("ix_employee_profiles_company_id", table_name="employee_profiles")

    # Drop table
    op.drop_table("employee_profiles")
