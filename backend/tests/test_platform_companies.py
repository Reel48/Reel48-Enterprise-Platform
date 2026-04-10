"""Tests for Platform Admin Company endpoints.

Covers cross-company listing, filtering, detail retrieval, creation
(with default sub-brand), update, deactivation, and authorization checks
for reel48_admin-only access.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.sub_brand import SubBrand
from tests.conftest import create_test_token


BASE_URL = "/api/v1/platform/companies"


# ---------------------------------------------------------------------------
# Functional: List all companies
# ---------------------------------------------------------------------------


async def test_list_all_companies_returns_all(
    client: AsyncClient,
    admin_db_session: AsyncSession,
    company_a,
    company_b,
    reel48_admin_token: str,
):
    """reel48_admin can list companies across the platform."""
    response = await client.get(
        f"{BASE_URL}/",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] >= 2
    slugs = [c["slug"] for c in data["data"]]
    assert "company-a" in slugs
    assert "company-b" in slugs


async def test_list_companies_with_is_active_filter(
    client: AsyncClient,
    admin_db_session: AsyncSession,
    reel48_admin_token: str,
):
    """is_active filter narrows results correctly."""
    # Create one active and one inactive company
    active = Company(name="Active Co", slug=f"active-{uuid4().hex[:6]}", is_active=True)
    inactive = Company(name="Inactive Co", slug=f"inactive-{uuid4().hex[:6]}", is_active=False)
    admin_db_session.add_all([active, inactive])
    await admin_db_session.flush()

    # Filter active only
    resp_active = await client.get(
        f"{BASE_URL}/",
        params={"is_active": "true"},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert resp_active.status_code == 200
    active_slugs = [c["slug"] for c in resp_active.json()["data"]]
    assert active.slug in active_slugs
    assert inactive.slug not in active_slugs

    # Filter inactive only
    resp_inactive = await client.get(
        f"{BASE_URL}/",
        params={"is_active": "false"},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert resp_inactive.status_code == 200
    inactive_slugs = [c["slug"] for c in resp_inactive.json()["data"]]
    assert inactive.slug in inactive_slugs
    assert active.slug not in inactive_slugs


async def test_list_companies_pagination(
    client: AsyncClient,
    admin_db_session: AsyncSession,
    reel48_admin_token: str,
):
    """Pagination works correctly."""
    # Create 3 companies
    for i in range(3):
        admin_db_session.add(
            Company(name=f"Page Co {i}", slug=f"page-co-{i}-{uuid4().hex[:6]}", is_active=True)
        )
    await admin_db_session.flush()

    response = await client.get(
        f"{BASE_URL}/",
        params={"page": 1, "per_page": 2},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) <= 2
    assert data["meta"]["page"] == 1
    assert data["meta"]["per_page"] == 2
    assert data["meta"]["total"] >= 3


# ---------------------------------------------------------------------------
# Functional: Get company detail
# ---------------------------------------------------------------------------


async def test_get_company_detail(
    client: AsyncClient,
    company_a,
    reel48_admin_token: str,
):
    """reel48_admin can retrieve a single company by ID."""
    company, _a1, _a2 = company_a
    response = await client.get(
        f"{BASE_URL}/{company.id}",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(company.id)
    assert data["name"] == "Company A"
    assert data["slug"] == "company-a"
    assert data["is_active"] is True


async def test_get_company_not_found(
    client: AsyncClient,
    reel48_admin_token: str,
):
    """Getting a non-existent company returns 404."""
    response = await client.get(
        f"{BASE_URL}/{uuid4()}",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Functional: Create company (with default sub-brand)
# ---------------------------------------------------------------------------


async def test_create_company_with_default_sub_brand(
    client: AsyncClient,
    admin_db_session: AsyncSession,
    reel48_admin_token: str,
):
    """Creating a company atomically creates the default sub-brand (ADR-003)."""
    slug = f"new-co-{uuid4().hex[:6]}"
    response = await client.post(
        f"{BASE_URL}/",
        json={"name": "New Company", "slug": slug},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "New Company"
    assert data["slug"] == slug
    assert data["is_active"] is True

    # Verify default sub-brand was created
    from sqlalchemy import select

    result = await admin_db_session.execute(
        select(SubBrand).where(
            SubBrand.company_id == data["id"],
            SubBrand.is_default == True,  # noqa: E712
        )
    )
    default_brand = result.scalar_one_or_none()
    assert default_brand is not None
    assert default_brand.slug == "default"


async def test_create_company_duplicate_slug_returns_409(
    client: AsyncClient,
    company_a,
    reel48_admin_token: str,
):
    """Duplicate slug returns 409 Conflict."""
    response = await client.post(
        f"{BASE_URL}/",
        json={"name": "Duplicate", "slug": "company-a"},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Functional: Update company
# ---------------------------------------------------------------------------


async def test_update_company_name(
    client: AsyncClient,
    company_a,
    reel48_admin_token: str,
):
    """reel48_admin can update a company's name."""
    company, _a1, _a2 = company_a
    response = await client.patch(
        f"{BASE_URL}/{company.id}",
        json={"name": "Company A Renamed"},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Company A Renamed"


async def test_update_company_slug_duplicate_returns_409(
    client: AsyncClient,
    company_a,
    company_b,
    reel48_admin_token: str,
):
    """Updating to a slug that already exists returns 409."""
    company_a_obj, _a1, _a2 = company_a
    response = await client.patch(
        f"{BASE_URL}/{company_a_obj.id}",
        json={"slug": "company-b"},
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Functional: Deactivate company
# ---------------------------------------------------------------------------


async def test_deactivate_company(
    client: AsyncClient,
    admin_db_session: AsyncSession,
    reel48_admin_token: str,
):
    """reel48_admin can deactivate a company (soft-delete via is_active=false)."""
    company = Company(
        name="To Deactivate", slug=f"deact-{uuid4().hex[:6]}", is_active=True
    )
    admin_db_session.add(company)
    await admin_db_session.flush()

    response = await client.post(
        f"{BASE_URL}/{company.id}/deactivate",
        headers={"Authorization": f"Bearer {reel48_admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is False


# ---------------------------------------------------------------------------
# Authorization: Only reel48_admin can access platform company endpoints
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "token_fixture",
    [
        "company_a_corporate_admin_token",
        "company_a_brand_a1_admin_token",
        "company_a_brand_a1_employee_token",
    ],
)
async def test_non_reel48_admin_cannot_list_companies(
    client: AsyncClient,
    company_a,
    token_fixture: str,
    request: pytest.FixtureRequest,
):
    """Non-reel48_admin roles get 403 on platform company endpoints."""
    token = request.getfixturevalue(token_fixture)
    response = await client.get(
        f"{BASE_URL}/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


async def test_corporate_admin_cannot_create_company(
    client: AsyncClient,
    company_a,
    company_a_corporate_admin_token: str,
):
    """Corporate admin cannot create companies — platform-only operation."""
    response = await client.post(
        f"{BASE_URL}/",
        json={"name": "Unauthorized", "slug": "unauthorized-co"},
        headers={"Authorization": f"Bearer {company_a_corporate_admin_token}"},
    )
    assert response.status_code == 403


async def test_employee_cannot_deactivate_company(
    client: AsyncClient,
    company_a,
    company_a_brand_a1_employee_token: str,
):
    """Employee cannot deactivate companies — platform-only operation."""
    company, _a1, _a2 = company_a
    response = await client.post(
        f"{BASE_URL}/{company.id}/deactivate",
        headers={"Authorization": f"Bearer {company_a_brand_a1_employee_token}"},
    )
    assert response.status_code == 403


async def test_unauthenticated_request_returns_401(client: AsyncClient):
    """Requests without a token are rejected."""
    response = await client.get(f"{BASE_URL}/")
    assert response.status_code == 401
