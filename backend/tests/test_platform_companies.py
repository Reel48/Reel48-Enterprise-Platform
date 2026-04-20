"""Tests for /api/v1/platform/companies endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_platform_list_companies_requires_reel48_admin(
    client: AsyncClient, company_a_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/platform/companies/",
        headers={"Authorization": f"Bearer {company_a_admin_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_platform_list_companies_returns_all(
    client: AsyncClient, company_a, company_b, reel48_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/platform/companies/",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert resp.status_code == 200
    ids = {c["id"] for c in resp.json()["data"]}
    assert str(company_a.id) in ids
    assert str(company_b.id) in ids


@pytest.mark.asyncio
async def test_platform_create_company(
    client: AsyncClient, reel48_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/platform/companies/",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
        json={"name": "Platform-Created Corp"},
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["slug"] == "platform-created-corp"


@pytest.mark.asyncio
async def test_platform_deactivate_reactivate(
    client: AsyncClient, company_a, reel48_admin_token
) -> None:
    deact = await client.post(
        f"/api/v1/platform/companies/{company_a.id}/deactivate",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert deact.status_code == 200
    assert deact.json()["data"]["is_active"] is False

    react = await client.post(
        f"/api/v1/platform/companies/{company_a.id}/reactivate",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert react.status_code == 200
    assert react.json()["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_platform_list_company_users(
    client: AsyncClient, company_a, user_a_employee, user_a_admin, reel48_admin_token
) -> None:
    resp = await client.get(
        f"/api/v1/platform/companies/{company_a.id}/users/",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()["data"]}
    assert user_a_employee.email in emails
    assert user_a_admin.email in emails


@pytest.mark.asyncio
async def test_platform_get_org_code_returns_null_when_none(
    client: AsyncClient, company_a, reel48_admin_token
) -> None:
    resp = await client.get(
        f"/api/v1/platform/companies/{company_a.id}/org_code/",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"] is None
