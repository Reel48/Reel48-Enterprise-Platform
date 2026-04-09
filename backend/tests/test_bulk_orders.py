"""Tests for Bulk Order endpoints (Module 5 Phases 2–3)."""

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


# ---------------------------------------------------------------------------
# Helpers — Item management
# ---------------------------------------------------------------------------


async def _add_item_via_api(
    client: AsyncClient,
    token: str,
    bulk_order_id: str,
    product_id: str,
    quantity: int = 1,
    size: str | None = None,
    decoration: str | None = None,
    employee_id: str | None = None,
    notes: str | None = None,
) -> dict:
    """POST an item to a bulk order and return the response data."""
    body: dict = {"product_id": product_id, "quantity": quantity}
    if size is not None:
        body["size"] = size
    if decoration is not None:
        body["decoration"] = decoration
    if employee_id is not None:
        body["employee_id"] = employee_id
    if notes is not None:
        body["notes"] = notes

    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/items/",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


# ---------------------------------------------------------------------------
# Functional Tests — Add Item
# ---------------------------------------------------------------------------


class TestAddItem:
    async def test_add_item_to_draft_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Add an item → 201, snapshotted product data, totals updated."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )

        item = await _add_item_via_api(
            client,
            user_a1_manager_token,
            bo["id"],
            str(products[0].id),
            quantity=3,
            size="M",
            decoration="embroidery",
        )

        assert item["product_name"] == products[0].name
        assert item["product_sku"] == products[0].sku
        assert float(item["unit_price"]) == float(products[0].unit_price)
        assert item["quantity"] == 3
        assert float(item["line_total"]) == float(products[0].unit_price) * 3
        assert item["employee_id"] is None
        assert item["size"] == "M"
        assert item["decoration"] == "embroidery"

        # Verify bulk order totals updated
        detail = await client.get(
            f"/api/v1/bulk_orders/{bo['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        bo_data = detail.json()["data"]
        assert bo_data["total_items"] == 3
        assert float(bo_data["total_amount"]) == float(item["line_total"])

    async def test_add_item_validates_product_in_catalog(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Product exists but NOT in catalog → 404."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        # Create a product NOT in the catalog
        orphan = Product(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            name="Orphan Product",
            sku=f"SKU-ORPHAN-{uuid4().hex[:6].upper()}",
            unit_price=50.00,
            status="active",
            created_by=user_a1_manager.id,
        )
        admin_db_session.add(orphan)
        await admin_db_session.flush()
        await admin_db_session.refresh(orphan)

        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        response = await client.post(
            f"/api/v1/bulk_orders/{bo['id']}/items/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"product_id": str(orphan.id), "quantity": 1},
        )
        assert response.status_code == 404

    async def test_add_item_validates_product_active(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Product in catalog but status='draft' → 422."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        # Set product to draft
        products[0].status = "draft"
        await admin_db_session.flush()

        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        response = await client.post(
            f"/api/v1/bulk_orders/{bo['id']}/items/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"product_id": str(products[0].id), "quantity": 1},
        )
        assert response.status_code == 422

    async def test_add_item_uses_catalog_price_override(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """CatalogProduct with price_override → item uses override, not product.unit_price."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session,
            company.id,
            brand_a1.id,
            user_a1_manager.id,
            num_products=1,
            price_overrides=[19.99],
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        item = await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[0].id), quantity=2,
        )
        assert float(item["unit_price"]) == 19.99
        assert float(item["line_total"]) == 19.99 * 2

    async def test_add_item_with_employee_id(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        user_a1_employee,
        company_a,
    ):
        """Provide a valid employee_id → item has employee_id set."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        item = await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[0].id), employee_id=str(user_a1_employee.id),
        )
        assert item["employee_id"] == str(user_a1_employee.id)

    async def test_add_item_with_invalid_employee_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
        company_b,
    ):
        """Employee from Company B → validation error."""
        company, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        # Create Company B employee inline
        user_b = User(
            company_id=company_b_obj.id,
            sub_brand_id=brand_b1.id,
            cognito_sub=str(uuid4()),
            email=f"emp-b-{uuid4().hex[:6]}@companyb.com",
            full_name="Employee B",
            role="employee",
        )
        admin_db_session.add(user_b)
        await admin_db_session.flush()
        await admin_db_session.refresh(user_b)

        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        response = await client.post(
            f"/api/v1/bulk_orders/{bo['id']}/items/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"product_id": str(products[0].id), "quantity": 1,
                  "employee_id": str(user_b.id)},
        )
        assert response.status_code == 422

    async def test_add_item_validates_size(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Invalid size → 422."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        response = await client.post(
            f"/api/v1/bulk_orders/{bo['id']}/items/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"product_id": str(products[0].id), "quantity": 1,
                  "size": "XXXL"},
        )
        assert response.status_code == 422

    async def test_add_item_validates_decoration(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Invalid decoration → 422."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        response = await client.post(
            f"/api/v1/bulk_orders/{bo['id']}/items/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"product_id": str(products[0].id), "quantity": 1,
                  "decoration": "laser_etching"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Functional Tests — Update Item
# ---------------------------------------------------------------------------


class TestUpdateItem:
    async def test_update_item_quantity_recalculates_totals(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """PATCH quantity → line_total and bulk order totals updated."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        item = await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[0].id), quantity=2,
        )

        # Update quantity from 2 → 5
        response = await client.patch(
            f"/api/v1/bulk_orders/{bo['id']}/items/{item['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"quantity": 5},
        )
        assert response.status_code == 200
        updated = response.json()["data"]
        assert updated["quantity"] == 5
        expected_total = float(products[0].unit_price) * 5
        assert float(updated["line_total"]) == expected_total

        # Verify bulk order totals
        detail = await client.get(
            f"/api/v1/bulk_orders/{bo['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        bo_data = detail.json()["data"]
        assert bo_data["total_items"] == 5
        assert float(bo_data["total_amount"]) == expected_total

    async def test_update_item_on_non_draft_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """PATCH item on submitted bulk order → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        # Insert submitted bulk order + item directly
        from app.models.bulk_order_item import BulkOrderItem as BOItem
        bulk_order = BulkOrder(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            catalog_id=catalog.id,
            created_by=user_a1_manager.id,
            title="Submitted Order",
            order_number=f"BLK-20260409-{uuid4().hex[:4].upper()}",
            status="submitted",
            total_items=1,
            total_amount=29.99,
        )
        admin_db_session.add(bulk_order)
        await admin_db_session.flush()
        await admin_db_session.refresh(bulk_order)

        item = BOItem(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            bulk_order_id=bulk_order.id,
            product_id=products[0].id,
            product_name=products[0].name,
            product_sku=products[0].sku,
            unit_price=29.99,
            quantity=1,
            line_total=29.99,
        )
        admin_db_session.add(item)
        await admin_db_session.flush()
        await admin_db_session.refresh(item)

        response = await client.patch(
            f"/api/v1/bulk_orders/{bulk_order.id}/items/{item.id}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"quantity": 10},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Functional Tests — Remove Item
# ---------------------------------------------------------------------------


class TestRemoveItem:
    async def test_remove_item_recalculates_totals(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Add 2 items, delete one → totals reflect only the remaining item."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=2,
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        item1 = await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[0].id), quantity=2,
        )
        item2 = await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[1].id), quantity=3,
        )

        # Delete item1
        response = await client.delete(
            f"/api/v1/bulk_orders/{bo['id']}/items/{item1['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 204

        # Verify totals reflect only item2
        detail = await client.get(
            f"/api/v1/bulk_orders/{bo['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        bo_data = detail.json()["data"]
        assert bo_data["total_items"] == 3
        assert float(bo_data["total_amount"]) == float(item2["line_total"])
        assert len(bo_data["items"]) == 1

    async def test_remove_item_returns_204(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """DELETE item → 204 with no body, item gone from bulk order."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )
        item = await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[0].id), quantity=1,
        )

        response = await client.delete(
            f"/api/v1/bulk_orders/{bo['id']}/items/{item['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 204
        assert response.content == b""

        # Verify item is gone
        detail = await client.get(
            f"/api/v1/bulk_orders/{bo['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert detail.json()["data"]["items"] == []


# ---------------------------------------------------------------------------
# State Tests — Item Management
# ---------------------------------------------------------------------------


class TestItemStateRestrictions:
    async def test_add_item_to_submitted_bulk_order_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Adding item to submitted bulk order → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=1,
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

        response = await client.post(
            f"/api/v1/bulk_orders/{bulk_order.id}/items/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"product_id": str(products[0].id), "quantity": 1},
        )
        assert response.status_code == 403

    async def test_bulk_order_totals_reflect_all_items(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Add 3 items with different quantities/prices → totals are correct."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id,
            num_products=3,
            price_overrides=[10.00, 20.00, 30.00],
        )
        bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id
        )

        # Add items: qty 5 @ $10, qty 10 @ $20, qty 3 @ $30
        await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[0].id), quantity=5,
        )
        await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[1].id), quantity=10,
        )
        await _add_item_via_api(
            client, user_a1_manager_token, bo["id"],
            str(products[2].id), quantity=3,
        )

        detail = await client.get(
            f"/api/v1/bulk_orders/{bo['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        bo_data = detail.json()["data"]

        assert bo_data["total_items"] == 5 + 10 + 3  # 18
        expected_amount = (5 * 10.00) + (10 * 20.00) + (3 * 30.00)  # 340.00
        assert float(bo_data["total_amount"]) == expected_amount
        assert len(bo_data["items"]) == 3


# ---------------------------------------------------------------------------
# Helpers — Status transitions (Phase 4)
# ---------------------------------------------------------------------------


async def _create_bulk_order_with_items(
    client: AsyncClient,
    token: str,
    catalog_id,
    product_id,
    title: str = "Bulk Order With Items",
    num_items: int = 2,
) -> dict:
    """Create a bulk order via API, add items, return the bulk order data."""
    bo_data = await _create_bulk_order_via_api(client, token, catalog_id, title)
    for i in range(num_items):
        await _add_item_via_api(
            client, token, bo_data["id"], str(product_id), quantity=i + 1,
        )
    return bo_data


async def _submit_bulk_order(client: AsyncClient, token: str, bulk_order_id: str) -> dict:
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _approve_bulk_order(client: AsyncClient, token: str, bulk_order_id: str) -> dict:
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _process_bulk_order(client: AsyncClient, token: str, bulk_order_id: str) -> dict:
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/process",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _ship_bulk_order(client: AsyncClient, token: str, bulk_order_id: str) -> dict:
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/ship",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


async def _deliver_bulk_order(client: AsyncClient, token: str, bulk_order_id: str) -> dict:
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/deliver",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


# ---------------------------------------------------------------------------
# Functional Tests — Status Transitions (Phase 4)
# ---------------------------------------------------------------------------


class TestBulkOrderStatusTransitions:
    """Lifecycle happy-path tests: submit → approve → process → ship → deliver."""

    async def test_submit_draft_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit a draft bulk order with items → status='submitted', submitted_at set."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        data = await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])

        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None

    async def test_submit_empty_bulk_order_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit a bulk order with NO items → 422."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Empty Order"
        )

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/submit",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 422

    async def test_submit_non_draft_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit already-submitted bulk order → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])

        # Try to submit again
        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/submit",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403

    async def test_approve_submitted_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Approve a submitted bulk order → status='approved', approved_by/approved_at set."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])
        data = await _approve_bulk_order(client, user_a1_manager_token, bo_data["id"])

        assert data["status"] == "approved"
        assert data["approved_by"] == str(user_a1_manager.id)
        assert data["approved_at"] is not None

    async def test_approve_non_submitted_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Approve a draft bulk order → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/approve",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403

    async def test_process_approved_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit → approve → process → status='processing'."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _approve_bulk_order(client, user_a1_manager_token, bo_data["id"])
        data = await _process_bulk_order(client, user_a1_manager_token, bo_data["id"])

        assert data["status"] == "processing"

    async def test_ship_processing_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit → approve → process → ship → status='shipped'."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _approve_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _process_bulk_order(client, user_a1_manager_token, bo_data["id"])
        data = await _ship_bulk_order(client, user_a1_manager_token, bo_data["id"])

        assert data["status"] == "shipped"

    async def test_deliver_shipped_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Full lifecycle: submit → approve → process → ship → deliver → status='delivered'."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _approve_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _process_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _ship_bulk_order(client, user_a1_manager_token, bo_data["id"])
        data = await _deliver_bulk_order(client, user_a1_manager_token, bo_data["id"])

        assert data["status"] == "delivered"


# ---------------------------------------------------------------------------
# Cancel Tests (Phase 4)
# ---------------------------------------------------------------------------


class TestBulkOrderCancel:
    async def test_cancel_draft_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Cancel a draft bulk order → status='cancelled', cancelled_at/cancelled_by set."""
        company, brand_a1, _a2 = company_a
        catalog, _products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Cancel Me"
        )

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/cancel",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["status"] == "cancelled"
        assert data["cancelled_at"] is not None
        assert data["cancelled_by"] == str(user_a1_manager.id)

    async def test_cancel_submitted_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit then cancel → status='cancelled'."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/cancel",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "cancelled"

    async def test_cancel_approved_bulk_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit → approve → cancel → status='cancelled'."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _approve_bulk_order(client, user_a1_manager_token, bo_data["id"])

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/cancel",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "cancelled"

    async def test_cancel_processing_bulk_order_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit → approve → process → cancel → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _approve_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _process_bulk_order(client, user_a1_manager_token, bo_data["id"])

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/cancel",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403

    async def test_cancel_delivered_bulk_order_fails(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Full lifecycle to delivered → cancel → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _approve_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _process_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _ship_bulk_order(client, user_a1_manager_token, bo_data["id"])
        await _deliver_bulk_order(client, user_a1_manager_token, bo_data["id"])

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/cancel",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Item Locking After Submit Tests (Phase 4)
# ---------------------------------------------------------------------------


class TestBulkOrderItemLockingAfterSubmit:
    """After submission, items cannot be added, updated, or removed."""

    async def test_cannot_add_item_after_submit(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit a bulk order, then try to add an item → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_with_items(
            client, user_a1_manager_token, catalog.id, products[0].id
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])

        response = await client.post(
            f"/api/v1/bulk_orders/{bo_data['id']}/items/",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"product_id": str(products[1].id), "quantity": 1},
        )
        assert response.status_code == 403

    async def test_cannot_update_item_after_submit(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit a bulk order, then try to update an item → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Lock Test"
        )
        item_data = await _add_item_via_api(
            client, user_a1_manager_token, bo_data["id"], str(products[0].id), quantity=1
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])

        response = await client.patch(
            f"/api/v1/bulk_orders/{bo_data['id']}/items/{item_data['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
            json={"quantity": 99},
        )
        assert response.status_code == 403

    async def test_cannot_remove_item_after_submit(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """Submit a bulk order, then try to remove an item → 403."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_manager.id
        )

        bo_data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Lock Test"
        )
        item_data = await _add_item_via_api(
            client, user_a1_manager_token, bo_data["id"], str(products[0].id), quantity=1
        )
        await _submit_bulk_order(client, user_a1_manager_token, bo_data["id"])

        response = await client.delete(
            f"/api/v1/bulk_orders/{bo_data['id']}/items/{item_data['id']}",
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 403
