"""Storage API endpoints for pre-signed URL generation.

S3 key structure is company-scoped: {company_id}/{category}/{filename}.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import get_tenant_context
from app.core.exceptions import ForbiddenError
from app.core.tenant import TenantContext
from app.schemas.common import ApiResponse
from app.schemas.storage import (
    DownloadUrlRequest,
    DownloadUrlResponse,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.s3_service import S3Service, get_s3_service

router = APIRouter(prefix="/storage", tags=["storage"])


def _require_company_id(context: TenantContext) -> UUID:
    """Guard: tenant-scoped storage endpoints require company_id from context."""
    if context.company_id is None:
        raise ForbiddenError("Use platform endpoints for cross-company operations")
    return context.company_id


def _validate_download_key_tenant(s3_key: str, context: TenantContext) -> None:
    """Validate that the s3_key belongs to the user's tenant scope.

    CRITICAL: Prevents Company A users from generating download URLs for
    Company B's files by verifying the key's company_id prefix.
    """
    parts = s3_key.split("/")
    if len(parts) < 3:
        raise ForbiddenError("Invalid file path")

    key_company_id = parts[0]
    if str(context.company_id) != key_company_id:
        raise ForbiddenError("You do not have access to this file")


@router.post("/upload-url", response_model=ApiResponse[UploadUrlResponse])
async def generate_upload_url(
    body: UploadUrlRequest,
    context: TenantContext = Depends(get_tenant_context),
    s3_service: S3Service = Depends(get_s3_service),
) -> ApiResponse[UploadUrlResponse]:
    """Generate a pre-signed upload URL for direct browser upload to S3."""
    company_id = _require_company_id(context)

    upload_url, s3_key = s3_service.generate_upload_url(
        company_id=company_id,
        category=body.category,
        content_type=body.content_type,
        file_extension=body.file_extension,
    )

    return ApiResponse(
        data=UploadUrlResponse(
            upload_url=upload_url,
            s3_key=s3_key,
            expires_in=900,
        )
    )


@router.post("/download-url", response_model=ApiResponse[DownloadUrlResponse])
async def generate_download_url(
    body: DownloadUrlRequest,
    context: TenantContext = Depends(get_tenant_context),
    s3_service: S3Service = Depends(get_s3_service),
) -> ApiResponse[DownloadUrlResponse]:
    """Generate a pre-signed download URL for a file in S3.

    Validates that the s3_key belongs to the user's tenant scope.
    """
    _require_company_id(context)
    _validate_download_key_tenant(body.s3_key, context)

    download_url = s3_service.generate_download_url(body.s3_key)

    return ApiResponse(
        data=DownloadUrlResponse(
            download_url=download_url,
            expires_in=3600,
        )
    )
