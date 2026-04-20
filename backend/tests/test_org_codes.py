"""Tests for /api/v1/org_codes endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_generate_org_code(
    client: AsyncClient, user_a_admin, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/org_codes/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 201
    code = resp.json()["data"]["code"]
    assert len(code) == 8


@pytest.mark.asyncio
async def test_employee_cannot_generate_org_code(
    client: AsyncClient, user_a_employee_token
) -> None:
    resp = await client.post(
        "/api/v1/org_codes/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_generate_deactivates_previous_active_code(
    client: AsyncClient, user_a_admin_token, org_code_a
) -> None:
    r1 = await client.post(
        "/api/v1/org_codes/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert r1.status_code == 201
    current = await client.get(
        "/api/v1/org_codes/current",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert current.status_code == 200
    assert current.json()["data"]["code"] == r1.json()["data"]["code"]


@pytest.mark.asyncio
async def test_current_returns_404_when_no_active_code(
    client: AsyncClient, user_a_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/org_codes/current",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deactivate_org_code(
    client: AsyncClient, org_code_a, user_a_admin_token
) -> None:
    resp = await client.delete(
        f"/api/v1/org_codes/{org_code_a.id}",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_active"] is False
