"""Tests for the simplified analytics endpoints (user/company counts only)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_company_overview_requires_company_admin(
    client: AsyncClient, user_a_employee_token
) -> None:
    resp = await client.get(
        "/api/v1/analytics/overview",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_company_overview_returns_user_count(
    client: AsyncClient, user_a_employee, user_a_admin, user_a_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/analytics/overview",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["active_users"] >= 2


@pytest.mark.asyncio
async def test_platform_overview_cross_company(
    client: AsyncClient, company_a, company_b, user_a_employee, user_b_employee, reel48_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/platform/analytics/overview",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_companies"] >= 2
    assert data["total_users"] >= 2


@pytest.mark.asyncio
async def test_platform_overview_rejects_non_admin(
    client: AsyncClient, company_a_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/platform/analytics/overview",
        headers={"Authorization": f"Bearer {company_a_admin_token}"},
    )
    assert resp.status_code == 403
