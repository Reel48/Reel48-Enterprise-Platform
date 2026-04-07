from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ValidateOrgCodeRequest(BaseModel):
    code: str


class SubBrandSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    is_default: bool


class ValidateOrgCodeResponse(BaseModel):
    company_name: str
    sub_brands: list[SubBrandSummary]


class SelfRegisterRequest(BaseModel):
    code: str
    sub_brand_id: UUID
    email: str
    full_name: str
    password: str


class InviteRegisterRequest(BaseModel):
    token: str
    email: str
    full_name: str
    password: str


class RegisterResponse(BaseModel):
    message: str
