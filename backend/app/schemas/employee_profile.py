from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

VALID_SHIRT_SIZES = {"XS", "S", "M", "L", "XL", "2XL", "3XL"}


class EmployeeProfileCreate(BaseModel):
    """All profile fields optional on creation. No user_id — set server-side."""

    department: str | None = None
    job_title: str | None = None
    location: str | None = None
    shirt_size: str | None = None
    pant_size: str | None = None
    shoe_size: str | None = None
    delivery_address_line1: str | None = None
    delivery_address_line2: str | None = None
    delivery_city: str | None = None
    delivery_state: str | None = None
    delivery_zip: str | None = None
    delivery_country: str | None = None
    notes: str | None = None
    profile_photo_url: str | None = None

    @field_validator("shirt_size", mode="before")
    @classmethod
    def validate_shirt_size(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_SHIRT_SIZES:
            raise ValueError(
                f"shirt_size must be one of {sorted(VALID_SHIRT_SIZES)}"
            )
        return v


class EmployeeProfileUpdate(BaseModel):
    """All fields optional for partial update. Adds onboarding_complete."""

    department: str | None = None
    job_title: str | None = None
    location: str | None = None
    shirt_size: str | None = None
    pant_size: str | None = None
    shoe_size: str | None = None
    delivery_address_line1: str | None = None
    delivery_address_line2: str | None = None
    delivery_city: str | None = None
    delivery_state: str | None = None
    delivery_zip: str | None = None
    delivery_country: str | None = None
    notes: str | None = None
    profile_photo_url: str | None = None
    onboarding_complete: bool | None = None

    @field_validator("shirt_size", mode="before")
    @classmethod
    def validate_shirt_size(cls, v: str | None) -> str | None:
        if v is not None and v not in VALID_SHIRT_SIZES:
            raise ValueError(
                f"shirt_size must be one of {sorted(VALID_SHIRT_SIZES)}"
            )
        return v


class EmployeeProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    sub_brand_id: UUID | None
    user_id: UUID
    department: str | None
    job_title: str | None
    location: str | None
    shirt_size: str | None
    pant_size: str | None
    shoe_size: str | None
    delivery_address_line1: str | None
    delivery_address_line2: str | None
    delivery_city: str | None
    delivery_state: str | None
    delivery_zip: str | None
    delivery_country: str | None
    notes: str | None
    profile_photo_url: str | None
    onboarding_complete: bool
    created_at: datetime
    updated_at: datetime
