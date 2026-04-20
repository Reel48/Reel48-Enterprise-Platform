"""Tests for the /api/v1/users endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import create_test_token


@pytest.mark.asyncio
async def test_get_me_returns_current_user(
    client: AsyncClient, user_a_employee, user_a_employee_token
) -> None:
    resp = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["email"] == user_a_employee.email
    assert data["role"] == "employee"
    assert data["company_name"] == "Company A"


@pytest.mark.asyncio
async def test_list_users_forbidden_for_employee(
    client: AsyncClient, user_a_employee, user_a_employee_token
) -> None:
    resp = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_users_returns_company_users_for_admin(
    client: AsyncClient, user_a_admin, user_a_employee, user_a_admin_token
) -> None:
    resp = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    emails = {u["email"] for u in data}
    assert user_a_admin.email in emails
    assert user_a_employee.email in emails


@pytest.mark.asyncio
async def test_company_admin_creates_employee(
    client: AsyncClient, company_a, user_a_admin, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={"email": "new.emp@companya.com", "full_name": "New Emp", "role": "employee"},
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["email"] == "new.emp@companya.com"
    assert data["role"] == "employee"
    assert data["company_id"] == str(company_a.id)


@pytest.mark.asyncio
async def test_create_user_rejects_reel48_admin_role(
    client: AsyncClient, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={"email": "ad@x.com", "full_name": "Ad", "role": "reel48_admin"},
    )
    # Role is not in VALID_ROLES → ValidationError → 422
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_employee_cannot_update_others_profile(
    client: AsyncClient, user_a_employee, user_a_admin, user_a_employee_token
) -> None:
    resp = await client.patch(
        f"/api/v1/users/{user_a_admin.id}",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"full_name": "Hacked"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employee_can_update_own_name(
    client: AsyncClient, user_a_employee, user_a_employee_token
) -> None:
    resp = await client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"full_name": "Renamed"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["full_name"] == "Renamed"


@pytest.mark.asyncio
async def test_soft_delete_user(
    client: AsyncClient, user_a_employee, user_a_admin_token
) -> None:
    resp = await client.delete(
        f"/api/v1/users/{user_a_employee.id}",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_user_cannot_access_other_company_user(
    client: AsyncClient, user_b_employee, company_a
) -> None:
    token = create_test_token(company_id=str(company_a.id), role="company_admin")
    resp = await client.get(
        f"/api/v1/users/{user_b_employee.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
