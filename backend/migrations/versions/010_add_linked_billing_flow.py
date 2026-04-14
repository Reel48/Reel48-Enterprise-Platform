"""add_linked_billing_flow

Adds 'linked' to the invoices billing_flow CHECK constraint to support
importing existing Stripe invoices (including historical ones) into the
platform without creating them through the order/catalog flows.

Revision ID: 010
Revises: 009
Create Date: 2026-04-13
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old CHECK constraint and recreate with 'linked' added.
    op.drop_constraint("ck_invoices_billing_flow_valid", "invoices", type_="check")
    op.create_check_constraint(
        "ck_invoices_billing_flow_valid",
        "invoices",
        "billing_flow IN ('assigned', 'self_service', 'post_window', 'linked')",
    )


def downgrade() -> None:
    # Revert to original constraint (without 'linked').
    # NOTE: Will fail if any rows have billing_flow = 'linked'.
    op.drop_constraint("ck_invoices_billing_flow_valid", "invoices", type_="check")
    op.create_check_constraint(
        "ck_invoices_billing_flow_valid",
        "invoices",
        "billing_flow IN ('assigned', 'self_service', 'post_window')",
    )
