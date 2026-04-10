"""Tests for Module 9 Phase 3: Wishlist Service & API Endpoints.

Covers:
- Functional tests (add, remove, list, check, pagination, duplicate, validation)
- Isolation tests (cross-company, cross-sub-brand)
- Authorization tests (all roles can manage own wishlist, unauthenticated returns 401)
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.user import User
from app.models.wishlist import Wishlist
from tests.conftest import create_test_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_product(
    db: AsyncSession,
    company_id,
    sub_brand_id,
    created_by,
    name="Test Product",
    sku=None,
    unit_price=29.99,
    status="active",
    image_urls=None,
) -> Product:
    """Helper to insert a product directly in the database.

    created_by must be a real users.id UUID (FK constraint).
    """
    p = Product(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        name=name,
        sku=sku or f"SKU-{uuid4().hex[:8].upper()}",
        unit_price=unit_price,
        status=status,
        image_urls=image_urls or ["https://example.com/img.png"],
        created_by=created_by,
    )
    db.add(p)
    await db.flush()
    await db.refresh(p)
    return p


async def _create_wishlist_entry(
    db: AsyncSession,
    user_id,
    product_id,
    company_id,
    sub_brand_id=None,
    catalog_id=None,
    notes=None,
    created_at=None,
) -> Wishlist:
    """Helper to insert a wishlist entry directly in the database."""
    w = Wishlist(
        company_id=company_id,
        sub_brand_id=sub_brand_id,
        user_id=user_id,
        product_id=product_id,
        catalog_id=catalog_id,
        notes=notes,
    )
    if created_at is not None:
        w.created_at = created_at
    db.add(w)
    await db.flush()
    await db.refresh(w)
    return w


# ===========================================================================
# FUNCTIONAL TESTS
# ===========================================================================


class TestAddToWishlist:
    """Tests for POST /api/v1/wishlists/"""

    async def test_add_product_to_wishlist_returns_201(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, name="Wishlist Product",
        )

        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        data = response.json()["data"]
        assert data["product_id"] == str(product.id)
        assert data["product_name"] == "Wishlist Product"
        assert data["product_sku"] == product.sku
        assert data["product_unit_price"] == 29.99
        assert data["product_image_url"] == "https://example.com/img.png"
        assert data["product_status"] == "active"
        assert data["is_purchasable"] is True
        assert data["id"] is not None

    async def test_add_product_with_notes(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id,
        )

        response = await client.post(
            "/api/v1/wishlists/",
            json={
                "product_id": str(product.id),
                "notes": "Want this in blue",
            },
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        assert response.json()["data"]["notes"] == "Want this in blue"

    async def test_add_duplicate_product_returns_409(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id,
        )

        # Add once
        await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        # Add again — should conflict
        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 409

    async def test_add_nonexistent_product_returns_404(
        self,
        client: AsyncClient,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(uuid4())},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404

    async def test_add_draft_product_returns_403(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, status="draft",
        )

        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403

    async def test_add_archived_product_returns_403(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, status="archived",
        )

        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 403


class TestRemoveFromWishlist:
    """Tests for DELETE /api/v1/wishlists/{wishlist_id}"""

    async def test_remove_from_wishlist_returns_204(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id,
        )
        entry = await _create_wishlist_entry(
            admin_db_session, user_a1_employee.id, product.id, company.id, brand_a1.id
        )

        response = await client.delete(
            f"/api/v1/wishlists/{entry.id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 204

    async def test_remove_another_users_entry_returns_404(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        """Cannot remove another user's wishlist entry (returns 404, not 403)."""
        company, brand_a1, _a2 = company_a

        # Create another user in the same sub-brand
        other_user = User(
            company_id=company.id,
            sub_brand_id=brand_a1.id,
            cognito_sub=str(uuid4()),
            email=f"other-{uuid4().hex[:6]}@companya.com",
            full_name="Other User",
            role="employee",
        )
        admin_db_session.add(other_user)
        await admin_db_session.flush()

        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=other_user.id,
        )
        entry = await _create_wishlist_entry(
            admin_db_session, other_user.id, product.id, company.id, brand_a1.id
        )

        response = await client.delete(
            f"/api/v1/wishlists/{entry.id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404

    async def test_remove_nonexistent_returns_404(
        self,
        client: AsyncClient,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        response = await client.delete(
            f"/api/v1/wishlists/{uuid4()}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404


class TestListWishlist:
    """Tests for GET /api/v1/wishlists/"""

    async def test_list_returns_products_with_details_newest_first(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        p1 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, name="First Product",
        )
        p2 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, name="Second Product",
        )
        now = datetime.now(timezone.utc)
        await _create_wishlist_entry(
            admin_db_session, user_a1_employee.id, p1.id, company.id, brand_a1.id,
            created_at=now - timedelta(minutes=5),
        )
        await _create_wishlist_entry(
            admin_db_session, user_a1_employee.id, p2.id, company.id, brand_a1.id,
            created_at=now,
        )

        response = await client.get(
            "/api/v1/wishlists/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        items = data["data"]
        assert len(items) >= 2
        # Most recently added first
        names = [i["product_name"] for i in items]
        assert names.index("Second Product") < names.index("First Product")

    async def test_list_includes_product_details(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id,
            name="Detail Product",
            unit_price=49.99,
            image_urls=["https://example.com/detail.png"],
        )
        await _create_wishlist_entry(
            admin_db_session, user_a1_employee.id, product.id, company.id, brand_a1.id
        )

        response = await client.get(
            "/api/v1/wishlists/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        items = response.json()["data"]
        detail_items = [i for i in items if i["product_name"] == "Detail Product"]
        assert len(detail_items) == 1
        item = detail_items[0]
        assert item["product_unit_price"] == 49.99
        assert item["product_image_url"] == "https://example.com/detail.png"
        assert item["is_purchasable"] is True

    async def test_pagination(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        for i in range(5):
            p = await _create_product(
                admin_db_session, company.id, brand_a1.id,
                created_by=user_a1_employee.id, name=f"Page Product {i}",
            )
            await _create_wishlist_entry(
                admin_db_session, user_a1_employee.id, p.id, company.id, brand_a1.id
            )

        response = await client.get(
            "/api/v1/wishlists/?page=1&per_page=2",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 2
        assert data["meta"]["per_page"] == 2
        assert data["meta"]["total"] >= 5


class TestCheckWishlist:
    """Tests for POST /api/v1/wishlists/check"""

    async def test_check_returns_correct_status(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        p1 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, name="Wishlisted",
        )
        p2 = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, name="Not Wishlisted",
        )
        await _create_wishlist_entry(
            admin_db_session, user_a1_employee.id, p1.id, company.id, brand_a1.id
        )

        response = await client.post(
            "/api/v1/wishlists/check",
            json={"product_ids": [str(p1.id), str(p2.id)]},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data[str(p1.id)] is True
        assert data[str(p2.id)] is False

    async def test_check_empty_list_returns_empty(
        self,
        client: AsyncClient,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        response = await client.post(
            "/api/v1/wishlists/check",
            json={"product_ids": []},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200
        assert response.json()["data"] == {}


# ===========================================================================
# ISOLATION TESTS
# ===========================================================================


class TestIsolation:
    """Cross-company and cross-sub-brand isolation tests."""

    async def test_company_b_cannot_see_company_a_wishlists(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
        user_a1_employee,
        user_b1_employee,
    ):
        """Company B employee cannot see Company A's wishlists."""
        company_a_obj, brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        product_a = await _create_product(
            admin_db_session, company_a_obj.id, brand_a1.id,
            created_by=user_a1_employee.id, name="Company A Product",
        )
        await _create_wishlist_entry(
            admin_db_session,
            user_a1_employee.id,
            product_a.id,
            company_a_obj.id,
            brand_a1.id,
        )

        # Query as Company B employee
        token_b = create_test_token(
            user_id=user_b1_employee.cognito_sub,
            company_id=str(company_b_obj.id),
            sub_brand_id=str(brand_b1.id),
            role="employee",
        )
        response = await client.get(
            "/api/v1/wishlists/",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert response.status_code == 200
        names = [i["product_name"] for i in response.json()["data"]]
        assert "Company A Product" not in names

    async def test_sub_brand_a2_cannot_see_a1_wishlists(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
    ):
        """Brand A2 employee cannot see Brand A1 user's wishlists."""
        company, brand_a1, brand_a2 = company_a

        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id, name="A1 Only Product",
        )
        await _create_wishlist_entry(
            admin_db_session,
            user_a1_employee.id,
            product.id,
            company.id,
            brand_a1.id,
        )

        # Create Brand A2 employee
        user_a2 = User(
            company_id=company.id,
            sub_brand_id=brand_a2.id,
            cognito_sub=str(uuid4()),
            email=f"emp-a2-wl-{uuid4().hex[:6]}@companya.com",
            full_name="Employee A2 WL",
            role="employee",
        )
        admin_db_session.add(user_a2)
        await admin_db_session.flush()

        token_a2 = create_test_token(
            user_id=user_a2.cognito_sub,
            company_id=str(company.id),
            sub_brand_id=str(brand_a2.id),
            role="employee",
        )

        response = await client.get(
            "/api/v1/wishlists/",
            headers={"Authorization": f"Bearer {token_a2}"},
        )
        assert response.status_code == 200
        names = [i["product_name"] for i in response.json()["data"]]
        assert "A1 Only Product" not in names

    async def test_cannot_add_product_from_another_company(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        company_b,
        user_a1_employee,
        user_a1_employee_token,
        user_b1_employee,
    ):
        """Cannot add a product from another company to wishlist."""
        _company_a_obj, _brand_a1, _a2 = company_a
        company_b_obj, brand_b1 = company_b

        # Create product in Company B
        product_b = await _create_product(
            admin_db_session, company_b_obj.id, brand_b1.id,
            created_by=user_b1_employee.id, name="Company B Product",
        )

        # Try to add as Company A employee
        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product_b.id)},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 404


# ===========================================================================
# AUTHORIZATION TESTS
# ===========================================================================


class TestAuthorization:
    """Role-based access control tests."""

    async def test_employee_can_manage_wishlist(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_employee,
        user_a1_employee_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_employee.id,
        )

        # Add
        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 201
        wishlist_id = response.json()["data"]["id"]

        # List
        response = await client.get(
            "/api/v1/wishlists/",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200

        # Check
        response = await client.post(
            "/api/v1/wishlists/check",
            json={"product_ids": [str(product.id)]},
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 200

        # Remove
        response = await client.delete(
            f"/api/v1/wishlists/{wishlist_id}",
            headers={"Authorization": f"Bearer {user_a1_employee_token}"},
        )
        assert response.status_code == 204

    async def test_manager_can_manage_wishlist(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_manager,
        user_a1_manager_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_manager.id,
        )

        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_manager_token}"},
        )
        assert response.status_code == 201

    async def test_admin_can_manage_wishlist(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a1_admin,
        user_a1_admin_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a1_admin.id,
        )

        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a1_admin_token}"},
        )
        assert response.status_code == 201

    async def test_corporate_admin_can_manage_wishlist(
        self,
        client: AsyncClient,
        admin_db_session: AsyncSession,
        company_a,
        user_a_corporate_admin,
        user_a_corporate_admin_token,
    ):
        company, brand_a1, _a2 = company_a
        product = await _create_product(
            admin_db_session, company.id, brand_a1.id,
            created_by=user_a_corporate_admin.id,
        )

        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(product.id)},
            headers={"Authorization": f"Bearer {user_a_corporate_admin_token}"},
        )
        assert response.status_code == 201

    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.get("/api/v1/wishlists/")
        assert response.status_code in (401, 403)

    async def test_unauthenticated_post_returns_401(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/wishlists/",
            json={"product_id": str(uuid4())},
        )
        assert response.status_code in (401, 403)
