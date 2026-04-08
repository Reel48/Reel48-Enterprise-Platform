"""Tests for Platform Admin endpoints (Module 3 Phase 4).

Covers product and catalog approval workflows, cross-company listing,
and authorization checks for reel48_admin-only access.
"""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.product import Product
from app.models.user import User
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_product(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    *,
    sku: str | None = None,
    status: str = "draft",
    name: str = "Test Product",
    unit_price: float = 29.99,
) -> Product:
    """Insert a product directly for test setup."""
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=name,
        description="A test product",
        sku=sku or f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=unit_price,
        sizes=["S", "M", "L"],
        decoration_options=["screen_print"],
        image_urls=[],
        created_by=created_by,
    )
    if status != "draft":
        product.status = status  # type: ignore[assignment]
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def _create_catalog(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    *,
    name: str = "Test Catalog",
    status: str = "draft",
    payment_model: str = "self_service",
    slug: str | None = None,
) -> Catalog:
    """Insert a catalog directly for test setup."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=name,
        description="A test catalog",
        slug=slug or f"catalog-{uuid4().hex[:8]}",
        payment_model=payment_model,
        created_by=created_by,
    )
    if status != "draft":
        catalog.status = status  # type: ignore[assignment]
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _create_user(
    db: AsyncSession, company_id, sub_brand_id, role: str = "sub_brand_admin"
) -> User:
    user = User(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        cognito_sub=str(uuid4()),
        email=f"{role}-{uuid4().hex[:6]}@test.com",
        full_name=f"Test {role}",
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def _add_product_to_catalog(
    db: AsyncSession, catalog: Catalog, product: Product
) -> CatalogProduct:
    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=catalog.company_id,
        sub_brand_id=catalog.sub_brand_id,
        display_order=0,
    )
    db.add(cp)
    await db.flush()
    return cp


# ---------------------------------------------------------------------------
# Platform Products Tests
# ---------------------------------------------------------------------------


class TestPlatformProducts:
    async def test_list_all_products_as_reel48_admin(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
    ):
        """reel48_admin sees products from both companies."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b
        user_a = await _create_user(admin_db_session, company_a_obj.id, brand_a1.id)
        user_b = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)
        await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id, name="A Product"
        )
        await _create_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id, name="B Product"
        )

        response = await client.get(
            "/api/v1/platform/products/",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] >= 2
        company_ids = {p["company_id"] for p in data["data"]}
        assert str(company_a_obj.id) in company_ids
        assert str(company_b_obj.id) in company_ids

    async def test_list_products_filtered_by_status(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="submitted"
        )
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="draft"
        )

        response = await client.get(
            "/api/v1/platform/products/?status=submitted",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        for p in response.json()["data"]:
            assert p["status"] == "submitted"

    async def test_list_products_filtered_by_company_id(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
    ):
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b
        user_a = await _create_user(admin_db_session, company_a_obj.id, brand_a1.id)
        user_b = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)
        await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id
        )
        await _create_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id
        )

        response = await client.get(
            f"/api/v1/platform/products/?company_id={company_a_obj.id}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        for p in response.json()["data"]:
            assert p["company_id"] == str(company_a_obj.id)

    async def test_approve_submitted_product(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="submitted"
        )

        response = await client.post(
            f"/api/v1/platform/products/{product.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "approved"
        assert data["approved_by"] == str(reel48_admin_user.id)
        assert data["approved_at"] is not None

    async def test_approve_non_submitted_product_returns_error(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="draft"
        )

        response = await client.post(
            f"/api/v1/platform/products/{product.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 403

    async def test_reject_submitted_product(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="submitted"
        )

        response = await client.post(
            f"/api/v1/platform/products/{product.id}/reject",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "draft"
        assert data["approved_by"] is None
        assert data["approved_at"] is None

    async def test_activate_approved_product(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="approved"
        )

        response = await client.post(
            f"/api/v1/platform/products/{product.id}/activate",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"

    async def test_activate_non_approved_product_returns_error(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="submitted"
        )

        response = await client.post(
            f"/api/v1/platform/products/{product.id}/activate",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 403

    async def test_non_reel48_admin_cannot_access_platform_products(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
    ):
        """corporate_admin gets 403 on platform endpoints."""
        response = await client.get(
            "/api/v1/platform/products/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Platform Catalogs Tests
# ---------------------------------------------------------------------------


class TestPlatformCatalogs:
    async def test_list_all_catalogs_as_reel48_admin(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
    ):
        """reel48_admin sees catalogs from both companies."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b
        user_a = await _create_user(admin_db_session, company_a_obj.id, brand_a1.id)
        user_b = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)
        await _create_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id, name="Catalog A"
        )
        await _create_catalog(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id, name="Catalog B"
        )

        response = await client.get(
            "/api/v1/platform/catalogs/",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] >= 2
        company_ids = {c["company_id"] for c in data["data"]}
        assert str(company_a_obj.id) in company_ids
        assert str(company_b_obj.id) in company_ids

    async def test_approve_catalog_with_approved_products(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        """Approve a submitted catalog whose products are all approved/active."""
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="approved"
        )
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id, status="submitted"
        )
        await _add_product_to_catalog(admin_db_session, catalog, product)

        response = await client.post(
            f"/api/v1/platform/catalogs/{catalog.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "approved"
        assert data["approved_by"] == str(reel48_admin_user.id)
        assert data["approved_at"] is not None

    async def test_approve_catalog_with_draft_product_returns_error(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        """Cannot approve a catalog if any product is still draft/submitted."""
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user.id, status="draft"
        )
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id, status="submitted"
        )
        await _add_product_to_catalog(admin_db_session, catalog, product)

        response = await client.post(
            f"/api/v1/platform/catalogs/{catalog.id}/approve",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 422

    async def test_reject_submitted_catalog(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id, status="submitted"
        )

        response = await client.post(
            f"/api/v1/platform/catalogs/{catalog.id}/reject",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "draft"
        assert data["approved_by"] is None

    async def test_activate_approved_catalog(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id, status="approved"
        )

        response = await client.post(
            f"/api/v1/platform/catalogs/{catalog.id}/activate",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "active"

    async def test_close_active_catalog(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id,
            status="active", payment_model="invoice_after_close",
        )

        response = await client.post(
            f"/api/v1/platform/catalogs/{catalog.id}/close",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "closed"

    async def test_close_non_active_catalog_returns_error(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company.id, brand_a1.id)
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user.id, status="draft"
        )

        response = await client.post(
            f"/api/v1/platform/catalogs/{catalog.id}/close",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 403

    async def test_non_reel48_admin_cannot_access_platform_catalogs(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
    ):
        """corporate_admin gets 403 on platform endpoints."""
        response = await client.get(
            "/api/v1/platform/catalogs/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_access_platform_endpoints(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.get(
            "/api/v1/platform/products/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403
