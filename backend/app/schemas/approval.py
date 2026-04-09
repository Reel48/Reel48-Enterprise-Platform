from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ApprovalDecisionRequest(BaseModel):
    """Used for POST /approvals/{id}/approve and /reject."""

    decision_notes: str | None = None


class ApprovalRuleCreate(BaseModel):
    """Used for POST /approval_rules/."""

    entity_type: str
    rule_type: str
    threshold_amount: float
    required_role: str

    @field_validator("entity_type")
    @classmethod
    def validate_entity_type(cls, v: str) -> str:
        allowed = {"order", "bulk_order"}
        if v not in allowed:
            raise ValueError(f"entity_type must be one of {allowed}")
        return v

    @field_validator("rule_type")
    @classmethod
    def validate_rule_type(cls, v: str) -> str:
        allowed = {"amount_threshold"}
        if v not in allowed:
            raise ValueError(f"rule_type must be one of {allowed}")
        return v

    @field_validator("required_role")
    @classmethod
    def validate_required_role(cls, v: str) -> str:
        allowed = {"corporate_admin", "sub_brand_admin", "regional_manager"}
        if v not in allowed:
            raise ValueError(f"required_role must be one of {allowed}")
        return v

    @field_validator("threshold_amount")
    @classmethod
    def threshold_must_be_positive(cls, v: float) -> float:
        if v < 0:
            raise ValueError("threshold_amount must be >= 0")
        return v


class ApprovalRuleUpdate(BaseModel):
    """Used for PATCH /approval_rules/{id}."""

    threshold_amount: float | None = None
    required_role: str | None = None
    is_active: bool | None = None

    @field_validator("required_role")
    @classmethod
    def validate_required_role(cls, v: str | None) -> str | None:
        if v is not None:
            allowed = {"corporate_admin", "sub_brand_admin", "regional_manager"}
            if v not in allowed:
                raise ValueError(f"required_role must be one of {allowed}")
        return v

    @field_validator("threshold_amount")
    @classmethod
    def threshold_must_be_positive(cls, v: float | None) -> float | None:
        if v is not None and v < 0:
            raise ValueError("threshold_amount must be >= 0")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ApprovalRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    entity_type: str
    entity_id: UUID
    requested_by: UUID
    decided_by: UUID | None
    status: str
    decision_notes: str | None
    requested_at: datetime
    decided_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApprovalQueueItem(BaseModel):
    """Extended response for queue endpoints -- includes entity summary."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str
    entity_id: UUID
    status: str
    requested_by: UUID
    requested_at: datetime
    # Denormalized entity fields for queue display:
    entity_name: str
    entity_amount: float | None


class ApprovalRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    entity_type: str
    rule_type: str
    threshold_amount: float | None
    required_role: str
    is_active: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
