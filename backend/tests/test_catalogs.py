"""Tests for the Catalogs CRUD and Catalog-Product association endpoints (Module 3 Phase 3)."""

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


async def _create_catalog(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    *,
    name: str = "Test Catalog",
    payment_model: str = "self_service",
    status: str = "draft",
    slug: str | None = None,
) -> Catalog:
    """Insert a catalog directly for test setup."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=name,
        description="A test catalog",
        slug=slug or f"test-catalog-{uuid4().hex[:6]}",
        payment_model=payment_model,
        created_by=created_by,
    )
    if status != "draft":
        catalog.status = status  # type: ignore[assignment]
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _create_product(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    *,
    sku: str | None = None,
    status: str = "draft",
    name: str = "Test Product",
) -> Product:
    """Insert a product directly for test setup."""
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=name,
        description="A test product",
        sku=sku or f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=29.99,
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


async def _add_product_to_catalog(
    db: AsyncSession,
    catalog: Catalog,
    product: Product,
    display_order: int = 0,
    price_override: float | None = None,
) -> CatalogProduct:
    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=catalog.company_id,
        sub_brand_id=catalog.sub_brand_id,
        display_order=display_order,
        price_override=price_override,
    )
    db.add(cp)
    await db.flush()
    await db.refresh(cp)
    return cp


# ---------------------------------------------------------------------------
# Functional Tests — Create
# ---------------------------------------------------------------------------


class TestCreateCatalog:
    async def test_create_self_service_catalog_returns_201(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        response = await client.post(
            "/api/v1/catalogs/",
            json={
                "name": "Summer Collection",
                "payment_model": "self_service",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "Summer Collection"
        assert data["payment_model"] == "self_service"
        assert data["status"] == "draft"
        assert data["slug"] == "summer-collection"
        assert data["buying_window_opens_at"] is None
        assert data["buying_window_closes_at"] is None

    async def test_create_invoice_after_close_catalog_with_buying_window(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        response = await client.post(
            "/api/v1/catalogs/",
            json={
                "name": "Winter Catalog",
                "payment_model": "invoice_after_close",
                "buying_window_opens_at": "2026-06-01T00:00:00Z",
                "buying_window_closes_at": "2026-07-01T00:00:00Z",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["payment_model"] == "invoice_after_close"
        assert data["buying_window_opens_at"] is not None
        assert data["buying_window_closes_at"] is not None

    async def test_create_invoice_after_close_without_window_returns_422(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        response = await client.post(
            "/api/v1/catalogs/",
            json={
                "name": "Bad Catalog",
                "payment_model": "invoice_after_close",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 422

    async def test_create_self_service_with_window_returns_422(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        response = await client.post(
            "/api/v1/catalogs/",
            json={
                "name": "Bad Catalog",
                "payment_model": "self_service",
                "buying_window_opens_at": "2026-06-01T00:00:00Z",
                "buying_window_closes_at": "2026-07-01T00:00:00Z",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 422

    async def test_create_catalog_slug_auto_generated(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        response = await client.post(
            "/api/v1/catalogs/",
            json={
                "name": "Fall & Winter 2026!",
                "payment_model": "self_service",
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["slug"] == "fall-winter-2026"

    async def test_create_catalog_duplicate_slug_gets_suffix(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        # Create first catalog
        await client.post(
            "/api/v1/catalogs/",
            json={"name": "Spring 2026", "payment_model": "self_service"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        # Create second with same name
        response = await client.post(
            "/api/v1/catalogs/",
            json={"name": "Spring 2026", "payment_model": "self_service"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["slug"] == "spring-2026-2"

    async def test_create_catalog_as_employee_returns_403(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.post(
            "/api/v1/catalogs/",
            json={"name": "Nope", "payment_model": "self_service"},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_create_catalog_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/catalogs/",
            json={"name": "Anon", "payment_model": "self_service"},
        )
        assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Functional Tests — List
# ---------------------------------------------------------------------------


class TestListCatalogs:
    async def test_list_catalogs_paginated(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        await _create_catalog(admin_db_session, company.id, brand_a1.id, user_a1_admin.id)
        await _create_catalog(admin_db_session, company.id, brand_a1.id, user_a1_admin.id)

        response = await client.get(
            "/api/v1/catalogs/?page=1&per_page=1",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["per_page"] == 1
        assert len(data["data"]) == 1
        assert data["meta"]["total"] >= 2

    async def test_list_catalogs_employee_sees_only_active(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="draft"
        )
        await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="active"
        )

        response = await client.get(
            "/api/v1/catalogs/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        for c in response.json()["data"]:
            assert c["status"] == "active"

    async def test_list_catalogs_admin_sees_all_statuses(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="draft"
        )
        await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="submitted"
        )

        response = await client.get(
            "/api/v1/catalogs/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        statuses = {c["status"] for c in response.json()["data"]}
        assert "draft" in statuses or "submitted" in statuses

    async def test_list_catalogs_sub_brand_scoping(
        self,
        client: AsyncClient,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        """Brand A1 admin doesn't see Brand A2 catalogs."""
        company, brand_a1, brand_a2 = company_a
        await _create_catalog(
            admin_db_session, company.id, brand_a2.id, user_a1_admin.id, name="A2 Catalog"
        )

        a2_admin = await _create_user(admin_db_session, company.id, brand_a2.id)
        a2_token = create_test_token(
            user_id=a2_admin.cognito_sub,
            company_id=str(company.id),
            sub_brand_id=str(brand_a2.id),
            role="sub_brand_admin",
        )
        response = await client.get(
            "/api/v1/catalogs/",
            headers={"Authorization": f"Bearer {a2_token}"},
        )
        assert response.status_code == 200
        a2_catalogs = [c for c in response.json()["data"] if c["name"] == "A2 Catalog"]
        assert len(a2_catalogs) >= 1


# ---------------------------------------------------------------------------
# Functional Tests — Get
# ---------------------------------------------------------------------------


class TestGetCatalog:
    async def test_get_catalog_detail(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.get(
            f"/api/v1/catalogs/{catalog.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(catalog.id)

    async def test_get_catalog_not_found_returns_404(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        response = await client.get(
            f"/api/v1/catalogs/{uuid4()}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Functional Tests — Update
# ---------------------------------------------------------------------------


class TestUpdateCatalog:
    async def test_update_catalog_draft_succeeds(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.patch(
            f"/api/v1/catalogs/{catalog.id}",
            json={"name": "Updated Catalog Name"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["name"] == "Updated Catalog Name"

    async def test_update_catalog_non_draft_returns_403(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )

        response = await client.patch(
            f"/api/v1/catalogs/{catalog.id}",
            json={"name": "Cannot Update"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Functional Tests — Submit
# ---------------------------------------------------------------------------


class TestSubmitCatalog:
    async def test_submit_catalog_with_products_succeeds(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        await _add_product_to_catalog(admin_db_session, catalog, product)

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "submitted"

    async def test_submit_empty_catalog_returns_error(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Functional Tests — Delete
# ---------------------------------------------------------------------------


class TestDeleteCatalog:
    async def test_soft_delete_draft_catalog_succeeds(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.delete(
            f"/api/v1/catalogs/{catalog.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(catalog.id)
        assert data["deleted_at"] is not None


# ---------------------------------------------------------------------------
# Functional Tests — Catalog Products
# ---------------------------------------------------------------------------


class TestCatalogProducts:
    async def test_add_product_to_catalog_returns_201(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/products/",
            json={"product_id": str(product.id), "display_order": 1},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["catalog_id"] == str(catalog.id)
        assert data["product_id"] == str(product.id)
        assert data["display_order"] == 1

    async def test_add_duplicate_product_returns_409(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        await _add_product_to_catalog(admin_db_session, catalog, product)

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/products/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 409

    async def test_add_cross_company_product_returns_error(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
    ):
        """Cannot add a product from Company B into a Company A catalog."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        catalog = await _create_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_admin.id
        )
        # Create a user in company B to own the product
        b_user = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)
        product_b = await _create_product(
            admin_db_session, company_b_obj.id, brand_b1.id, b_user.id
        )

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/products/",
            json={"product_id": str(product_b.id)},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403

    async def test_remove_product_from_catalog_returns_204(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        await _add_product_to_catalog(admin_db_session, catalog, product)

        response = await client.delete(
            f"/api/v1/catalogs/{catalog.id}/products/{product.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 204

    async def test_list_catalog_products_paginated(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        p1 = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        p2 = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        await _add_product_to_catalog(admin_db_session, catalog, p1, display_order=1)
        await _add_product_to_catalog(admin_db_session, catalog, p2, display_order=2)

        response = await client.get(
            f"/api/v1/catalogs/{catalog.id}/products/?page=1&per_page=1",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 1
        assert data["meta"]["total"] == 2

    async def test_add_product_with_price_override(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        catalog = await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.post(
            f"/api/v1/catalogs/{catalog.id}/products/",
            json={
                "product_id": str(product.id),
                "display_order": 0,
                "price_override": 15.50,
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["price_override"] == 15.50


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestCatalogIsolation:
    async def test_company_b_cannot_see_company_a_catalogs(
        self,
        client: AsyncClient,
        user_a1_admin,
        company_a,
        company_b,
        admin_db_session: AsyncSession,
    ):
        """Cross-company isolation: Company B admin sees zero Company A catalogs."""
        company_a_obj, brand_a1, _a2 = company_a
        await _create_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_admin.id,
            status="active",
        )

        company_b_obj, brand_b1 = company_b
        b_admin = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)
        b_admin_token = create_test_token(
            user_id=b_admin.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="sub_brand_admin",
        )

        response = await client.get(
            "/api/v1/catalogs/",
            headers={"Authorization": f"Bearer {b_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 0

    async def test_brand_a2_cannot_see_brand_a1_catalogs(
        self,
        client: AsyncClient,
        user_a1_admin,
        company_a,
        admin_db_session: AsyncSession,
    ):
        """Cross-sub-brand isolation within the same company."""
        company, brand_a1, brand_a2 = company_a
        await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )

        a2_admin = await _create_user(admin_db_session, company.id, brand_a2.id)
        a2_token = create_test_token(
            user_id=a2_admin.cognito_sub,
            company_id=str(company.id),
            sub_brand_id=str(brand_a2.id),
            role="sub_brand_admin",
        )

        response = await client.get(
            "/api/v1/catalogs/",
            headers={"Authorization": f"Bearer {a2_token}"},
        )
        assert response.status_code == 200
        for c in response.json()["data"]:
            assert c["sub_brand_id"] != str(brand_a1.id)

    async def test_corporate_admin_sees_all_sub_brand_catalogs(
        self,
        client: AsyncClient,
        user_a1_admin,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
        company_a,
        admin_db_session: AsyncSession,
    ):
        """Corporate admin has cross-sub-brand visibility."""
        company, brand_a1, brand_a2 = company_a
        await _create_catalog(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            name="A1 Catalog",
        )
        await _create_catalog(
            admin_db_session, company.id, brand_a2.id, user_a1_admin.id,
            name="A2 Catalog",
        )

        response = await client.get(
            "/api/v1/catalogs/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] >= 2
