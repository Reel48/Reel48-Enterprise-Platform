"""Tests for Bulk Order session CRUD endpoints (Module 5 Phase 2)."""

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bulk_order import BulkOrder
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.product import Product
from app.models.user import User
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_active_catalog_with_products(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    payment_model: str = "self_service",
    num_products: int = 2,
    price_overrides: list[float | None] | None = None,
    buying_window_opens_at=None,
    buying_window_closes_at=None,
) -> tuple[Catalog, list[Product], list[CatalogProduct]]:
    """Create an active catalog with active products for testing bulk orders."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Test Catalog {uuid4().hex[:6]}",
        description="Catalog for bulk order tests",
        slug=f"test-catalog-{uuid4().hex[:6]}",
        payment_model=payment_model,
        status="active",
        buying_window_opens_at=buying_window_opens_at,
        buying_window_closes_at=buying_window_closes_at,
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)

    products: list[Product] = []
    catalog_products: list[CatalogProduct] = []

    for i in range(num_products):
        override = None
        if price_overrides and i < len(price_overrides):
            override = price_overrides[i]

        product = Product(
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            name=f"Product {i + 1}",
            description=f"Test product {i + 1}",
            sku=f"SKU-{uuid4().hex[:8].upper()}",
            unit_price=29.99 + i * 10,
            sizes=["S", "M", "L", "XL"],
            decoration_options=["screen_print", "embroidery"],
            image_urls=[],
            status="active",
            created_by=created_by,
        )
        db.add(product)
        await db.flush()
        await db.refresh(product)
        products.append(product)

        cp = CatalogProduct(
            catalog_id=catalog.id,
            product_id=product.id,
            company_id=company_id,
            sub_brand_id=sub_brand_id,
            display_order=i,
            price_override=override,
        )
        db.add(cp)
        await db.flush()
        await db.refresh(cp)
        catalog_products.append(cp)

    return catalog, products, catalog_products


async def _create_bulk_order_via_api(
    client: AsyncClient,
    token: str,
    catalog_id,
    title: str = "Test Bulk Order",
) -> dict:
    """Create a bulk order via API and return the response JSON data."""
    response = await client.post(
        "/api/v1/bulk_orders/",
        headers={"Authorization": f"Bearer {token}"},
        json={"catalog_id": str(catalog_id), "title": title},
    )
    assert response.status_code == 201
    return response.json()["data"]


# ---------------------------------------------------------------------------
# Functional Tests — Create Bulk Order
# ---------------------------------------------------------------------------


class TestCreateBulkOrder:
    async def test_create_bulk_order_returns_201(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Manager creates a draft bulk order → 201 with correct defaults."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Q3 Uniforms"
        )

        assert data["status"] == "draft"
        assert data["total_items"] == 0
        assert float(data["total_amount"]) == 0.0
        assert data["catalog_id"] == str(catalog.id)
        assert data["title"] == "Q3 Uniforms"
        assert data["created_by"] == str(user_a1_manager.id)
        assert data["submitted_at"] is None
        assert data["approved_by"] is None

    async def test_create_bulk_order_generates_order_number(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Order number matches BLK-YYYYMMDD-XXXX pattern."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )

        pattern = r"^BLK-\d{8}-[0-9A-F]{4}$"
        assert re.match(pattern, data["order_number"]), (
            f"Order number '{data['order_number']}' doesn't match BLK-YYYYMMDD-XXXX"
        )

    async def test_create_bulk_order_validates_catalog_exists(
        self,
        client: AsyncClient,
        user_a1_manager_token: str,
    ):
        """Nonexistent catalog_id → 404."""
        response = await client.post(
            "/api/v1/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"catalog_id": str(uuid4()), "title": "Bad Catalog"},
        )
        assert response.status_code == 404

    async def test_create_bulk_order_validates_catalog_active(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Draft catalog → 403."""
        company, brand_a1, _a2 = company_a
        catalog = Catalog(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            name="Draft Catalog",
            slug=f"draft-catalog-{uuid4().hex[:6]}",
            payment_model="self_service",
            status="draft",
            created_by=user_a1_manager.id,
        )
        admin_db_session.add(catalog)
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"catalog_id": str(catalog.id), "title": "Should Fail"},
        )
        assert response.status_code == 403

    async def test_create_bulk_order_validates_buying_window_closed(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Invoice-after-close catalog with past window → 422."""
        company, brand_a1, _a2 = company_a
        now = datetime.now(UTC)
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session,
            company.id,
            brand_a1.id,
            user_a1_manager.id,
            payment_model="invoice_after_close",
            buying_window_opens_at=now - timedelta(days=30),
            buying_window_closes_at=now - timedelta(days=1),
        )

        response = await client.post(
            "/api/v1/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"catalog_id": str(catalog.id), "title": "Window Closed"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Functional Tests — List, Get, Update, Delete
# ---------------------------------------------------------------------------


class TestListBulkOrders:
    async def test_list_bulk_orders_paginated(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """List returns paginated results with meta."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        # Create two bulk orders
        await _create_bulk_order_via_api(client, user_a1_manager_token, catalog.id, "Order 1")
        await _create_bulk_order_via_api(client, user_a1_manager_token, catalog.id, "Order 2")

        response = await client.get(
            "/api/v1/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["data"]) >= 2
        assert "meta" in body
        assert body["meta"]["page"] == 1
        assert body["meta"]["per_page"] == 20
        assert body["meta"]["total"] >= 2

    async def test_list_bulk_orders_filter_by_status(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """?status=draft returns only draft orders."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        await _create_bulk_order_via_api(client, user_a1_manager_token, catalog.id, "Draft One")

        response = await client.get(
            "/api/v1/bulk_orders/?status=draft",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["meta"]["total"] >= 1
        for order in body["data"]:
            assert order["status"] == "draft"


class TestGetBulkOrder:
    async def test_get_bulk_order_detail(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """GET returns bulk order with empty items list."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        data = await _create_bulk_order_via_api(client, user_a1_manager_token, catalog.id)

        response = await client.get(
            f"/api/v1/bulk_orders/{data['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        detail = response.json()["data"]
        assert detail["id"] == data["id"]
        assert detail["items"] == []


class TestUpdateBulkOrder:
    async def test_update_draft_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """PATCH updates title/description/notes on a draft."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        data = await _create_bulk_order_via_api(client, user_a1_manager_token, catalog.id)

        response = await client.patch(
            f"/api/v1/bulk_orders/{data['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={
                "title": "Updated Title",
                "description": "New description",
                "notes": "Important notes",
            },
        )
        assert response.status_code == 200
        updated = response.json()["data"]
        assert updated["title"] == "Updated Title"
        assert updated["description"] == "New description"
        assert updated["notes"] == "Important notes"

    async def test_update_non_draft_bulk_order_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Updating a submitted bulk order → 403."""
        company, brand_a1, _a2 = company_a
        # Need a real catalog for FK constraint
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )
        bulk_order = BulkOrder(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            catalog_id=catalog.id,
            created_by=user_a1_manager.id,
            title="Submitted Order",
            order_number=f"BLK-20260409-{uuid4().hex[:4].upper()}",
            status="submitted",
            total_items=0,
            total_amount=0,
        )
        admin_db_session.add(bulk_order)
        await admin_db_session.flush()
        await admin_db_session.refresh(bulk_order)

        response = await client.patch(
            f"/api/v1/bulk_orders/{bulk_order.id}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"title": "Should Fail"},
        )
        assert response.status_code == 403


class TestDeleteBulkOrder:
    async def test_delete_draft_bulk_order_returns_204(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Hard delete of a draft → 204, subsequent GET → 404."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        data = await _create_bulk_order_via_api(client, user_a1_manager_token, catalog.id)

        response = await client.delete(
            f"/api/v1/bulk_orders/{data['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 204

        # Verify it's gone
        response = await client.get(
            f"/api/v1/bulk_orders/{data['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 404

    async def test_delete_non_draft_bulk_order_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Deleting a submitted bulk order → 403."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )
        bulk_order = BulkOrder(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            catalog_id=catalog.id,
            created_by=user_a1_manager.id,
            title="Submitted Order",
            order_number=f"BLK-20260409-{uuid4().hex[:4].upper()}",
            status="submitted",
            total_items=0,
            total_amount=0,
        )
        admin_db_session.add(bulk_order)
        await admin_db_session.flush()
        await admin_db_session.refresh(bulk_order)

        response = await client.delete(
            f"/api/v1/bulk_orders/{bulk_order.id}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestBulkOrderAuthorization:
    async def test_employee_cannot_create_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Employee role → 403 on bulk order creation."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
            json={"catalog_id": str(catalog.id), "title": "Should Fail"},
        )
        assert response.status_code == 403

    async def test_employee_cannot_list_bulk_orders(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
    ):
        """Employee role → 403 on bulk order list."""
        response = await client.get(
            "/api/v1/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestBulkOrderIsolation:
    async def test_company_b_cannot_see_company_a_bulk_orders(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
        company_b,
    ):
        """Cross-company isolation: Company B manager sees zero Company A bulk orders."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Create catalog and bulk order in Company A
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_manager.id
        )
        data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Company A Order"
        )

        # Create a manager in Company B (inline)
        user_b = User(
            company_id=company_b_obj.id,
            sub_brand_id=brand_b1.id,
            cognito_sub=str(uuid4()),
            email=f"manager-b-{uuid4().hex[:6]}@companyb.com",
            full_name="Manager B",
            role="regional_manager",
        )
        admin_db_session.add(user_b)
        await admin_db_session.flush()
        token_b = create_test_token(
            user_id=user_b.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="regional_manager",
        )

        # List as Company B manager → empty
        response = await client.get(
            "/api/v1/bulk_orders/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 200
        assert len(response.json()["data"]) == 0

        # GET the specific ID → 404
        response = await client.get(
            f"/api/v1/bulk_orders/{data['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 404
