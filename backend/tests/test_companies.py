"""Tests for the /api/v1/companies endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_companies_returns_own_company_for_non_admin(
    client: AsyncClient, company_a, company_a_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/companies/",
        headers={"Authorization": f"Bearer {company_a_admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == str(company_a.id)


@pytest.mark.asyncio
async def test_get_company_rejects_cross_company_access(
    client: AsyncClient, company_a, company_b, company_b_employee_token
) -> None:
    resp = await client.get(
        f"/api/v1/companies/{company_a.id}",
        headers={"Authorization": f"Bearer {company_b_employee_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reel48_admin_can_create_company(
    client: AsyncClient, reel48_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/companies/",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
        json={"name": "New Corp", "slug": "new-corp"},
    )
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["name"] == "New Corp"
    assert body["slug"] == "new-corp"
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_non_admin_cannot_create_company(
    client: AsyncClient, company_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/companies/",
        headers={"Authorization": f"Bearer {company_a_admin_token}"},
        json={"name": "Forbidden Corp"},
    )
    assert resp.status_code == 403
