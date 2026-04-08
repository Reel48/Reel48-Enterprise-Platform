"""Tests for Platform Admin Order endpoints (Module 4 Phase 5).

Covers cross-company order listing, filtering, detail retrieval,
and authorization checks for reel48_admin-only access.
"""

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.order import Order
from app.models.order_line_item import OrderLineItem
from app.models.product import Product
from app.models.user import User
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(
    db: AsyncSession, company_id, sub_brand_id, role: str = "employee"
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


async def _create_product(
    db: AsyncSession, company_id, sub_brand_id, created_by
) -> Product:
    product = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name="Test Product",
        description="A test product",
        sku=f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=29.99,
        sizes=["S", "M", "L"],
        decoration_options=["screen_print"],
        image_urls=[],
        status="active",
        created_by=created_by,
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def _create_order_with_items(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    user_id,
    catalog_id,
    product_id,
    *,
    status: str = "pending",
) -> Order:
    """Create an order with one line item directly in the database."""
    order = Order(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        user_id=user_id,
        catalog_id=catalog_id,
        order_number=f"ORD-20260408-{uuid4().hex[:4].upper()}",
        status=status,
        subtotal=29.99,
        total_amount=29.99,
    )
    db.add(order)
    await db.flush()
    await db.refresh(order)

    li = OrderLineItem(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        order_id=order.id,
        product_id=product_id,
        product_name="Test Product",
        product_sku="SKU-TEST",
        unit_price=29.99,
        quantity=1,
        line_total=29.99,
    )
    db.add(li)
    await db.flush()
    await db.refresh(li)

    return order


async def _create_active_catalog(
    db: AsyncSession, company_id, sub_brand_id, created_by
) -> Catalog:
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Test Catalog {uuid4().hex[:6]}",
        description="Catalog for platform order tests",
        slug=f"test-catalog-{uuid4().hex[:6]}",
        payment_model="self_service",
        status="active",
        created_by=created_by,
    )
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)
    return catalog


# ---------------------------------------------------------------------------
# Platform Orders Tests
# ---------------------------------------------------------------------------


class TestPlatformOrders:
    async def test_platform_list_orders_returns_all_companies(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
    ):
        """reel48_admin sees orders from both Company A and Company B."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        user_a = await _create_user(admin_db_session, company_a_obj.id, brand_a1.id)
        user_b = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)

        catalog_a = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id
        )
        catalog_b = await _create_active_catalog(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id
        )
        product_a = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id
        )
        product_b = await _create_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id
        )

        await _create_order_with_items(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id,
            catalog_a.id, product_a.id,
        )
        await _create_order_with_items(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id,
            catalog_b.id, product_b.id,
        )

        response = await client.get(
            "/api/v1/platform/orders/",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["total"] >= 2
        company_ids = {o["company_id"] for o in data["data"]}
        assert str(company_a_obj.id) in company_ids
        assert str(company_b_obj.id) in company_ids

    async def test_platform_list_orders_filter_by_company(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
    ):
        """?company_id= returns only that company's orders."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        user_a = await _create_user(admin_db_session, company_a_obj.id, brand_a1.id)
        user_b = await _create_user(admin_db_session, company_b_obj.id, brand_b1.id)

        catalog_a = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id
        )
        catalog_b = await _create_active_catalog(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id
        )
        product_a = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id
        )
        product_b = await _create_product(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id
        )

        await _create_order_with_items(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a.id,
            catalog_a.id, product_a.id,
        )
        await _create_order_with_items(
            admin_db_session, company_b_obj.id, brand_b1.id, user_b.id,
            catalog_b.id, product_b.id,
        )

        response = await client.get(
            f"/api/v1/platform/orders/?company_id={company_a_obj.id}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        for o in response.json()["data"]:
            assert o["company_id"] == str(company_a_obj.id)

    async def test_platform_list_orders_filter_by_status(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        """?status=approved returns only approved orders."""
        company_a_obj, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company_a_obj.id, brand_a1.id)
        catalog = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user.id
        )
        product = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user.id
        )

        await _create_order_with_items(
            admin_db_session, company_a_obj.id, brand_a1.id, user.id,
            catalog.id, product.id, status="approved",
        )
        await _create_order_with_items(
            admin_db_session, company_a_obj.id, brand_a1.id, user.id,
            catalog.id, product.id, status="pending",
        )

        response = await client.get(
            "/api/v1/platform/orders/?status=approved",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        for o in response.json()["data"]:
            assert o["status"] == "approved"

    async def test_platform_get_order_detail(
        self,
        client: AsyncClient,
        reel48_admin_user_token: str,
        reel48_admin_user,
        admin_db_session: AsyncSession,
        company_a,
    ):
        """reel48_admin can get any order with line items."""
        company_a_obj, brand_a1, _a2 = company_a
        user = await _create_user(admin_db_session, company_a_obj.id, brand_a1.id)
        catalog = await _create_active_catalog(
            admin_db_session, company_a_obj.id, brand_a1.id, user.id
        )
        product = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id, user.id
        )
        order = await _create_order_with_items(
            admin_db_session, company_a_obj.id, brand_a1.id, user.id,
            catalog.id, product.id,
        )

        response = await client.get(
            f"/api/v1/platform/orders/{order.id}",
            headers={"Authorization": f"Bearer {reel48_admin_user_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(order.id)
        assert data["order_number"] == order.order_number
        assert len(data["line_items"]) == 1
        assert data["line_items"][0]["product_name"] == "Test Product"

    async def test_platform_orders_requires_reel48_admin(
        self,
        client: AsyncClient,
        user_a_corporate_admin_token: str,
        user_a_corporate_admin,
    ):
        """corporate_admin gets 403 on platform order endpoints."""
        response = await client.get(
            "/api/v1/platform/orders/",
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 403

    async def test_platform_orders_employee_gets_403(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        user_a1_employee,
    ):
        """employee gets 403 on platform order endpoints."""
        response = await client.get(
            "/api/v1/platform/orders/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403
