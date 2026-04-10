"""Tests for Module 9 Phase 2: Notification Service & API Endpoints.

Covers:
- Functional tests (CRUD, feed filtering, mark-as-read, pagination)
- Isolation tests (cross-company, cross-sub-brand)
- Authorization tests (role-based access control)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.models.user import User
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_notification(
    db: AsyncSession,
    company_id,
    sub_brand_id=None,
    title="Test Notification",
    body="Test body",
    notification_type="announcement",
    target_scope="sub_brand",
    target_user_id=None,
    created_by=None,
    is_active=True,
    expires_at=None,
    read_by=None,
) -> Notification:
    """Helper to insert a notification directly in the database."""
    n = Notification(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        title=title,
        body=body,
        notification_type=notification_type,
        target_scope=target_scope,
        target_user_id=target_user_id,
        created_by=created_by or uuid4(),
        is_active=is_active,
        expires_at=expires_at,
    )
    if read_by is not None:
        n.read_by = read_by  # type: ignore[assignment]
    db.add(n)
    await db.flush()
    await db.refresh(n)
    return n


# ===========================================================================
# FUNCTIONAL TESTS
# ===========================================================================


class TestCreateNotification:
    """Tests for POST /api/v1/notifications/"""

    async def test_create_company_scope_as_corporate_admin(
        self,
        client: AsyncClient,
        company_a,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Company-wide announcement",
                "body": "Hello everyone!",
                "notification_type": "announcement",
                "target_scope": "company",
            },
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["title"] == "Company-wide announcement"
        assert data["target_scope"] == "company"
        assert data["sub_brand_id"] is None  # company-scope has no sub_brand_id

    async def test_create_sub_brand_scope_as_sub_brand_admin(
        self,
        client: AsyncClient,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Brand A1 announcement",
                "body": "For brand A1 only",
                "notification_type": "announcement",
                "target_scope": "sub_brand",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["target_scope"] == "sub_brand"
        assert data["sub_brand_id"] is not None

    async def test_create_individual_notification(
        self,
        client: AsyncClient,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
        user_a1_employee,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Personal notification",
                "body": "Just for you",
                "notification_type": "order_update",
                "target_scope": "individual",
                "target_user_id": str(user_a1_employee.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["target_scope"] == "individual"
        assert data["target_user_id"] == str(user_a1_employee.id)

    async def test_create_individual_without_target_user_returns_400(
        self,
        client: AsyncClient,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Missing target",
                "body": "No target user",
                "notification_type": "announcement",
                "target_scope": "individual",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 422

    async def test_create_with_invalid_notification_type_returns_422(
        self,
        client: AsyncClient,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Bad type",
                "body": "Invalid",
                "notification_type": "invalid_type",
                "target_scope": "sub_brand",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 422


class TestListNotificationsFeed:
    """Tests for GET /api/v1/notifications/"""

    async def test_employee_sees_company_scope_notification(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=None,
            title="Company-wide",
            target_scope="company",
            created_by=user_a1_employee.id,
        )

        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        titles = [n["title"] for n in data["data"]]
        assert "Company-wide" in titles

    async def test_employee_sees_sub_brand_scope_notification(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Brand A1 news",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Brand A1 news" in titles

    async def test_employee_sees_individual_notification(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Just for you",
            target_scope="individual",
            target_user_id=user_a1_employee.id,
            created_by=user_a1_employee.id,
        )

        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Just for you" in titles

    async def test_expired_notifications_not_in_feed(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Expired notification",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )

        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Expired notification" not in titles

    async def test_deactivated_notifications_not_in_feed(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Deactivated notification",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
            is_active=False,
        )

        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Deactivated notification" not in titles

    async def test_unread_only_filter(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        user_id_str = str(user_a1_employee.id)

        # Create one read and one unread
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Already read",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
            read_by=[user_id_str],
        )
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Still unread",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        response = await client.get(
            "/api/v1/notifications/?unread_only=true",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Still unread" in titles
        assert "Already read" not in titles

    async def test_unread_count_in_meta(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        user_id_str = str(user_a1_employee.id)

        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Read one",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
            read_by=[user_id_str],
        )
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Unread one",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Unread two",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        meta = response.json()["meta"]
        # unread_count should be at least 2 (other tests may add notifications)
        assert meta["unread_count"] >= 2

    async def test_pagination(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        for i in range(5):
            await _create_notification(
                admin_db_session,
                company_id=company.id,
                sub_brand_id=brand_a1.id,
                title=f"Paginated {i}",
                target_scope="sub_brand",
                created_by=user_a1_employee.id,
            )

        response = await client.get(
            "/api/v1/notifications/?page=1&per_page=2",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["meta"]["per_page"] == 2
        assert data["meta"]["total"] >= 5


class TestMarkAsRead:
    """Tests for POST /api/v1/notifications/{id}/read"""

    async def test_mark_as_read(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        n = await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="To be read",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        response = await client.post(
            f"/api/v1/notifications/{n.id}/read",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["is_read"] is True
        assert str(user_a1_employee.id) in data["read_by"]

    async def test_mark_as_read_idempotent(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        n = await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Read twice",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        # Mark twice
        await client.post(
            f"/api/v1/notifications/{n.id}/read",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        response = await client.post(
            f"/api/v1/notifications/{n.id}/read",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        # user_id should appear only once in read_by
        read_by = response.json()["data"]["read_by"]
        assert read_by.count(str(user_a1_employee.id)) == 1

    async def test_mark_nonexistent_returns_404(
        self,
        client: AsyncClient,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        response = await client.post(
            f"/api/v1/notifications/{uuid4()}/read",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404


class TestMarkAllAsRead:
    """Tests for POST /api/v1/notifications/read-all"""

    async def test_mark_all_as_read(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        for i in range(3):
            await _create_notification(
                admin_db_session,
                company_id=company.id,
                sub_brand_id=brand_a1.id,
                title=f"Bulk read {i}",
                target_scope="sub_brand",
                created_by=user_a1_employee.id,
            )

        response = await client.post(
            "/api/v1/notifications/read-all",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["marked_count"] >= 3


class TestAdminListNotifications:
    """Tests for GET /api/v1/notifications/admin/"""

    async def test_admin_sees_all_including_expired_and_inactive(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        company, brand_a1, _a2 = company_a
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Active notification",
            target_scope="sub_brand",
            created_by=user_a1_admin.id,
        )
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Expired admin view",
            target_scope="sub_brand",
            created_by=user_a1_admin.id,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Inactive admin view",
            target_scope="sub_brand",
            created_by=user_a1_admin.id,
            is_active=False,
        )

        response = await client.get(
            "/api/v1/notifications/admin/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Active notification" in titles
        assert "Expired admin view" in titles
        assert "Inactive admin view" in titles

    async def test_admin_filter_by_notification_type(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        company, brand_a1, _a2 = company_a
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Announcement",
            notification_type="announcement",
            target_scope="sub_brand",
            created_by=user_a1_admin.id,
        )
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Order update",
            notification_type="order_update",
            target_scope="sub_brand",
            created_by=user_a1_admin.id,
        )

        response = await client.get(
            "/api/v1/notifications/admin/?notification_type=announcement",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        for n in data:
            assert n["notification_type"] == "announcement"


class TestDeactivateNotification:
    """Tests for DELETE /api/v1/notifications/{id}"""

    async def test_deactivate_notification(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        company, brand_a1, _a2 = company_a
        n = await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="To deactivate",
            target_scope="sub_brand",
            created_by=user_a1_admin.id,
        )

        response = await client.delete(
            f"/api/v1/notifications/{n.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["is_active"] is False


# ===========================================================================
# ISOLATION TESTS
# ===========================================================================


class TestIsolation:
    """Cross-company and cross-sub-brand isolation tests."""

    async def test_company_b_cannot_see_company_a_notifications(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
        user_a1_employee,
        user_b1_employee,
    ):
        """Company B employee cannot see Company A's notifications."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        await _create_notification(
            admin_db_session,
            company_id=company_a_obj.id,
            sub_brand_id=None,
            title="Company A only",
            target_scope="company",
            created_by=user_a1_employee.id,
        )

        # Query as Company B employee
        token_b = create_test_token(
            user_id=user_b1_employee.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="employee",
        )
        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Company A only" not in titles

    async def test_sub_brand_a2_cannot_see_a1_sub_brand_notifications(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
    ):
        """Brand A2 employee cannot see Brand A1's sub-brand-scope notifications."""
        company, brand_a1, brand_a2 = company_a

        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Brand A1 only",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        # Create a Brand A2 employee user + token
        user_a2 = User(
            company_id=company.id,
            sub_brand_id=brand_a2.id,
            cognito_sub=str(uuid4()),
            email=f"emp-a2-{uuid4().hex[:6]}@companya.com",
            full_name="Employee A2",
            role="employee",
        )
        admin_db_session.add(user_a2)
        await admin_db_session.flush()

        token_a2 = create_test_token(
            user_id=user_a2.cognito_sub,
            company_id=str(company.id),
            sub_brand_id=str(brand_a2.id),
            role="employee",
        )

        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {token_a2}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Brand A1 only" not in titles

    async def test_corporate_admin_sees_all_sub_brand_notifications(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
        user_a1_employee,
    ):
        """Corporate admin sees notifications from all sub-brands in their company."""
        company, brand_a1, brand_a2 = company_a

        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Brand A1 corp-vis",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )
        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a2.id,
            title="Brand A2 corp-vis",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        # Admin list should show both
        response = await client.get(
            "/api/v1/notifications/admin/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Brand A1 corp-vis" in titles
        assert "Brand A2 corp-vis" in titles

    async def test_individual_notification_only_visible_to_target_user(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        """An individual notification is only visible to its target user."""
        company, brand_a1, _a2 = company_a

        # Create another employee in the same sub-brand
        other_user = User(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            cognito_sub=str(uuid4()),
            email=f"other-a1-{uuid4().hex[:6]}@companya.com",
            full_name="Other Employee A1",
            role="employee",
        )
        admin_db_session.add(other_user)
        await admin_db_session.flush()

        await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Individual for other",
            target_scope="individual",
            target_user_id=other_user.id,
            created_by=user_a1_employee.id,
        )

        # user_a1_employee should NOT see the notification targeted at other_user
        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        titles = [n["title"] for n in response.json()["data"]]
        assert "Individual for other" not in titles


# ===========================================================================
# AUTHORIZATION TESTS
# ===========================================================================


class TestAuthorization:
    """Role-based access control tests."""

    async def test_employee_cannot_create_notification(
        self,
        client: AsyncClient,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Employee attempt",
                "body": "Should fail",
                "notification_type": "announcement",
                "target_scope": "sub_brand",
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_regional_manager_cannot_create_notification(
        self,
        client: AsyncClient,
        company_a,
        user_a1_manager,
        user_a1_manager_token,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Manager attempt",
                "body": "Should fail",
                "notification_type": "announcement",
                "target_scope": "sub_brand",
            },
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403

    async def test_sub_brand_admin_cannot_create_company_scope(
        self,
        client: AsyncClient,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        response = await client.post(
            "/api/v1/notifications/",
            json={
                "title": "Company scope attempt",
                "body": "Should fail",
                "notification_type": "announcement",
                "target_scope": "company",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_access_admin_list(
        self,
        client: AsyncClient,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        response = await client.get(
            "/api/v1/notifications/admin/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_regional_manager_cannot_access_admin_list(
        self,
        client: AsyncClient,
        company_a,
        user_a1_manager,
        user_a1_manager_token,
    ):
        response = await client.get(
            "/api/v1/notifications/admin/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_deactivate_notification(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        n = await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Cannot deactivate",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        response = await client.delete(
            f"/api/v1/notifications/{n.id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.get("/api/v1/notifications/")
        assert response.status_code in (401, 403)

    async def test_employee_can_read_notifications(
        self,
        client: AsyncClient,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        """Employees can view the notification feed."""
        response = await client.get(
            "/api/v1/notifications/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200

    async def test_employee_can_mark_as_read(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        """Employees can mark notifications as read."""
        company, brand_a1, _a2 = company_a
        n = await _create_notification(
            admin_db_session,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            title="Employee reads",
            target_scope="sub_brand",
            created_by=user_a1_employee.id,
        )

        response = await client.post(
            f"/api/v1/notifications/{n.id}/read",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
