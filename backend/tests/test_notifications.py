"""Tests for /api/v1/notifications endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_creates_company_notification(
    client: AsyncClient, user_a_admin_token
) -> None:
    resp = await client.post(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "title": "Company news",
            "body": "All-hands tomorrow.",
            "notification_type": "announcement",
            "target_scope": "company",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["title"] == "Company news"
    assert data["target_scope"] == "company"


@pytest.mark.asyncio
async def test_employee_cannot_create_notification(
    client: AsyncClient, user_a_employee_token
) -> None:
    resp = await client.post(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
        json={
            "title": "X",
            "body": "Y",
            "notification_type": "announcement",
            "target_scope": "company",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_employee_sees_company_notification(
    client: AsyncClient, user_a_admin_token, user_a_employee, user_a_employee_token
) -> None:
    await client.post(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "title": "News",
            "body": "Body",
            "notification_type": "announcement",
            "target_scope": "company",
        },
    )
    resp = await client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["meta"]["unread_count"] == 1


@pytest.mark.asyncio
async def test_individual_notification_visible_only_to_target(
    client: AsyncClient,
    user_a_admin_token,
    user_a_employee,
    user_a_employee_token,
    user_a_manager,
    user_a_manager_token,
) -> None:
    resp = await client.post(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "title": "Private",
            "body": "You only",
            "notification_type": "announcement",
            "target_scope": "individual",
            "target_user_id": str(user_a_employee.id),
        },
    )
    assert resp.status_code == 201

    r_emp = await client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert r_emp.json()["meta"]["total"] == 1

    r_mgr = await client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_manager_token}"},
    )
    assert r_mgr.json()["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_mark_as_read_flips_unread_count(
    client: AsyncClient, user_a_admin_token, user_a_employee_token
) -> None:
    create = await client.post(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "title": "X",
            "body": "Y",
            "notification_type": "announcement",
            "target_scope": "company",
        },
    )
    notification_id = create.json()["data"]["id"]
    mark = await client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert mark.status_code == 200

    feed = await client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert feed.json()["meta"]["unread_count"] == 0


@pytest.mark.asyncio
async def test_deactivate_notification_hides_it(
    client: AsyncClient, user_a_admin_token, user_a_employee_token
) -> None:
    create = await client.post(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
        json={
            "title": "X",
            "body": "Y",
            "notification_type": "announcement",
            "target_scope": "company",
        },
    )
    notification_id = create.json()["data"]["id"]
    resp = await client.delete(
        f"/api/v1/notifications/{notification_id}",
        headers={"Authorization": f"Bearer {user_a_admin_token}"},
    )
    assert resp.status_code == 200
    feed = await client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {user_a_employee_token}"},
    )
    assert feed.json()["meta"]["total"] == 0
