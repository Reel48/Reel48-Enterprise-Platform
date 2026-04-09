from sqlalchemy import Boolean, Column, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import CompanyBase


class ApprovalRule(CompanyBase):
    """
    Company-level rules that define when approval is required for orders/bulk orders.
    Uses CompanyBase (company_id only, no sub_brand_id).
    RLS: approval_rules_company_isolation policy on company_id only.
    One rule per (company_id, entity_type, rule_type) combination.
    """

    __tablename__ = "approval_rules"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "entity_type", "rule_type",
            name="uq_approval_rules_company_entity_rule",
        ),
    )

    entity_type = Column(String(30), nullable=False)
    rule_type = Column(String(30), nullable=False)
    threshold_amount = Column(Numeric(10, 2), nullable=True)
    required_role = Column(String(50), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", name="fk_approval_rules_created_by_users"),
        nullable=False,
    )
