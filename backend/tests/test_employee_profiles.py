"""Tests for /api/v1/profiles endpoints (Module 2)."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_upsert_my_profile_creates(
    client: AsyncClient, user_a_employee, user_a_employee_token
) -> None:
    resp = await client.put(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"department": "Ops", "shirt_size": "M"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["department"] == "Ops"
    assert data["shirt_size"] == "M"
    assert data["user_id"] == str(user_a_employee.id)


@pytest.mark.asyncio
async def test_upsert_my_profile_updates(
    client: AsyncClient, user_a_employee, user_a_employee_token
) -> None:
    await client.put(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"department": "Ops"},
    )
    resp = await client.put(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"department": "Sales"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["department"] == "Sales"


@pytest.mark.asyncio
async def test_upsert_rejects_invalid_shirt_size(
    client: AsyncClient, user_a_employee_token
) -> None:
    resp = await client.put(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"shirt_size": "XXXL"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_complete_onboarding(
    client: AsyncClient, user_a_employee, user_a_employee_token
) -> None:
    resp = await client.post(
        "/api/v1/profiles/me/complete-onboarding",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["onboarding_complete"] is True


@pytest.mark.asyncio
async def test_set_profile_photo_validates_company_scope(
    client: AsyncClient, user_a_employee, company_a, company_b, user_a_employee_token
) -> None:
    await client.put(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={},
    )

    # Valid key (own company)
    good_key = f"{company_a.id}/profiles/test.png"
    resp = await client.post(
        "/api/v1/profiles/me/photo",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"s3_key": good_key},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["profile_photo_url"] == good_key

    # Reject other company's key
    bad_key = f"{company_b.id}/profiles/test.png"
    resp = await client.post(
        "/api/v1/profiles/me/photo",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"s3_key": bad_key},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_set_profile_photo_rejects_wrong_category(
    client: AsyncClient, user_a_employee, company_a, user_a_employee_token
) -> None:
    await client.put(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={},
    )
    wrong = f"{company_a.id}/logos/test.png"
    resp = await client.post(
        "/api/v1/profiles/me/photo",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"s3_key": wrong},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_lists_profiles(
    client: AsyncClient, user_a_admin_token, user_a_employee_token, user_a_employee
) -> None:
    # Create a profile via the employee
    await client.put(
        "/api/v1/profiles/me",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={"department": "Ops"},
    )
    resp = await client.get(
        "/api/v1/profiles/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


@pytest.mark.asyncio
async def test_employee_cannot_list_profiles(
    client: AsyncClient, user_a_employee_token
) -> None:
    resp = await client.get(
        "/api/v1/profiles/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert resp.status_code == 403
