from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class InviteCreate(BaseModel):
    email: str
    role: str = "employee"

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class InviteResponse(BaseModel):
    """Full invite details including unmasked token. Used on POST create."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    email: str
    role: str
    token: str
    expires_at: datetime
    consumed_at: datetime | None
    created_by: UUID
    created_at: datetime


class InviteListItem(BaseModel):
    """Invite details with masked token. Used on GET list."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    email: str
    role: str
    token: str
    expires_at: datetime
    consumed_at: datetime | None
    created_by: UUID
    created_at: datetime

    @field_validator("token", mode="before")
    @classmethod
    def mask_token(cls, v: str) -> str:
        return v[:8] + "..." if len(v) > 8 else v
