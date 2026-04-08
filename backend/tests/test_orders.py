"""Tests for Order Placement endpoint (Module 4 Phase 2)."""

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import Catalog
from app.models.catalog_product import CatalogProduct
from app.models.employee_profile import EmployeeProfile
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
    """Create an active catalog with active products for testing orders."""
    catalog = Catalog(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=f"Test Catalog {uuid4().hex[:6]}",
        description="Catalog for order tests",
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


async def _create_employee_profile_with_address(
    db: AsyncSession, user: User
) -> EmployeeProfile:
    """Create an employee profile with a delivery address."""
    profile = EmployeeProfile(
        company_id=user.company_id,
        sub_brand_id=user.sub_brand_id,
        user_id=user.id,
        department="Engineering",
        delivery_address_line1="123 Main St",
        delivery_address_line2="Suite 100",
        delivery_city="Austin",
        delivery_state="TX",
        delivery_zip="78701",
        delivery_country="US",
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


# ---------------------------------------------------------------------------
# Functional Tests — Create Order
# ---------------------------------------------------------------------------


class TestCreateOrderFunctional:
    async def test_create_order_success(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Employee places order with valid catalog/products → 201."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 2},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["status"] == "pending"
        assert data["catalog_id"] == str(catalog.id)
        assert len(data["line_items"]) == 1

    async def test_create_order_snapshots_product_details(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Response contains product_name, product_sku from product at order time."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        li = response.json()["data"]["line_items"][0]
        assert li["product_name"] == products[0].name
        assert li["product_sku"] == products[0].sku

    async def test_create_order_uses_catalog_price_override(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """When catalog_product has price_override, order uses that price."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session,
            company.id,
            brand_a1.id,
            user_a1_employee.id,
            price_overrides=[19.99],
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        li = response.json()["data"]["line_items"][0]
        assert float(li["unit_price"]) == 19.99

    async def test_create_order_uses_product_price_when_no_override(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """When no price_override, uses product.unit_price."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session,
            company.id,
            brand_a1.id,
            user_a1_employee.id,
            price_overrides=[None],
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        li = response.json()["data"]["line_items"][0]
        assert float(li["unit_price"]) == float(products[0].unit_price)

    async def test_create_order_calculates_totals(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """subtotal = sum(line_totals), total_amount = subtotal."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 2},
                    {"product_id": str(products[1].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        li_totals = [float(li["line_total"]) for li in data["line_items"]]
        expected_subtotal = sum(li_totals)
        assert float(data["subtotal"]) == expected_subtotal
        assert float(data["total_amount"]) == expected_subtotal

    async def test_create_order_multiple_line_items(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Order with 3 different products has correct line items and totals."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id, num_products=3
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                    {"product_id": str(products[1].id), "quantity": 3},
                    {"product_id": str(products[2].id), "quantity": 2},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert len(data["line_items"]) == 3

    async def test_create_order_copies_shipping_from_profile(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """When no address in request, copies from employee profile."""
        company, brand_a1, _a2 = company_a
        await _create_employee_profile_with_address(admin_db_session, user_a1_employee)
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["shipping_address_line1"] == "123 Main St"
        assert data["shipping_city"] == "Austin"
        assert data["shipping_state"] == "TX"
        assert data["shipping_zip"] == "78701"

    async def test_create_order_uses_explicit_shipping_address(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """When address provided in request, uses it (not profile)."""
        company, brand_a1, _a2 = company_a
        await _create_employee_profile_with_address(admin_db_session, user_a1_employee)
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
                "shipping_address_line1": "456 Oak Ave",
                "shipping_city": "Dallas",
                "shipping_state": "TX",
                "shipping_zip": "75201",
                "shipping_country": "US",
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["shipping_address_line1"] == "456 Oak Ave"
        assert data["shipping_city"] == "Dallas"

    async def test_create_order_generates_order_number(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """order_number matches pattern 'ORD-YYYYMMDD-XXXX'."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        order_number = response.json()["data"]["order_number"]
        assert re.match(r"^ORD-\d{8}-[A-F0-9]{4}$", order_number)

    async def test_create_order_status_is_pending(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """New orders have status='pending'."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["status"] == "pending"

    async def test_create_order_with_size_and_decoration(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Size and decoration fields are stored on line items."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {
                        "product_id": str(products[0].id),
                        "quantity": 1,
                        "size": "L",
                        "decoration": "embroidery",
                    },
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        li = response.json()["data"]["line_items"][0]
        assert li["size"] == "L"
        assert li["decoration"] == "embroidery"


# ---------------------------------------------------------------------------
# Validation Error Tests
# ---------------------------------------------------------------------------


class TestCreateOrderValidation:
    async def test_create_order_empty_line_items_returns_422(
        self,
        client: AsyncClient,
        user_a1_employee_token: str,
        company_a,
    ):
        """Empty line items list → 422."""
        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(uuid4()),
                "line_items": [],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422

    async def test_create_order_product_not_in_catalog_returns_404(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Product exists but not in this catalog → 404."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        # Create a product NOT in the catalog
        other_product = Product(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            name="Other Product",
            sku=f"SKU-{uuid4().hex[:8].upper()}",
            unit_price=15.00,
            sizes=[],
            decoration_options=[],
            image_urls=[],
            status="active",
            created_by=user_a1_employee.id,
        )
        admin_db_session.add(other_product)
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(other_product.id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404

    async def test_create_order_catalog_not_active_returns_403(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
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
            created_by=user_a1_employee.id,
        )
        admin_db_session.add(catalog)
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(uuid4()), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_create_order_product_not_active_returns_422(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Product in catalog but status=draft → 422."""
        company, brand_a1, _a2 = company_a

        # Create active catalog
        catalog = Catalog(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            name="Catalog for draft product",
            slug=f"cat-draft-prod-{uuid4().hex[:6]}",
            payment_model="self_service",
            status="active",
            created_by=user_a1_employee.id,
        )
        admin_db_session.add(catalog)
        await admin_db_session.flush()

        # Create a draft product
        product = Product(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            name="Draft Product",
            sku=f"SKU-{uuid4().hex[:8].upper()}",
            unit_price=20.00,
            sizes=[],
            decoration_options=[],
            image_urls=[],
            status="draft",
            created_by=user_a1_employee.id,
        )
        admin_db_session.add(product)
        await admin_db_session.flush()

        # Add draft product to catalog
        cp = CatalogProduct(
            catalog_id=catalog.id,
            product_id=product.id,
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            display_order=0,
        )
        admin_db_session.add(cp)
        await admin_db_session.flush()

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(product.id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422

    async def test_create_order_invalid_size_returns_422(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Size not in product.sizes → 422."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {
                        "product_id": str(products[0].id),
                        "quantity": 1,
                        "size": "XXXL",
                    },
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422

    async def test_create_order_invalid_decoration_returns_422(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Decoration not in product.decoration_options → 422."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {
                        "product_id": str(products[0].id),
                        "quantity": 1,
                        "decoration": "laser_etching",
                    },
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422

    async def test_create_order_buying_window_closed_returns_422(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """invoice_after_close catalog with past close date → 422."""
        company, brand_a1, _a2 = company_a
        now = datetime.now(UTC)
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session,
            company.id,
            brand_a1.id,
            user_a1_employee.id,
            payment_model="invoice_after_close",
            buying_window_opens_at=now - timedelta(days=2),
            buying_window_closes_at=now - timedelta(days=1),
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422

    async def test_create_order_buying_window_not_open_returns_422(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """invoice_after_close catalog with future open date → 422."""
        company, brand_a1, _a2 = company_a
        now = datetime.now(UTC)
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session,
            company.id,
            brand_a1.id,
            user_a1_employee.id,
            payment_model="invoice_after_close",
            buying_window_opens_at=now + timedelta(days=1),
            buying_window_closes_at=now + timedelta(days=2),
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Authorization Tests
# ---------------------------------------------------------------------------


class TestCreateOrderAuthorization:
    async def test_create_order_reel48_admin_returns_403(
        self,
        client: AsyncClient,
        reel48_admin_token: str,
    ):
        """reel48_admin has no company_id → 403."""
        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(uuid4()),
                "line_items": [
                    {"product_id": str(uuid4()), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {reel48_admin_token}"},
        )
        assert response.status_code == 403

    async def test_create_order_employee_can_order(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        user_a1_employee_token: str,
        company_a,
    ):
        """Employee role can place orders (201)."""
        company, brand_a1, _a2 = company_a
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company.id, brand_a1.id, user_a1_employee.id
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201


# ---------------------------------------------------------------------------
# Isolation Tests
# ---------------------------------------------------------------------------


class TestCreateOrderIsolation:
    async def test_create_order_cross_company_catalog_returns_404(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        user_a1_employee,
        company_a,
        company_b,
        user_b1_employee,
    ):
        """Company B employee cannot order from Company A's catalog."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Create catalog in Company A
        catalog, products, _cps = await _create_active_catalog_with_products(
            admin_db_session, company_a_obj.id, brand_a1.id, user_a1_employee.id
        )

        # Create token for Company B employee with matching cognito_sub
        token_b = create_test_token(
            user_id=user_b1_employee.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="employee",
        )

        response = await client.post(
            "/api/v1/orders/",
            json={
                "catalog_id": str(catalog.id),
                "line_items": [
                    {"product_id": str(products[0].id), "quantity": 1},
                ],
            },
            headers={"Authorization": f"Bearer {token_b}"},
        )
        # Company B's catalog query won't find Company A's catalog
        assert response.status_code == 404
