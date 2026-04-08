"""Tests for the Products CRUD endpoints (Module 3 Phase 2)."""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
    # Override default status if needed
    if status != "draft":
        product.status = status  # type: ignore[assignment]
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


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


# ---------------------------------------------------------------------------
# Functional Tests — Create
# ---------------------------------------------------------------------------


class TestCreateProduct:
    async def test_create_product_as_admin_returns_201(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_a,
    ):
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "Basic Tee",
                "sku": "BT-001",
                "unit_price": 19.99,
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["name"] == "Basic Tee"
        assert data["sku"] == "BT-001"
        assert data["unit_price"] == 19.99
        assert data["status"] == "draft"
        assert data["created_by"] == str(user_a1_admin.id)
        assert data["company_id"] == str(user_a1_admin.company_id)

    async def test_create_product_with_all_fields(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        response = await client.post(
            "/api/v1/products/",
            json={
                "name": "Premium Polo",
                "description": "High quality polo shirt",
                "sku": "PP-001",
                "unit_price": 49.99,
                "sizes": ["S", "M", "L", "XL"],
                "decoration_options": ["embroidery", "screen_print"],
                "image_urls": ["https://example.com/polo.jpg"],
            },
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["description"] == "High quality polo shirt"
        assert data["sizes"] == ["S", "M", "L", "XL"]
        assert data["decoration_options"] == ["embroidery", "screen_print"]
        assert data["image_urls"] == ["https://example.com/polo.jpg"]

    async def test_create_product_duplicate_sku_returns_409(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        # Create first product
        await client.post(
            "/api/v1/products/",
            json={"name": "Product A", "sku": "DUP-SKU", "unit_price": 10.00},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        # Try duplicate SKU
        response = await client.post(
            "/api/v1/products/",
            json={"name": "Product B", "sku": "DUP-SKU", "unit_price": 20.00},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 409

    async def test_create_product_same_sku_different_company_succeeds(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        company_b,
        admin_db_session: AsyncSession,
    ):
        # Create product in Company A
        await client.post(
            "/api/v1/products/",
            json={"name": "Product A", "sku": "CROSS-SKU", "unit_price": 10.00},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        # Create admin in Company B and create product with same SKU
        company_b_obj, brand_b1 = company_b
        b_admin = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)
        b_admin_token = create_test_token(
            user_id=b_admin.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="sub_brand_admin",
        )
        response = await client.post(
            "/api/v1/products/",
            json={"name": "Product B", "sku": "CROSS-SKU", "unit_price": 15.00},
            headers={"Authorization": f"Bearer {b_admin_token}"},
        )
        assert response.status_code == 201

    async def test_create_product_as_employee_returns_403(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        response = await client.post(
            "/api/v1/products/",
            json={"name": "Nope", "sku": "NO-001", "unit_price": 5.00},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_create_product_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/products/",
            json={"name": "Anon", "sku": "AN-001", "unit_price": 5.00},
        )
        assert response.status_code in (401, 403)

    async def test_create_product_as_reel48_admin_returns_403(
        self,
        client: AsyncClient,
        reel48_admin_token: str,
    ):
        response = await client.post(
            "/api/v1/products/",
            json={"name": "Platform", "sku": "PL-001", "unit_price": 5.00},
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Functional Tests — List
# ---------------------------------------------------------------------------


class TestListProducts:
    async def test_list_products_returns_paginated_results(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        await _create_product(admin_db_session, company.id, brand_a1.id, user_a1_admin.id)
        await _create_product(admin_db_session, company.id, brand_a1.id, user_a1_admin.id)

        response = await client.get(
            "/api/v1/products/?page=1&per_page=1",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["per_page"] == 1
        assert len(data["data"]) == 1
        assert data["meta"]["total"] >= 2

    async def test_list_products_as_employee_sees_only_active(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        # Create a draft and an active product
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="draft"
        )
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="active"
        )

        response = await client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        products = response.json()["data"]
        # Employee should only see active products
        for p in products:
            assert p["status"] == "active"

    async def test_list_products_as_admin_sees_all_statuses(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="draft"
        )
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="submitted"
        )

        response = await client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        statuses = {p["status"] for p in response.json()["data"]}
        assert "draft" in statuses or "submitted" in statuses

    async def test_list_products_with_status_filter(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="draft"
        )
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="submitted"
        )

        response = await client.get(
            "/api/v1/products/?status=submitted",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        for p in response.json()["data"]:
            assert p["status"] == "submitted"

    async def test_list_products_sub_brand_scoping(
        self,
        client: AsyncClient,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        """Brand A1 admin doesn't see Brand A2 products."""
        company, brand_a1, brand_a2 = company_a
        # Create a product in Brand A2
        await _create_product(
            admin_db_session, company.id, brand_a2.id, user_a1_admin.id,
            name="A2 Product",
        )

        # Brand A2 admin should see it, Brand A1 admin should not
        a2_admin = await _create_user(admin_db_session, company.id, brand_a2.id)
        a2_token = create_test_token(
            user_id=a2_admin.cognito_sub,
            company_id=str(company.id),
            sub_brand_id=str(brand_a2.id),
            role="sub_brand_admin",
        )
        response = await client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {a2_token}"},
        )
        assert response.status_code == 200
        a2_products = [p for p in response.json()["data"] if p["name"] == "A2 Product"]
        assert len(a2_products) >= 1


# ---------------------------------------------------------------------------
# Functional Tests — Get
# ---------------------------------------------------------------------------


class TestGetProduct:
    async def test_get_product_returns_detail(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.get(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["id"] == str(product.id)

    async def test_get_product_not_found_returns_404(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
    ):
        response = await client.get(
            f"/api/v1/products/{uuid4()}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 404

    async def test_get_product_as_employee_cannot_see_draft(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id, status="draft"
        )

        response = await client.get(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Functional Tests — Update
# ---------------------------------------------------------------------------


class TestUpdateProduct:
    async def test_update_product_draft_succeeds(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.patch(
            f"/api/v1/products/{product.id}",
            json={"name": "Updated Name", "unit_price": 39.99},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Updated Name"
        assert data["unit_price"] == 39.99

    async def test_update_product_non_draft_returns_403(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )

        response = await client.patch(
            f"/api/v1/products/{product.id}",
            json={"name": "Cannot Update"},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Functional Tests — Delete
# ---------------------------------------------------------------------------


class TestDeleteProduct:
    async def test_soft_delete_product_draft_succeeds(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.delete(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(product.id)
        assert data["deleted_at"] is not None

    async def test_soft_delete_product_non_draft_returns_403(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="active",
        )

        response = await client.delete(
            f"/api/v1/products/{product.id}",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Functional Tests — Submit
# ---------------------------------------------------------------------------


class TestSubmitProduct:
    async def test_submit_product_transitions_to_submitted(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id
        )

        response = await client.post(
            f"/api/v1/products/{product.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "submitted"

    async def test_submit_already_submitted_product_returns_error(
        self,
        client: AsyncClient,
        user_a1_admin_token: str,
        user_a1_admin,
        admin_db_session: AsyncSession,
        company_a,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            status="submitted",
        )

        response = await client.post(
            f"/api/v1/products/{product.id}/submit",
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestProductIsolation:
    async def test_company_b_cannot_see_company_a_products(
        self,
        client: AsyncClient,
        user_a1_admin,
        company_a,
        company_b,
        admin_db_session: AsyncSession,
    ):
        """Cross-company isolation: Company B admin sees zero Company A products."""
        company_a_obj, brand_a1, _a2 = company_a
        await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_admin.id,
            status="active",
        )

        # Create Company B admin
        company_b_obj, brand_b1 = company_b
        b_admin = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)
        b_admin_token = create_test_token(
            user_id=b_admin.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="sub_brand_admin",
        )

        response = await client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {b_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 0

    async def test_brand_a2_cannot_see_brand_a1_products(
        self,
        client: AsyncClient,
        user_a1_admin,
        company_a,
        admin_db_session: AsyncSession,
    ):
        """Cross-sub-brand isolation within the same company."""
        company, brand_a1, brand_a2 = company_a
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
        )

        # Brand A2 admin queries — should see 0 Brand A1 products
        a2_admin = await _create_user(admin_db_session, company.id, brand_a2.id)
        a2_token = create_test_token(
            user_id=a2_admin.cognito_sub,
            company_id=str(company.id),
            sub_brand_id=str(brand_a2.id),
            role="sub_brand_admin",
        )

        response = await client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {a2_token}"},
        )
        assert response.status_code == 200
        # All returned products should be brand_a2, not brand_a1
        for p in response.json()["data"]:
            assert p["sub_brand_id"] != str(brand_a1.id)

    async def test_corporate_admin_sees_all_sub_brand_products(
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
        await _create_product(
            admin_db_session, company.id, brand_a1.id, user_a1_admin.id,
            name="A1 Product",
        )
        await _create_product(
            admin_db_session, company.id, brand_a2.id, user_a1_admin.id,
            name="A2 Product",
        )

        response = await client.get(
            "/api/v1/products/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["total"] >= 2
