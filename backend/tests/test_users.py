"""Tests for the Users CRUD endpoints."""

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Functional Tests
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    async def test_get_me_returns_own_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == user_a1_employee.email
        assert data["full_name"] == user_a1_employee.full_name
        assert "cognito_sub" not in data
        assert "deleted_at" not in data


class TestCreateUser:
    async def test_create_user_returns_201(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "newuser@companya.com",
                "full_name": "New User",
                "role": "employee",
                "sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["email"] == "newuser@companya.com"
        assert data["role"] == "employee"

    async def test_create_user_duplicate_email_returns_409(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": user_a1_employee.email,
                "full_name": "Duplicate",
                "role": "employee",
                "sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 409

    async def test_create_user_invalid_role_returns_422(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "bad@role.com",
                "full_name": "Bad Role",
                "role": "superuser",
                "sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 422


class TestListUsers:
    async def test_admin_can_list_users(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee,
        company_a,
    ):
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] >= 1


class TestGetUser:
    async def test_admin_can_get_user_in_scope(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee,
    ):
        response = await client.get(
            f"/api/v1/users/{user_a1_employee.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["email"] == user_a1_employee.email


class TestUpdateUser:
    async def test_admin_can_update_user(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee,
    ):
        response = await client.patch(
            f"/api/v1/users/{user_a1_employee.id}",
            json={"full_name": "Updated Name"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["full_name"] == "Updated Name"

    async def test_employee_can_update_own_full_name(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.patch(
            f"/api/v1/users/{user_a1_employee.id}",
            json={"full_name": "My New Name"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["full_name"] == "My New Name"

    async def test_employee_cannot_update_own_role(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.patch(
            f"/api/v1/users/{user_a1_employee.id}",
            json={"role": "corporate_admin"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403


class TestDeleteUser:
    async def test_soft_delete_user(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        user_a1_employee,
    ):
        response = await client.delete(
            f"/api/v1/users/{user_a1_employee.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(user_a1_employee.id)

        # Verify user is excluded from list
        list_response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        user_ids = [u["id"] for u in list_response.json()["data"]]
        assert str(user_a1_employee.id) not in user_ids


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestUserAuthorization:
    async def test_employee_cannot_list_users(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_create_user(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "hack@test.com",
                "full_name": "Hack",
                "role": "employee",
                "sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_delete_user(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a1_admin,
    ):
        response = await client.delete(
            f"/api/v1/users/{user_a1_admin.id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_sub_brand_admin_cannot_assign_corporate_admin_role(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/users/",
            json={
                "email": "promoted@test.com",
                "full_name": "Promoted",
                "role": "corporate_admin",
                "sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_view_other_users_profile(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a1_admin,
    ):
        response = await client.get(
            f"/api/v1/users/{user_a1_admin.id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestUserIsolation:
    async def test_company_b_cannot_see_company_a_users(
        self,
        client: AsyncClient,
        company_b_corporate_admin_token: str,
        company_b,
        user_a1_employee,
        company_a,
    ):
        response = await client.get(
            f"/api/v1/users/{user_a1_employee.id}",
            headers={"Authorization": f"Bearer {company_b_corporate_admin_token}"},
        )
        # Should be 404 — user not found in Company B's scope
        assert response.status_code == 404

    async def test_brand_a2_admin_cannot_see_brand_a1_users(
        self,
        client: AsyncClient,
        company_a_brand_a2_admin_token: str,
        user_a1_employee,
        company_a,
    ):
        response = await client.get(
            f"/api/v1/users/{user_a1_employee.id}",
            headers={"Authorization": f"Bearer {company_a_brand_a2_admin_token}"},
        )
        # Brand A2 admin cannot access Brand A1 user
        assert response.status_code == 403

    async def test_corporate_admin_sees_all_sub_brand_users(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
        user_a1_employee,
        company_a,
    ):
        response = await client.get(
            "/api/v1/users/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        # Should see users across sub-brands (at least the employee + admin + corporate admin)
        assert response.json()["meta"]["total"] >= 2
