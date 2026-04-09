"""Tests for Platform Admin Bulk Order endpoints (Module 5 Phase 5).

Covers cross-company bulk order listing, filtering, detail retrieval,
and authorization checks for reel48_admin-only access.
"""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bulk_order import BulkOrder
from app.models.bulk_order_item import BulkOrderItem
from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.product import Product
from app.models.user import User
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_active_catalog(
    db: AsyncSession, company_id, sub_brand_id, created_by,
) -> Catalog:
    """Create an active catalog for bulk order tests."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Platform Test Catalog {uuid4().hex[:6]}",
        slug=f"platform-cat-{uuid4().hex[:6]}",
        payment_model="self_service",
        status="active",
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


async def _create_product_in_catalog(
    db: AsyncSession, catalog, company_id, sub_brand_id, created_by,
) -> Product:
    """Create an active product and add it to the catalog."""
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Platform Product {uuid4().hex[:6]}",
        sku=f"PLAT-{uuid4().hex[:8].upper()}",
        unit_price=25.00,
        sizes=["M", "L"],
        decoration_options=[],
        image_urls=[],
        status="active",
        created_by=created_by,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)

    cp = CatalogProduct(
        catalog_id=catalog.id,
        product_id=product.id,
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        display_order=0,
    )
    db.add(cp)
    await db.flush()
    return product


async def _create_company_b_manager(
    db: AsyncSession, company_b,
) -> tuple[User, str]:
    """Create a manager user in Company B with a matching JWT token."""
    company, brand_b1 = company_b
    user = User(
        company_id=company.id,
        sub_brand_id=brand_b1.id,
        cognito_sub=str(uuid4()),
        email=f"mgr-b-{uuid4().hex[:6]}@test.com",
        full_name="Manager B1",
        role="regional_manager",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    token = create_test_token(
        user_id=user.cognito_sub,
        company_id=str(company.id),
        sub_brand_id=str(brand_b1.id),
        role="regional_manager",
    )
    return user, token


async def _create_bulk_order_via_api(
    client: AsyncClient, token: str, catalog_id, title: str = "Test Bulk Order",
) -> dict:
    """Create a bulk order via API and return the response JSON data."""
    response = await client.post(
        "/api/v1/bulk_orders/",
        headers={"Authorization": f"Bearer {token}"},
        json={"catalog_id": str(catalog_id), "title": title},
    )
    assert response.status_code == 201
    return response.json()["data"]


async def _add_item_via_api(
    client: AsyncClient, token: str, bulk_order_id: str, product_id,
) -> dict:
    """Add an item to a bulk order via API."""
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/items/",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": str(product_id), "quantity": 2, "size": "M"},
    )
    assert response.status_code == 201
    return response.json()["data"]


async def _submit_bulk_order_via_api(
    client: AsyncClient, token: str, bulk_order_id: str,
) -> dict:
    """Submit a bulk order via API."""
    response = await client.post(
        f"/api/v1/bulk_orders/{bulk_order_id}/submit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    return response.json()["data"]


# ---------------------------------------------------------------------------
# Platform Bulk Orders Tests
# ---------------------------------------------------------------------------


class TestPlatformBulkOrders:
    async def test_platform_list_bulk_orders_returns_all_companies(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
        company_b,
    ):
        """reel48_admin sees bulk orders from both Company A and Company B."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Set up Company A catalog + product
        catalog_a = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_manager.id,
        )
        await _create_product_in_catalog(
            admin_db_session, catalog_a, company_a_obj.id, brand_a1.id,
            user_a1_manager.id,
        )

        # Set up Company B manager, catalog + product
        mgr_b, mgr_b_token = await _create_company_b_manager(
            admin_db_session, company_b,
        )
        catalog_b = await _create_active_catalog(
            admin_db_session, company_b_obj.id, brand_b1.id, mgr_b.id,
        )
        await _create_product_in_catalog(
            admin_db_session, catalog_b, company_b_obj.id, brand_b1.id, mgr_b.id,
        )

        # Create bulk orders via API
        await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog_a.id, "Company A Bulk",
        )
        await _create_bulk_order_via_api(
            client, mgr_b_token, catalog_b.id, "Company B Bulk",
        )

        # Platform admin lists all
        response = await client.get(
            "/api/v1/platform/bulk_orders/",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] >= 2
        company_ids = {bo["company_id"] for bo in data["data"]}
        assert str(company_a_obj.id) in company_ids
        assert str(company_b_obj.id) in company_ids

    async def test_platform_list_bulk_orders_filter_by_company(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
        company_b,
    ):
        """?company_id= returns only that company's bulk orders."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        catalog_a = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_manager.id,
        )
        await _create_product_in_catalog(
            admin_db_session, catalog_a, company_a_obj.id, brand_a1.id,
            user_a1_manager.id,
        )

        mgr_b, mgr_b_token = await _create_company_b_manager(
            admin_db_session, company_b,
        )
        catalog_b = await _create_active_catalog(
            admin_db_session, company_b_obj.id, brand_b1.id, mgr_b.id,
        )
        await _create_product_in_catalog(
            admin_db_session, catalog_b, company_b_obj.id, brand_b1.id, mgr_b.id,
        )

        await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog_a.id, "A Bulk",
        )
        await _create_bulk_order_via_api(
            client, mgr_b_token, catalog_b.id, "B Bulk",
        )

        response = await client.get(
            f"/api/v1/platform/bulk_orders/?company_id={company_a_obj.id}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        for bo in response.json()["data"]:
            assert bo["company_id"] == str(company_a_obj.id)

    async def test_platform_list_bulk_orders_filter_by_status(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """?status= filters bulk orders by status."""
        company_a_obj, brand_a1, _a2 = company_a

        catalog = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_manager.id,
        )
        product = await _create_product_in_catalog(
            admin_db_session, catalog, company_a_obj.id, brand_a1.id,
            user_a1_manager.id,
        )

        # Create two bulk orders
        draft_bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Draft Bulk Order",
        )
        submit_bo = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "To Submit Bulk Order",
        )

        # Add item and submit the second one
        await _add_item_via_api(
            client, user_a1_manager_token, submit_bo["id"], product.id,
        )
        await _submit_bulk_order_via_api(
            client, user_a1_manager_token, submit_bo["id"],
        )

        # Filter by draft
        response = await client.get(
            "/api/v1/platform/bulk_orders/?status=draft",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        draft_ids = {bo["id"] for bo in response.json()["data"]}
        assert draft_bo["id"] in draft_ids
        assert submit_bo["id"] not in draft_ids

        # Filter by submitted
        response = await client.get(
            "/api/v1/platform/bulk_orders/?status=submitted",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        submitted_ids = {bo["id"] for bo in response.json()["data"]}
        assert submit_bo["id"] in submitted_ids
        assert draft_bo["id"] not in submitted_ids

    async def test_platform_get_bulk_order_detail(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        user_a1_manager,
        user_a1_manager_token: str,
        company_a,
    ):
        """reel48_admin can get any bulk order with items."""
        company_a_obj, brand_a1, _a2 = company_a

        catalog = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_manager.id,
        )
        product = await _create_product_in_catalog(
            admin_db_session, catalog, company_a_obj.id, brand_a1.id,
            user_a1_manager.id,
        )

        bo_data = await _create_bulk_order_via_api(
            client, user_a1_manager_token, catalog.id, "Detail Test",
        )
        await _add_item_via_api(
            client, user_a1_manager_token, bo_data["id"], product.id,
        )

        response = await client.get(
            f"/api/v1/platform/bulk_orders/{bo_data['id']}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == bo_data["id"]
        assert data["title"] == "Detail Test"
        assert len(data["items"]) == 1
        assert data["items"][0]["product_name"].startswith("Platform Product")

    async def test_platform_bulk_orders_requires_reel48_admin(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
    ):
        """corporate_admin gets 403 on platform bulk order endpoints."""
        response = await client.get(
            "/api/v1/platform/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    async def test_platform_bulk_orders_employee_gets_403(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        """employee gets 403 on platform bulk order endpoints."""
        response = await client.get(
            "/api/v1/platform/bulk_orders/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403
