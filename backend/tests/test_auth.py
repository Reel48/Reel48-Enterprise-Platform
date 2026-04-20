"""Tests for unauthenticated auth endpoints (validate-org-code, register)."""

import pytest
from httpx import AsyncClient

from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# validate-org-code
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_org_code_returns_company_name_for_valid_code(
    client: AsyncClient, org_code_a, company_a
) -> None:
    resp = await client.post(
        "/api/v1/auth/validate-org-code",
        json={"code": org_code_a.code},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["company_name"] == company_a.name
    assert "sub_brands" not in body["data"]


@pytest.mark.asyncio
async def test_validate_org_code_400_on_invalid_code(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/validate-org-code",
        json={"code": "NOSUCH01"},
    )
    assert resp.status_code == 400
    assert resp.json()["errors"][0]["code"] == "INVALID_REQUEST"


# ---------------------------------------------------------------------------
# register (single-step)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_single_step_creates_employee(
    client: AsyncClient, org_code_a
) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "code": org_code_a.code,
            "email": "NEW@companya.com",
            "full_name": "New Hire",
            "password": "Valid-Passw0rd!",
        },
    )
    assert resp.status_code == 201
    assert "successful" in resp.json()["data"]["message"].lower()


@pytest.mark.asyncio
async def test_register_400_on_invalid_code(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "code": "NOSUCH01",
            "email": "foo@x.com",
            "full_name": "F",
            "password": "Valid-Passw0rd!",
        },
    )
    assert resp.status_code == 400
    assert resp.json()["errors"][0]["code"] == "REGISTRATION_FAILED"


# ---------------------------------------------------------------------------
# Role normalizer (legacy JWT roles get mapped server-side)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_legacy_corporate_admin_role_mapped_to_company_admin(
    client: AsyncClient, company_a
) -> None:
    token = create_test_token(company_id=str(company_a.id), role="corporate_admin")
    resp = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    # company_admin can list users → 200
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_legacy_regional_manager_mapped_to_manager(
    client: AsyncClient, company_a
) -> None:
    token = create_test_token(company_id=str(company_a.id), role="regional_manager")
    # Manager cannot list users (only company_admin+) → 403
    resp = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
