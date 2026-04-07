from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str
    full_name: str
    role: str
    sub_brand_id: UUID


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    sub_brand_id: UUID | None = None
    is_active: bool | None = None


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
    created_at: datetime
    updated_at: datetime
