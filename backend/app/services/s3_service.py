"""
S3 file storage service.

This is the ONLY file that wraps boto3 S3 operations. All other code calls this
service for pre-signed URL generation and file management. The service is injected
as a FastAPI dependency, making it easily mockable in tests.

S3 key structure is company-scoped: {company_id}/{category}/{uuid}.{ext}
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import structlog

from app.core.config import settings
from app.core.exceptions import ValidationError

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# File type validation rules per surviving category
# ---------------------------------------------------------------------------
_CATEGORY_RULES: dict[str, dict[str, Any]] = {
    "logos": {
        "allowed_types": {"image/png", "image/svg+xml", "image/jpeg"},
        "allowed_extensions": {".png", ".svg", ".jpg", ".jpeg"},
        "max_size_mb": 5,
    },
    "profiles": {
        "allowed_types": {"image/png", "image/jpeg"},
        "allowed_extensions": {".png", ".jpg", ".jpeg"},
        "max_size_mb": 5,
    },
}


class S3Service:
    def __init__(
        self,
        client: Any,
        bucket_name: str,
        cloudfront_domain: str | None = None,
    ) -> None:
        self._client = client
        self._bucket_name = bucket_name
        self._cloudfront_domain = cloudfront_domain

    def generate_upload_url(
        self,
        company_id: UUID,
        category: str,
        content_type: str,
        file_extension: str,
    ) -> tuple[str, str]:
        """Generate a pre-signed PUT URL for direct browser upload.

        Returns: (upload_url, s3_key)
        - Validates content_type against allowed types for the category
        - Generates a unique filename: {uuid}.{extension}
        - Builds the S3 key: {company_id}/{category}/{uuid}.{ext}
        - Pre-signed URL expires in 15 minutes
        """
        ext = file_extension.lower().strip()
        if not ext.startswith("."):
            ext = f".{ext}"

        rules = _CATEGORY_RULES.get(category)
        if rules is None:
            raise ValidationError(
                f"Invalid category '{category}'. Must be one of: {', '.join(_CATEGORY_RULES.keys())}"
            )

        if content_type not in rules["allowed_types"]:
            raise ValidationError(
                f"Content type '{content_type}' is not allowed for category '{category}'. "
                f"Allowed: {', '.join(sorted(rules['allowed_types']))}"
            )

        if ext not in rules["allowed_extensions"]:
            raise ValidationError(
                f"File extension '{ext}' is not allowed for category '{category}'. "
                f"Allowed: {', '.join(sorted(rules['allowed_extensions']))}"
            )

        unique_filename = f"{uuid4()}{ext}"
        s3_key = f"{company_id}/{category}/{unique_filename}"

        url = self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket_name,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=900,
        )

        logger.info(
            "upload_url_generated",
            s3_key=s3_key,
            category=category,
            content_type=content_type,
            company_id=str(company_id),
        )

        return url, s3_key

    def generate_download_url(self, s3_key: str) -> str:
        """Generate a pre-signed GET URL for file download (1 hour)."""
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket_name, "Key": s3_key},
            ExpiresIn=3600,
        )

        logger.info("download_url_generated", s3_key=s3_key)
        return url


def get_s3_service() -> S3Service:
    """FastAPI dependency — creates boto3 S3 client + returns S3Service."""
    import boto3  # type: ignore[import-untyped]

    client = boto3.client("s3", region_name=settings.AWS_REGION)
    return S3Service(
        client=client,
        bucket_name=settings.S3_BUCKET_NAME,
        cloudfront_domain=settings.CLOUDFRONT_DOMAIN,
    )
