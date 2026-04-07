from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrgCodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    code: str
    is_active: bool
    created_by: UUID
    created_at: datetime
