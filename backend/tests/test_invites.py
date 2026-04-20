"""Tests for /api/v1/invites endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_company_admin_creates_invite(
    client: AsyncClient, user_a_admin, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/invites/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={"email": "new@x.com", "role": "employee"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["email"] == "new@x.com"
    assert data["role"] == "employee"
    assert len(data["token"]) == 64


@pytest.mark.asyncio
async def test_create_invite_rejects_invalid_role(
    client: AsyncClient, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/invites/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={"email": "bogus@x.com", "role": "reel48_admin"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_employee_cannot_create_invite(
    client: AsyncClient, user_a_employee_token
) -> None:
    resp = await client.post(
        "/api/v1/invites/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"email": "foo@x.com", "role": "employee"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_invites_returns_masked_token(
    client: AsyncClient, invite_a, user_a_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/invites/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 200
    items = resp.json()["data"]
    assert len(items) == 1
    assert items[0]["token"].endswith("...")


@pytest.mark.asyncio
async def test_delete_invite(
    client: AsyncClient, invite_a, user_a_admin_token
) -> None:
    resp = await client.delete(
        f"/api/v1/invites/{invite_a.id}",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_duplicate_active_invite_conflict(
    client: AsyncClient, user_a_admin_token
) -> None:
    payload = {"email": "dup@x.com", "role": "employee"}
    r1 = await client.post(
        "/api/v1/invites/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json=payload,
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/v1/invites/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json=payload,
    )
    assert r2.status_code == 409
