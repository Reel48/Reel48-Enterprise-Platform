"""Tests for the Sub-Brands CRUD endpoints."""

from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Functional Tests
# ---------------------------------------------------------------------------


class TestCreateSubBrand:
    async def test_create_sub_brand(
        self, client: AsyncClient, company_a_corporate_admin_token: str, company_a
    ):
        response = await client.post(
            "/api/v1/sub_brands/",
            json={"name": "Brand A3", "slug": "brand-a3"},
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "Brand A3"
        assert data["slug"] == "brand-a3"
        assert data["is_default"] is False

    async def test_create_duplicate_slug_returns_409(
        self, client: AsyncClient, company_a_corporate_admin_token: str, company_a
    ):
        response = await client.post(
            "/api/v1/sub_brands/",
            json={"name": "Dup", "slug": "brand-a1"},
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 409


class TestListSubBrands:
    async def test_corporate_admin_sees_all_sub_brands(
        self, client: AsyncClient, company_a_corporate_admin_token: str, company_a
    ):
        response = await client.get(
            "/api/v1/sub_brands/",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 2  # Brand A1, Brand A2

    async def test_employee_sees_only_own_sub_brand(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        response = await client.get(
            "/api/v1/sub_brands/",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 1
        assert data["data"][0]["slug"] == "brand-a1"


class TestGetSubBrand:
    async def test_get_sub_brand(
        self, client: AsyncClient, company_a_corporate_admin_token: str, company_a
    ):
        _company, brand_a1, _a2 = company_a
        response = await client.get(
            f"/api/v1/sub_brands/{brand_a1.id}",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["slug"] == "brand-a1"


class TestUpdateSubBrand:
    async def test_update_sub_brand_name(
        self, client: AsyncClient, company_a_corporate_admin_token: str, company_a
    ):
        _company, _a1, brand_a2 = company_a
        response = await client.patch(
            f"/api/v1/sub_brands/{brand_a2.id}",
            json={"name": "Updated A2"},
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated A2"


class TestDeactivateSubBrand:
    async def test_deactivate_non_default_sub_brand(
        self, client: AsyncClient, company_a_corporate_admin_token: str, company_a
    ):
        _company, _a1, brand_a2 = company_a
        response = await client.delete(
            f"/api/v1/sub_brands/{brand_a2.id}",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False

    async def test_cannot_deactivate_default_sub_brand(
        self, client: AsyncClient, company_a_corporate_admin_token: str, company_a
    ):
        _company, brand_a1, _a2 = company_a  # brand_a1 is default
        response = await client.delete(
            f"/api/v1/sub_brands/{brand_a1.id}",
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 409
        assert "default" in response.json()["errors"][0]["message"].lower()

    async def test_cannot_deactivate_last_active_sub_brand(
        self, client: AsyncClient, company_b_corporate_admin_token: str, company_b
    ):
        # Company B has only one sub-brand (B1 default) — cannot deactivate
        _company, brand_b1 = company_b
        response = await client.delete(
            f"/api/v1/sub_brands/{brand_b1.id}",
            headers={"Authorization": f"Bearer {company_b_corporate_admin_token}"},
        )
        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestSubBrandAuthorization:
    async def test_employee_cannot_create_sub_brand(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        response = await client.post(
            "/api/v1/sub_brands/",
            json={"name": "Hack", "slug": "hack"},
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_sub_brand_admin_cannot_create_sub_brand(
        self, client: AsyncClient, company_a_brand_a1_admin_token: str, company_a
    ):
        response = await client.post(
            "/api/v1/sub_brands/",
            json={"name": "Hack", "slug": "hack"},
            headers={"Authorization": f"Bearer {company_a_brand_a1_admin_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestSubBrandIsolation:
    async def test_company_b_cannot_see_company_a_sub_brands(
        self, client: AsyncClient, company_b_corporate_admin_token: str, company_a, company_b
    ):
        response = await client.get(
            "/api/v1/sub_brands/",
            headers={"Authorization": f"Bearer {company_b_corporate_admin_token}"},
        )
        assert response.status_code == 200
        slugs = [sb["slug"] for sb in response.json()["data"]]
        assert "brand-a1" not in slugs
        assert "brand-a2" not in slugs

    async def test_brand_a2_employee_sees_only_brand_a2(
        self, client: AsyncClient, company_a_brand_a2_employee_token: str, company_a
    ):
        response = await client.get(
            "/api/v1/sub_brands/",
            headers={"Authorization": f"Bearer {company_a_brand_a2_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 1
        assert data["data"][0]["slug"] == "brand-a2"

    async def test_employee_cannot_get_other_sub_brand(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        _company, _a1, brand_a2 = company_a
        response = await client.get(
            f"/api/v1/sub_brands/{brand_a2.id}",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403
