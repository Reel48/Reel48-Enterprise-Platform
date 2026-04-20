from typing import Literal

from pydantic import BaseModel, field_validator


class UploadUrlRequest(BaseModel):
    category: Literal["logos", "profiles"]
    content_type: str
    file_extension: str

    @field_validator("file_extension")
    @classmethod
    def normalize_extension(cls, v: str) -> str:
        """Ensure extension starts with a dot and is lowercase."""
        v = v.lower().strip()
        if not v.startswith("."):
            v = f".{v}"
        return v


class UploadUrlResponse(BaseModel):
    upload_url: str
    s3_key: str
    expires_in: int


class DownloadUrlRequest(BaseModel):
    s3_key: str


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int
