"""Tests for the storage API endpoints (pre-signed URL generation).

Covers:
- Functional tests: upload/download URL generation, validation, extension normalization
- Isolation tests: cross-company and cross-sub-brand file access denial
- Authorization tests: unauthenticated, reel48_admin rejection, role-based access
"""

import pytest
from httpx import AsyncClient

from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Upload URL — Functional Tests
# ---------------------------------------------------------------------------


async def test_generate_upload_url_valid_products(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Valid upload URL request for products category returns 200 with URL and s3_key."""
    company, brand_a1, _a2 = company_a
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": ".png",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "upload_url" in data
    assert data["expires_in"] == 900
    # s3_key should follow pattern: {company_id}/{sub_brand_slug}/{category}/{uuid}.{ext}
    s3_key = data["s3_key"]
    parts = s3_key.split("/")
    assert parts[0] == str(company.id)
    assert parts[1] == "brand-a1"  # sub-brand slug
    assert parts[2] == "products"
    assert parts[3].endswith(".png")


async def test_generate_upload_url_valid_logos(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_admin_token: str,
):
    """Valid upload URL request for logos category returns 200."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "logos",
            "content_type": "image/svg+xml",
            "file_extension": ".svg",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["s3_key"].endswith(".svg")


async def test_generate_upload_url_valid_catalog_pdf(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_admin_token: str,
):
    """Valid upload URL request for catalog (PDF) category returns 200."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "catalog",
            "content_type": "application/pdf",
            "file_extension": ".pdf",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "catalog" in data["s3_key"]


async def test_generate_upload_url_valid_profiles(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Valid upload URL request for profiles category returns 200."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "profiles",
            "content_type": "image/jpeg",
            "file_extension": ".jpg",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "profiles" in data["s3_key"]
    assert data["s3_key"].endswith(".jpg")


async def test_upload_url_invalid_content_type_returns_422(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Invalid content_type for category returns 422."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/gif",
            "file_extension": ".gif",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert len(errors) > 0
    assert "image/gif" in errors[0]["message"]


async def test_upload_url_invalid_extension_returns_422(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Invalid file extension for category returns 422."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": ".bmp",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert len(errors) > 0
    assert ".bmp" in errors[0]["message"]


async def test_upload_url_extension_normalization_no_dot(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Extension without leading dot is normalized (png -> .png)."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": "png",  # no dot
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["s3_key"].endswith(".png")


async def test_upload_url_extension_normalization_uppercase(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Uppercase extension is normalized to lowercase."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": ".PNG",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["s3_key"].endswith(".png")


async def test_upload_url_corporate_admin_uses_shared_path(
    client: AsyncClient,
    company_a,
    company_a_corporate_admin_token: str,
):
    """Corporate admin (sub_brand_id=None) uploads use 'shared' path segment."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "logos",
            "content_type": "image/png",
            "file_extension": ".png",
        },
        headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
    )
    assert response.status_code == 200
    s3_key = response.json()["data"]["s3_key"]
    parts = s3_key.split("/")
    assert parts[1] == "shared"


async def test_upload_url_missing_fields_returns_422(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Missing required fields returns 422."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={"category": "products"},
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Download URL — Functional Tests
# ---------------------------------------------------------------------------


async def test_generate_download_url_valid(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Valid download URL request returns 200 with URL."""
    company, _a1, _a2 = company_a
    s3_key = f"{company.id}/brand-a1/products/test-file.png"
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": s3_key},
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert "download_url" in data
    assert data["expires_in"] == 3600
    assert s3_key in data["download_url"]


async def test_download_url_shared_assets(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Users can download shared assets for their company."""
    company, _a1, _a2 = company_a
    s3_key = f"{company.id}/shared/logos/company-logo.png"
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": s3_key},
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


async def test_company_b_cannot_download_company_a_file(
    client: AsyncClient,
    company_a,
    company_b,
    company_b_employee_token: str,
):
    """Company B user cannot generate download URL for Company A's file."""
    company_a_obj, _a1, _a2 = company_a
    s3_key = f"{company_a_obj.id}/brand-a1/products/secret-file.png"
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": s3_key},
        headers={"Authorization": f"Bearer {company_b_employee_token}"},
    )
    assert response.status_code == 403


async def test_corporate_admin_can_download_any_sub_brand_file(
    client: AsyncClient,
    company_a,
    company_a_corporate_admin_token: str,
):
    """Corporate admin CAN download files from any sub-brand in their company."""
    company, _a1, brand_a2 = company_a
    s3_key = f"{company.id}/brand-a2/products/file.png"
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": s3_key},
        headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
    )
    assert response.status_code == 200


async def test_download_url_invalid_path_returns_403(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Download URL with too few path segments returns 403."""
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": "bad/path"},
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


async def test_upload_url_unauthenticated_returns_401(
    client: AsyncClient,
):
    """Unauthenticated upload URL request returns 401/403."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": ".png",
        },
    )
    assert response.status_code == 401


async def test_download_url_unauthenticated_returns_401(
    client: AsyncClient,
):
    """Unauthenticated download URL request returns 401."""
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": "some-company/brand/products/file.png"},
    )
    assert response.status_code == 401


async def test_reel48_admin_rejected_on_upload(
    client: AsyncClient,
    reel48_admin_token: str,
):
    """reel48_admin is rejected on tenant-scoped storage endpoints."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": ".png",
        },
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 403
    assert "platform" in response.json()["errors"][0]["message"].lower()


async def test_reel48_admin_rejected_on_download(
    client: AsyncClient,
    reel48_admin_token: str,
):
    """reel48_admin is rejected on tenant-scoped download endpoint."""
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": "some-id/brand/products/file.png"},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 403


async def test_all_roles_can_upload(
    client: AsyncClient,
    company_a,
):
    """All authenticated tenant roles can generate upload URLs."""
    company, brand_a1, _a2 = company_a
    roles = ["employee", "regional_manager", "sub_brand_admin", "corporate_admin"]

    for role in roles:
        sub_brand_id = None if role == "corporate_admin" else str(brand_a1.id)
        token = create_test_token(
            company_id=str(company.id),
            sub_brand_id=sub_brand_id,
            role=role,
        )
        response = await client.post(
            "/api/v1/storage/upload-url",
            json={
                "category": "profiles",
                "content_type": "image/jpeg",
                "file_extension": ".jpg",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, f"Role {role} failed with {response.status_code}"


async def test_all_roles_can_download_own_company(
    client: AsyncClient,
    company_a,
):
    """All authenticated tenant roles can generate download URLs for their own company."""
    company, brand_a1, _a2 = company_a
    s3_key = f"{company.id}/brand-a1/products/file.png"
    roles = ["employee", "regional_manager", "sub_brand_admin", "corporate_admin"]

    for role in roles:
        sub_brand_id = None if role == "corporate_admin" else str(brand_a1.id)
        token = create_test_token(
            company_id=str(company.id),
            sub_brand_id=sub_brand_id,
            role=role,
        )
        response = await client.post(
            "/api/v1/storage/download-url",
            json={"s3_key": s3_key},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, f"Role {role} failed with {response.status_code}"


# ---------------------------------------------------------------------------
# Mock S3 Service verification
# ---------------------------------------------------------------------------


async def test_mock_s3_records_upload_calls(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
    mock_s3,
):
    """Verify the mock S3 service records upload URL generation calls."""
    response = await client.post(
        "/api/v1/storage/upload-url",
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": ".png",
        },
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200
    assert len(mock_s3.generated_upload_urls) == 1
    assert mock_s3.generated_upload_urls[0]["category"] == "products"
    assert mock_s3.generated_upload_urls[0]["content_type"] == "image/png"


async def test_mock_s3_records_download_calls(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
    mock_s3,
):
    """Verify the mock S3 service records download URL generation calls."""
    company, _a1, _a2 = company_a
    s3_key = f"{company.id}/brand-a1/products/file.png"
    response = await client.post(
        "/api/v1/storage/download-url",
        json={"s3_key": s3_key},
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 200
    assert len(mock_s3.generated_download_urls) == 1
    assert mock_s3.generated_download_urls[0]["s3_key"] == s3_key
