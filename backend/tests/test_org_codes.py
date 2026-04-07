"""Tests for the Org Codes CRUD endpoints."""

from httpx import AsyncClient

from app.services.org_code_service import ALPHABET

# ---------------------------------------------------------------------------
# Functional Tests
# ---------------------------------------------------------------------------


class TestGenerateOrgCode:
    async def test_generate_org_code_returns_201(
        self, client: AsyncClient, user_a_corporate_admin_token: str, user_a_corporate_admin
    ):
        response = await client.post(
            "/api/v1/org_codes/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["code"]) == 8
        assert all(c in ALPHABET for c in data["code"])
        assert data["is_active"] is True

    async def test_generate_new_code_deactivates_previous(
        self, client: AsyncClient, user_a_corporate_admin_token: str, user_a_corporate_admin
    ):
        # Generate first code
        r1 = await client.post(
            "/api/v1/org_codes/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        first_code = r1.json()["data"]["code"]

        # Generate second code
        r2 = await client.post(
            "/api/v1/org_codes/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        second_code = r2.json()["data"]["code"]

        assert first_code != second_code

        # Current should be the second code
        r3 = await client.get(
            "/api/v1/org_codes/current",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert r3.json()["data"]["code"] == second_code


class TestGetCurrentOrgCode:
    async def test_get_current_when_none_exists_returns_404(
        self, client: AsyncClient, user_a_corporate_admin_token: str, user_a_corporate_admin
    ):
        response = await client.get(
            "/api/v1/org_codes/current",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 404


class TestDeactivateOrgCode:
    async def test_deactivate_org_code(
        self, client: AsyncClient, user_a_corporate_admin_token: str, user_a_corporate_admin
    ):
        # Generate a code first
        r1 = await client.post(
            "/api/v1/org_codes/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        org_code_id = r1.json()["data"]["id"]

        # Deactivate it
        r2 = await client.delete(
            f"/api/v1/org_codes/{org_code_id}",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert r2.status_code == 200
        assert r2.json()["data"]["is_active"] is False

        # Current should now be 404
        r3 = await client.get(
            "/api/v1/org_codes/current",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert r3.status_code == 404


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestOrgCodeAuthorization:
    async def test_employee_cannot_generate_org_code(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        response = await client.post(
            "/api/v1/org_codes/",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_sub_brand_admin_cannot_generate_org_code(
        self, client: AsyncClient, company_a_brand_a1_admin_token: str, company_a
    ):
        response = await client.post(
            "/api/v1/org_codes/",
            headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_view_current_org_code(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        response = await client.get(
            "/api/v1/org_codes/current",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestOrgCodeIsolation:
    async def test_company_b_cannot_see_company_a_org_codes(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
        company_b_corporate_admin_token: str,
        company_b,
    ):
        # Generate a code for Company A
        await client.post(
            "/api/v1/org_codes/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )

        # Company B should see no current code
        response = await client.get(
            "/api/v1/org_codes/current",
            headers={"Authorization": f"Bearer {company_b_corporate_admin_token}"},
        )
        assert response.status_code == 404
