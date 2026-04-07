from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SubBrandCreate(BaseModel):
    name: str
    slug: str


class SubBrandUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    is_active: bool | None = None


class SubBrandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    name: str
    slug: str
    is_default: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
