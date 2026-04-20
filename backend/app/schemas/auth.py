from pydantic import BaseModel, field_validator


class ValidateOrgCodeRequest(BaseModel):
    code: str


class ValidateOrgCodeResponse(BaseModel):
    company_name: str


class SelfRegisterRequest(BaseModel):
    code: str
    email: str
    full_name: str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class InviteRegisterRequest(BaseModel):
    token: str
    email: str
    full_name: str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RegisterResponse(BaseModel):
    message: str
