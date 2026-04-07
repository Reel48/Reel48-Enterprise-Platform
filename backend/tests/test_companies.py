"""Tests for the Companies CRUD endpoints."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sub_brand import SubBrand

# ---------------------------------------------------------------------------
# Functional Tests
# ---------------------------------------------------------------------------


class TestCreateCompany:
    async def test_create_company_returns_201_with_default_sub_brand(
        self, client: AsyncClient, reel48_admin_token: str, admin_db_session: AsyncSession
    ):
        response = await client.post(
            "/api/v1/companies/",
            json={"name": "New Corp", "slug": "new-corp"},
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "New Corp"
        assert data["slug"] == "new-corp"
        assert data["is_active"] is True
        assert "stripe_customer_id" not in data

        # Verify default sub-brand was created atomically
        result = await admin_db_session.execute(
            select(SubBrand).where(SubBrand.company_id == data["id"], SubBrand.is_default == True)  # noqa: E712
        )
        default_sb = result.scalar_one_or_none()
        assert default_sb is not None
        assert default_sb.slug == "default"
        assert default_sb.name == "New Corp - Default"

    async def test_create_company_duplicate_slug_returns_409(
        self, client: AsyncClient, reel48_admin_token: str, company_a
    ):
        response = await client.post(
            "/api/v1/companies/",
            json={"name": "Duplicate", "slug": "company-a"},
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["errors"][0]["message"]


class TestGetCompany:
    async def test_get_company_as_reel48_admin(
        self, client: AsyncClient, reel48_admin_token: str, company_a
    ):
        company, _a1, _a2 = company_a
        response = await client.get(
            f"/api/v1/companies/{company.id}",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(company.id)

    async def test_get_own_company_as_employee(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        company, _a1, _a2 = company_a
        response = await client.get(
            f"/api/v1/companies/{company.id}",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 200


class TestListCompanies:
    async def test_reel48_admin_sees_all_companies(
        self, client: AsyncClient, reel48_admin_token: str, company_a, company_b
    ):
        response = await client.get(
            "/api/v1/companies/",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] >= 2

    async def test_employee_sees_only_own_company(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a, company_b
    ):
        response = await client.get(
            "/api/v1/companies/",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] == 1
        assert data["data"][0]["slug"] == "company-a"


class TestUpdateCompany:
    async def test_update_company_name(
        self, client: AsyncClient, reel48_admin_token: str, company_a
    ):
        company, _a1, _a2 = company_a
        response = await client.patch(
            f"/api/v1/companies/{company.id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Name"

    async def test_update_company_duplicate_slug_returns_409(
        self, client: AsyncClient, reel48_admin_token: str, company_a, company_b
    ):
        company, _a1, _a2 = company_a
        response = await client.patch(
            f"/api/v1/companies/{company.id}",
            json={"slug": "company-b"},
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 409


class TestDeactivateCompany:
    async def test_deactivate_company(
        self, client: AsyncClient, reel48_admin_token: str, company_a
    ):
        company, _a1, _a2 = company_a
        response = await client.delete(
            f"/api/v1/companies/{company.id}",
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is False


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestCompanyAuthorization:
    async def test_employee_cannot_create_company(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str
    ):
        response = await client.post(
            "/api/v1/companies/",
            json={"name": "Hack", "slug": "hack"},
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_corporate_admin_cannot_create_company(
        self, client: AsyncClient, company_a_corporate_admin_token: str
    ):
        response = await client.post(
            "/api/v1/companies/",
            json={"name": "Hack", "slug": "hack"},
            headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_update_company(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        company, _a1, _a2 = company_a
        response = await client.patch(
            f"/api/v1/companies/{company.id}",
            json={"name": "Hacked"},
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_delete_company(
        self, client: AsyncClient, company_a_brand_a1_employee_token: str, company_a
    ):
        company, _a1, _a2 = company_a
        response = await client.delete(
            f"/api/v1/companies/{company.id}",
            headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestCompanyIsolation:
    async def test_company_b_cannot_read_company_a(
        self, client: AsyncClient, company_b_employee_token: str, company_a
    ):
        company, _a1, _a2 = company_a
        response = await client.get(
            f"/api/v1/companies/{company.id}",
            headers={"Authorization": f"Bearer {company_b_employee_token}"},
        )
        assert response.status_code == 403

    async def test_company_b_list_excludes_company_a(
        self, client: AsyncClient, company_b_employee_token: str, company_a, company_b
    ):
        response = await client.get(
            "/api/v1/companies/",
            headers={"Authorization": f"Bearer {company_b_employee_token}"},
        )
        assert response.status_code == 200
        slugs = [c["slug"] for c in response.json()["data"]]
        assert "company-a" not in slugs
        assert "company-b" in slugs
