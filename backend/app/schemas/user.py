from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class UserCreate(BaseModel):
    email: str
    full_name: str
    role: str
    sub_brand_id: UUID

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    sub_brand_id: UUID | None = None
    is_active: bool | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is not None:
            return v.strip().lower()
        return v


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    email: str
    full_name: str
    role: str
    registration_method: str
    is_active: bool
    company_name: str | None = None
    created_at: datetime
    updated_at: datetime
