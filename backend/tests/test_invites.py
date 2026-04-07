"""Tests for the Invites CRUD endpoints."""

from uuid import uuid4

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Functional Tests
# ---------------------------------------------------------------------------


class TestCreateInvite:
    async def test_create_invite_returns_201_with_full_token(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/invites/",
            json={
                "email": "newguy@companya.com",
                "target_sub_brand_id": str(brand_a1.id),
                "role": "employee",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["email"] == "newguy@companya.com"
        assert data["role"] == "employee"
        assert len(data["token"]) == 64  # Full token on create
        assert data["expires_at"] is not None
        assert data["consumed_at"] is None

    async def test_create_duplicate_active_invite_returns_409(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        payload = {
            "email": "dup@companya.com",
            "target_sub_brand_id": str(brand_a1.id),
        }
        # First invite
        r1 = await client.post(
            "/api/v1/invites/",
            json=payload,
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert r1.status_code == 201

        # Duplicate invite for same email
        r2 = await client.post(
            "/api/v1/invites/",
            json=payload,
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert r2.status_code == 409

    async def test_create_invite_invalid_sub_brand_returns_422(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
        company_a,
    ):
        response = await client.post(
            "/api/v1/invites/",
            json={
                "email": "bad@companya.com",
                "target_sub_brand_id": str(uuid4()),  # Non-existent sub-brand
            },
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 422


class TestListInvites:
    async def test_list_invites_masks_tokens(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        # Create an invite first
        await client.post(
            "/api/v1/invites/",
            json={
                "email": "masked@companya.com",
                "target_sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )

        response = await client.get(
            "/api/v1/invites/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        for invite in response.json()["data"]:
            assert invite["token"].endswith("...")
            assert len(invite["token"]) == 11  # 8 chars + "..."


class TestDeleteInvite:
    async def test_delete_invite_returns_204(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        # Create an invite
        r1 = await client.post(
            "/api/v1/invites/",
            json={
                "email": "todelete@companya.com",
                "target_sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        invite_id = r1.json()["data"]["id"]

        # Delete it
        r2 = await client.delete(
            f"/api/v1/invites/{invite_id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert r2.status_code == 204


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestInviteAuthorization:
    async def test_employee_cannot_create_invite(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        company_a,
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.post(
            "/api/v1/invites/",
            json={
                "email": "hack@test.com",
                "target_sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_list_invites(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.get(
            "/api/v1/invites/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_sub_brand_admin_cannot_invite_to_other_sub_brand(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        _company, _a1, brand_a2 = company_a
        response = await client.post(
            "/api/v1/invites/",
            json={
                "email": "wrong-brand@test.com",
                "target_sub_brand_id": str(brand_a2.id),  # A2, not A1
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_corporate_admin_can_invite_to_any_sub_brand(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
        company_a,
    ):
        _company, _a1, brand_a2 = company_a
        response = await client.post(
            "/api/v1/invites/",
            json={
                "email": "any-brand@companya.com",
                "target_sub_brand_id": str(brand_a2.id),
            },
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestInviteIsolation:
    async def test_company_b_cannot_see_company_a_invites(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_b_corporate_admin_token: str,
        company_a,
        company_b,
    ):
        _company, brand_a1, _a2 = company_a
        # Create an invite in Company A
        await client.post(
            "/api/v1/invites/",
            json={
                "email": "isolated@companya.com",
                "target_sub_brand_id": str(brand_a1.id),
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )

        # Company B admin should see no invites
        response = await client.get(
            "/api/v1/invites/",
            headers={"Authorization": f"Bearer {company_b_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 0
