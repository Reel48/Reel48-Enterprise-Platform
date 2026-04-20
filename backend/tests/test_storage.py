"""Tests for /api/v1/storage endpoints (pre-signed URL generation)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upload_url_success(
    client: AsyncClient, company_a, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/storage/upload-url",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "category": "logos",
            "content_type": "image/png",
            "file_extension": "png",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert str(company_a.id) in data["s3_key"]
    assert "/logos/" in data["s3_key"]
    assert data["expires_in"] == 900


@pytest.mark.asyncio
async def test_upload_url_rejects_invalid_category(
    client: AsyncClient, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/storage/upload-url",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "category": "products",
            "content_type": "image/png",
            "file_extension": "png",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_url_rejects_mismatched_content_type(
    client: AsyncClient, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/storage/upload-url",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "category": "profiles",
            "content_type": "image/webp",
            "file_extension": "webp",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_download_url_validates_company_prefix(
    client: AsyncClient, company_a, company_b, user_a_employee_token
) -> None:
    own = f"{company_a.id}/profiles/test.png"
    resp = await client.post(
        "/api/v1/storage/download-url",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"s3_key": own},
    )
    assert resp.status_code == 200

    other = f"{company_b.id}/profiles/test.png"
    resp = await client.post(
        "/api/v1/storage/download-url",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"s3_key": other},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reel48_admin_forbidden_on_tenant_storage(
    client: AsyncClient, reel48_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/storage/upload-url",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
        json={
            "category": "logos",
            "content_type": "image/png",
            "file_extension": "png",
        },
    )
    assert resp.status_code == 403
